"""ORM models: the persistent state of students, sessions, syllabus and quizzes."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(80))
    grade: Mapped[int] = mapped_column(Integer, default=11)
    board: Mapped[str] = mapped_column(String(20), default="CBSE")
    guardian_consent_at: Mapped[datetime] = mapped_column()
    persona: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trait_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    mastery: Mapped[list["Mastery"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Mastery(Base):
    __tablename__ = "mastery"
    __table_args__ = (UniqueConstraint("student_id", "concept_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    concept_id: Mapped[str] = mapped_column(String(64))
    level: Mapped[float] = mapped_column(Float, default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    student: Mapped[Student] = relationship(back_populates="mastery")


class TutorSession(Base):
    __tablename__ = "tutor_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[str] = mapped_column(String(64))
    persona: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(10), default="active")
    # Serialised SessionDesigner / affect state, so a session survives restarts.
    flow_state: Mapped[dict] = mapped_column(JSON, default=dict)
    mastery_start: Mapped[float] = mapped_column(Float, default=0.0)
    mastery_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    teaser: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("tutor_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # "student" | "tutor"
    content: Mapped[str] = mapped_column(Text)
    # Per-turn analytics: affect, assessment, sources, latency.
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    session: Mapped[TutorSession] = relationship(back_populates="messages")


class SyllabusDocument(Base):
    __tablename__ = "syllabus_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(default=utcnow)

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("syllabus_documents.id", ondelete="CASCADE"), index=True)
    section: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    concept_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    document: Mapped[SyllabusDocument] = relationship(back_populates="chunks")


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[str] = mapped_column(String(64))
    # List of question dicts including answer keys (never sent to the client).
    questions: Mapped[list] = mapped_column(JSON)
    answered: Mapped[dict] = mapped_column(JSON, default=dict)  # question_id -> bool
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
