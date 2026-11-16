"""Mastery map and session history."""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DB, KG, concept_out, load_student
from app.api.schemas import SessionSummaryOut
from app.engagement.progress_viz import mastery_map
from app.models import TutorSession
from app.student.mastery_tracker import MasteryTracker

router = APIRouter(prefix="/api/students", tags=["progress"])


@router.get("/{student_id}/mastery-map")
def get_mastery_map(student_id: str, db: DB, kg: KG) -> dict:
    load_student(db, student_id)
    return mastery_map(kg, MasteryTracker(db).all_levels(student_id))


@router.get("/{student_id}/sessions", response_model=list[SessionSummaryOut])
def session_history(student_id: str, db: DB, kg: KG):
    load_student(db, student_id)
    sessions = db.scalars(
        select(TutorSession).where(TutorSession.student_id == student_id).order_by(TutorSession.started_at.desc())
    )
    levels = {cid: m.level for cid, m in MasteryTracker(db).all_levels(student_id).items()}
    out = []
    for s in sessions:
        concept = kg.get(s.concept_id)
        if concept is None:
            continue
        out.append(
            {
                "session_id": s.id,
                "concept": concept_out(concept),
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "turns": sum(1 for m in s.messages if m.role == "student"),
                "mastery_start": s.mastery_start,
                "mastery_end": s.mastery_end if s.status == "ended" else levels.get(s.concept_id, 0.0),
            }
        )
    return out
