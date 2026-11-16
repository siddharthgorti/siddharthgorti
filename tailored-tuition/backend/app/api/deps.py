"""Shared FastAPI dependencies and lookups."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.domain.knowledge_graph import Concept, KnowledgeGraph, get_knowledge_graph
from app.llm.client import LLMClient, get_llm
from app.models import Student, TutorSession
from app.tutor.persona_manager import get_persona

DB = Annotated[Session, Depends(get_db)]
KG = Annotated[KnowledgeGraph, Depends(get_knowledge_graph)]
LLM = Annotated[LLMClient, Depends(get_llm)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def load_student(db: Session, student_id: str) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(404, "Student not found")
    return student


def load_concept(kg: KnowledgeGraph, concept_id: str) -> Concept:
    concept = kg.get(concept_id)
    if concept is None:
        raise HTTPException(404, f"Unknown concept: {concept_id}")
    return concept


def load_session(db: Session, session_id: str) -> TutorSession:
    session = db.get(TutorSession, session_id)
    if session is None:
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
        "grade": s.grade,
        "board": s.board,
        "persona": s.persona,
        "created_at": s.created_at,
    }
