"""Guardian dashboard: children (with consent), passwords, export, deletion."""

from __future__ import annotations

import json
import re
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import DB, KG, student_out
from app.engagement.progress_viz import mastery_map
from app.models import AuthSession, EmailToken, Guardian, Mastery, Message, Quiz, Student, TutorSession, utcnow
from app.security.auth import GuardianDep, SettingsDep, clear_cookie, end_all_sessions
from app.security.passwords import hash_password, verify_password
from app.student.mastery_tracker import MasteryTracker

router = APIRouter(prefix="/api", tags=["guardian"])

USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,30}$")
StudentPassword = Annotated[str, Field(min_length=8, max_length=128)]


class ChildIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    username: str = Field(min_length=3, max_length=30)
    password: StudentPassword
    consent: Literal[True]  # must be exactly true
    policy_version: str = Field(max_length=32)


class PasswordIn(BaseModel):
    password: StudentPassword


class DeleteAccountIn(BaseModel):
    password: str = Field(max_length=128)


@router.get("/privacy/policy")
def privacy_policy(settings: SettingsDep):
    return {"version": settings.privacy_policy_version, "updated": settings.privacy_policy_version}


def _own_child(db: Session, guardian: Guardian, student_id: str) -> Student:
    s = db.get(Student, student_id)
    if s is None or s.guardian_id != guardian.id:
        raise HTTPException(404, "Student not found")
    return s


@router.get("/guardian/students")
def list_children(guardian: GuardianDep, db: DB, kg: KG):
    out = []
    for s in db.scalars(select(Student).where(Student.guardian_id == guardian.id).order_by(Student.created_at)):
        summary = mastery_map(kg, MasteryTracker(db).all_levels(s.id))["summary"]
        last_msg = db.scalar(
            select(func.max(Message.created_at))
            .join(TutorSession, Message.session_id == TutorSession.id)
            .where(TutorSession.student_id == s.id)
        )
        last_quiz = db.scalar(select(func.max(Quiz.created_at)).where(Quiz.student_id == s.id))
        last = max((d for d in (last_msg, last_quiz) if d is not None), default=None)
        out.append(
            {
                **student_out(s),
                "overall_progress": summary["overall_progress"],
                "mastered": summary["mastered"],
                "last_active": last,
            }
        )
    return out


@router.post("/guardian/students", status_code=201)
def add_child(body: ChildIn, guardian: GuardianDep, db: DB, settings: SettingsDep):
    if guardian.email_verified_at is None:
        raise HTTPException(403, "Please verify your email address before adding a child.")
    if body.policy_version != settings.privacy_policy_version:
        raise HTTPException(409, "The privacy notice has been updated. Please reload the page and review it.")
    username = body.username.strip().lower()
    if not USERNAME_RE.match(username):
        raise HTTPException(422, "Usernames are 3–30 characters: letters, numbers, dots, dashes or underscores.")
    if db.scalar(select(Student).where(Student.username == username)):
        raise HTTPException(409, "That username is taken. Please choose another.")
    student = Student(
        guardian_id=guardian.id,
        name=body.name.strip(),
        username=username,
        password_hash=hash_password(body.password),
        grade=settings.default_grade,
        board=settings.default_board,
        consent_given_at=utcnow(),
        consent_policy_version=body.policy_version,
    )
    db.add(student)
    db.commit()
    return student_out(student)


@router.put("/guardian/students/{student_id}/password", status_code=204)
def change_child_password(student_id: str, body: PasswordIn, guardian: GuardianDep, db: DB):
    s = _own_child(db, guardian, student_id)
    s.password_hash = hash_password(body.password)
    end_all_sessions(db, student_id=s.id)  # log the child out everywhere
    db.commit()
    return Response(status_code=204)


@router.get("/guardian/students/{student_id}/export")
def export_child(student_id: str, guardian: GuardianDep, db: DB, kg: KG):
    """Everything stored about the child, in one JSON document (right of access)."""
    s = _own_child(db, guardian, student_id)
    sessions = db.scalars(select(TutorSession).where(TutorSession.student_id == s.id).order_by(TutorSession.started_at))
    quizzes = db.scalars(select(Quiz).where(Quiz.student_id == s.id).order_by(Quiz.created_at))
    data = {
        "exported_at": utcnow().isoformat(),
        "student": {**student_out(s), "created_at": s.created_at.isoformat()},
        "consent": {
            "given_by_guardian": guardian.email,
            "given_at": s.consent_given_at.isoformat(),
            "privacy_notice_version": s.consent_policy_version,
        },
        "mastery": [
            {"concept": m.concept_id, "level": m.level, "attempts": m.attempts, "correct": m.correct}
            for m in MasteryTracker(db).all_levels(s.id).values()
        ],
        "tutoring_sessions": [
            {
                "concept": t.concept_id,
                "tutor_persona": t.persona,
                "started_at": t.started_at.isoformat(),
                "ended_at": t.ended_at.isoformat() if t.ended_at else None,
                "messages": [{"from": m.role, "text": m.content, "at": m.created_at.isoformat()} for m in t.messages],
            }
            for t in sessions
        ],
        "quizzes": [
            {
                "concept": q.concept_id,
                "taken_at": q.created_at.isoformat(),
                "questions": [
                    {"question": item["prompt"], "answered": q.answered.get(item["id"])} for item in q.questions
                ],
            }
            for q in quizzes
        ],
    }
    filename = f"tailored-tuition-{s.username}.json"
    return Response(
        content=json.dumps(data, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def delete_student_data(db: Session, student_id: str) -> None:
    """Permanently remove a student and everything linked to them. Explicit
    deletes (not relying on DB cascades) so it behaves the same on every database."""
    session_ids = select(TutorSession.id).where(TutorSession.student_id == student_id)
    db.execute(delete(Message).where(Message.session_id.in_(session_ids)))
    db.execute(delete(TutorSession).where(TutorSession.student_id == student_id))
    db.execute(delete(Quiz).where(Quiz.student_id == student_id))
    db.execute(delete(Mastery).where(Mastery.student_id == student_id))
    db.execute(delete(AuthSession).where(AuthSession.student_id == student_id))
    db.execute(delete(Student).where(Student.id == student_id))


@router.delete("/guardian/students/{student_id}", status_code=204)
def delete_child(student_id: str, guardian: GuardianDep, db: DB):
    s = _own_child(db, guardian, student_id)
    delete_student_data(db, s.id)
    db.commit()
    return Response(status_code=204)


@router.delete("/guardian/account", status_code=204)
def delete_account(body: DeleteAccountIn, guardian: GuardianDep, db: DB, settings: SettingsDep):
    if not verify_password(body.password, guardian.password_hash):
        raise HTTPException(403, "Password is incorrect.")
    for sid in db.scalars(select(Student.id).where(Student.guardian_id == guardian.id)).all():
        delete_student_data(db, sid)
    db.execute(delete(EmailToken).where(EmailToken.guardian_id == guardian.id))
    db.execute(delete(AuthSession).where(AuthSession.guardian_id == guardian.id))
    db.execute(delete(Guardian).where(Guardian.id == guardian.id))
    db.commit()
    response = Response(status_code=204)
    clear_cookie(response, settings)
    return response
