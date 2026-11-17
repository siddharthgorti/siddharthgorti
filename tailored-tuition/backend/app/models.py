"""ORM models: guardians, students, login sessions, tutoring, syllabus and quizzes.

Data minimisation: we store what tutoring and progress need, nothing more. The
onboarding quiz's personality-trait scores are shown once and NOT stored; only
the chosen tutor persona is kept.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Guardian(Base):
    """A parent or guardian: the adult account holder who consents for children."""

    __tablename__ = "guardians"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)  # stored lower-case
    password_hash: Mapped[str] = mapped_column(String(255))
    email_verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    students: Mapped[list["Student"]] = relationship(back_populates="guardian", order_by="Student.created_at")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    guardian_id: Mapped[str] = mapped_column(ForeignKey("guardians.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True)  # stored lower-case
    password_hash: Mapped[str] = mapped_column(String(255))
    grade: Mapped[int] = mapped_column(Integer, default=11)
    board: Mapped[str] = mapped_column(String(20), default="CBSE")
    persona: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Consent record: the guardian (guardian_id) consented, when, to which notice version.
    consent_given_at: Mapped[datetime] = mapped_column()
    consent_policy_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    guardian: Mapped[Guardian] = relationship(back_populates="students")
    mastery: Mapped[list["Mastery"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class AuthSession(Base):
    """A login. The cookie holds a random token; only its SHA-256 is stored."""

    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(10))  # "guardian" | "student"
    guardian_id: Mapped[str | None] = mapped_column(
        ForeignKey("guardians.id", ondelete="CASCADE"), nullable=True, index=True
    )
    student_id: Mapped[str | None] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime] = mapped_column()


class EmailToken(Base):
    """Single-use email link (verification or password reset). Only the hash is stored."""

    __tablename__ = "email_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    guardian_id: Mapped[str] = mapped_column(ForeignKey("guardians.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(10))  # "verify" | "reset"
    expires_at: Mapped[datetime] = mapped_column()
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)


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
    started_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
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
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

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
    answered: Mapped[dict] = mapped_column(JSON, default=dict)  # question_id -> {"answer", "correct"}
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
