"""Pydantic request/response models. These mirror docs/API.md exactly."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PersonaId = Literal["coach", "challenger", "explainer", "mentor"]
Phase = Literal["warmup", "stretch", "peak", "end_high", "complete"]


class PersonaOut(BaseModel):
    id: PersonaId
    name: str
    tagline: str
    description: str


class StudentOut(BaseModel):
    id: str
    name: str
    username: str
    grade: int
    board: str
    persona: PersonaId | None
    created_at: datetime


class OnboardingAnswer(BaseModel):
    question_id: str
    option_index: int


class OnboardingSubmit(BaseModel):
    answers: list[OnboardingAnswer]


class OnboardingResult(BaseModel):
    persona: PersonaOut
    trait_scores: dict[str, float]
    rationale: str


class PersonaUpdate(BaseModel):
    persona_id: PersonaId


class ConceptOut(BaseModel):
    id: str
    name: str
    chapter: int
    prerequisites: list[str]


class SourceOut(BaseModel):
    document: str
    section: str
    snippet: str


class ChatMessageOut(BaseModel):
    role: Literal["student", "tutor"]
    content: str
    created_at: datetime


class PhasePlanItem(BaseModel):
    phase: Phase
    target_problems: int


class SessionCreate(BaseModel):
    concept_id: str = Field(max_length=64)


class SessionStateOut(BaseModel):
    session_id: str
    student_id: str
    concept: ConceptOut
    persona: PersonaOut
    phase: Phase
    problems_in_phase: int
    phase_plan: list[PhasePlanItem]
    mastery: float
    status: Literal["active", "ended"]
    messages: list[ChatMessageOut]


class TurnIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    latency_seconds: float | None = Field(default=None, ge=0, le=86400)


class TurnOut(BaseModel):
    reply: ChatMessageOut
    sources: list[SourceOut]
    affect: Literal["frustration", "boredom", "confusion", "flow", "fatigue", "neutral"]
    phase: Phase
    problems_in_phase: int
    mastery: float
    advice: Literal["continue", "gentle_check", "suggest_stop"]
    teaser: str | None


class SessionEndOut(BaseModel):
    teaser: str
    mastery: float


class SessionSummaryOut(BaseModel):
    session_id: str
    concept: ConceptOut
    started_at: datetime
    ended_at: datetime | None
    turns: int
    mastery_start: float
    mastery_end: float | None


class QuizCreate(BaseModel):
    concept_id: str = Field(max_length=64)
    num_questions: int = Field(default=5, ge=1, le=10)


class QuizQuestionOut(BaseModel):
    id: str
    type: Literal["mcq", "numerical"]
    prompt: str
    options: list[str] | None
    difficulty: float


class QuizOut(BaseModel):
    quiz_id: str
    concept: ConceptOut
    questions: list[QuizQuestionOut]


class AnswerIn(BaseModel):
    question_id: str
    answer: str = Field(min_length=1, max_length=200)


class AnswerOut(BaseModel):
    correct: bool
    correct_answer: str
    explanation: str
    mastery_after: float


class SyllabusDocumentOut(BaseModel):
    id: str
    filename: str
    sections: int
    chunks: int
    uploaded_at: datetime


class HealthOut(BaseModel):
    status: Literal["ok"]
    llm_mode: Literal["anthropic", "ollama", "offline"]
    model: str  # chat model
    quiz_model: str
