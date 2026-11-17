"""Per-student daily usage limits (UTC day). Counted from the data itself, so
they hold across restarts and need no extra table."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Message, Quiz, TutorSession


def _day_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _deny(what: str, limit: int) -> None:
    raise HTTPException(
        429, f"You've reached today's limit of {limit} {what}. It resets at midnight UTC (5:30 am IST)."
    )


def check_new_session(db: Session, student_id: str, settings: Settings) -> None:
    n = db.scalar(
        select(func.count(TutorSession.id)).where(
            TutorSession.student_id == student_id, TutorSession.started_at >= _day_start()
        )
    )
    if n >= settings.max_sessions_per_day:
        _deny("tutoring sessions", settings.max_sessions_per_day)


def check_message(db: Session, student_id: str, settings: Settings) -> None:
    n = db.scalar(
        select(func.count(Message.id))
        .join(TutorSession, Message.session_id == TutorSession.id)
        .where(
            TutorSession.student_id == student_id,
            Message.role == "student",
            Message.created_at >= _day_start(),
        )
    )
    if n >= settings.max_messages_per_day:
        _deny("messages", settings.max_messages_per_day)


def check_quiz(db: Session, student_id: str, settings: Settings) -> None:
    n = db.scalar(select(func.count(Quiz.id)).where(Quiz.student_id == student_id, Quiz.created_at >= _day_start()))
    if n >= settings.max_quizzes_per_day:
        _deny("quizzes", settings.max_quizzes_per_day)
