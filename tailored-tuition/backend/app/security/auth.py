"""Login sessions (cookie) and the current-user dependency.

Cookie `tt_session`: HttpOnly (JavaScript can't read it), SameSite=Lax, Secure
when COOKIE_SECURE (HTTPS). The database stores only the token's SHA-256.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import AuthSession, Guardian, Student, utcnow
from app.security.tokens import hash_token, new_token

COOKIE = "tt_session"


@dataclass
class Principal:
    role: str  # "guardian" | "student"
    guardian: Guardian | None = None
    student: Student | None = None
    token_hash: str | None = None


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def start_session(
    db: Session,
    response: Response,
    settings: Settings,
    *,
    guardian: Guardian | None = None,
    student: Student | None = None,
) -> None:
    role = "guardian" if guardian else "student"
    days = settings.guardian_session_days if guardian else settings.student_session_days
    token, token_hash = new_token()
    db.add(
        AuthSession(
            token_hash=token_hash,
            role=role,
            guardian_id=guardian.id if guardian else None,
            student_id=student.id if student else None,
            expires_at=utcnow() + timedelta(days=days),
        )
    )
    db.commit()
    response.set_cookie(
        COOKIE,
        token,
        max_age=days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def end_all_sessions(db: Session, *, guardian_id: str | None = None, student_id: str | None = None) -> None:
    if guardian_id:
        db.execute(delete(AuthSession).where(AuthSession.guardian_id == guardian_id))
    if student_id:
        db.execute(delete(AuthSession).where(AuthSession.student_id == student_id))


def clear_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(COOKIE, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax")


def optional_principal(request: Request, db: Annotated[Session, Depends(get_db)]) -> Principal | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    row = db.get(AuthSession, hash_token(token))
    if row is None:
        return None
    if _aware(row.expires_at) <= utcnow():
        db.delete(row)
        db.commit()
        return None
    if row.role == "guardian":
        g = db.get(Guardian, row.guardian_id) if row.guardian_id else None
        return Principal("guardian", guardian=g, token_hash=row.token_hash) if g else None
    s = db.get(Student, row.student_id) if row.student_id else None
    return Principal("student", student=s, token_hash=row.token_hash) if s else None


def current_principal(p: Annotated[Principal | None, Depends(optional_principal)]) -> Principal:
    if p is None:
        raise HTTPException(401, "Please log in.")
    return p


def current_guardian(p: Annotated[Principal, Depends(current_principal)]) -> Guardian:
    if p.role != "guardian":
        raise HTTPException(403, "This page is for parents and guardians.")
    return p.guardian


def current_student(p: Annotated[Principal, Depends(current_principal)]) -> Student:
    if p.role != "student":
        raise HTTPException(403, "Only a student can do this. Log in as the student.")
    return p.student


def can_read_student(p: Principal, student: Student) -> bool:
    if p.role == "student":
        return p.student.id == student.id
    return student.guardian_id == p.guardian.id


def is_admin(guardian: Guardian, settings: Settings) -> bool:
    return guardian.email_verified_at is not None and guardian.email in settings.admin_email_set


PrincipalDep = Annotated[Principal, Depends(current_principal)]
GuardianDep = Annotated[Guardian, Depends(current_guardian)]
StudentDep = Annotated[Student, Depends(current_student)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
