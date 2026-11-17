"""Shared FastAPI dependencies and lookups."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.domain.knowledge_graph import Concept, KnowledgeGraph, get_knowledge_graph
from app.llm.client import LLMClient, get_llm
from app.models import Guardian, Student, TutorSession
from app.security.auth import Principal, can_read_student, is_admin
from app.tutor.persona_manager import get_persona

DB = Annotated[Session, Depends(get_db)]
KG = Annotated[KnowledgeGraph, Depends(get_knowledge_graph)]
LLM = Annotated[LLMClient, Depends(get_llm)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def load_student(db: Session, student_id: str, p: Principal) -> Student:
    """The student, if `p` may read them. Someone else's student looks exactly
    like a missing one (404), so ids can't be probed."""
    student = db.get(Student, student_id)
    if student is None or not can_read_student(p, student):
        raise HTTPException(404, "Student not found")
    return student


def require_self(p: Principal, student_id: str) -> Student:
    """For actions only the student themself may take (chatting, quizzes, onboarding)."""
    if p.role != "student":
        raise HTTPException(403, "Only the student can do this. Log in as the student.")
    if p.student.id != student_id:
        raise HTTPException(404, "Student not found")
    return p.student


def load_concept(kg: KnowledgeGraph, concept_id: str) -> Concept:
    concept = kg.get(concept_id)
    if concept is None:
        raise HTTPException(404, f"Unknown concept: {concept_id}")
    return concept


def load_session(db: Session, session_id: str, p: Principal) -> TutorSession:
    session = db.get(TutorSession, session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    student = db.get(Student, session.student_id)
    if student is None or not can_read_student(p, student):
        raise HTTPException(404, "Session not found")
    return session


def concept_out(c: Concept) -> dict:
    return {"id": c.id, "name": c.name, "chapter": c.chapter, "prerequisites": list(c.prerequisites)}


def persona_out(persona_id: str) -> dict:
    return get_persona(persona_id).public()


def student_out(s: Student) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "username": s.username,
        "grade": s.grade,
        "board": s.board,
        "persona": s.persona,
        "created_at": s.created_at,
    }


def guardian_out(g: Guardian, settings: Settings) -> dict:
    return {
        "id": g.id,
        "name": g.name,
        "email": g.email,
        "email_verified": g.email_verified_at is not None,
        "is_admin": is_admin(g, settings),
        "created_at": g.created_at,
    }
