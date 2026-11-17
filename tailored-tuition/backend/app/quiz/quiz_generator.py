"""Adaptive quiz generation, grounded in syllabus content.

Fix vs. the spec: its difficulty bands (0.0–0.3, 0.4–0.6, 0.7–1.0) left gaps
at 0.3–0.4 and 0.6–0.7 for a continuous score. Bands are now contiguous.

LLM-written answer keys can be wrong. Every item is structurally validated
(4 options, valid index, parseable numeric answer) and invalid ones dropped;
quiz generation uses a higher effort level than chat because key correctness
matters more than latency here.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.knowledge_graph import Concept
from app.domain.rag_pipeline import SYLLABUS_NOTE, Retriever, format_context
from app.llm.client import LLMClient, LLMError
from app.llm.schemas import QuizDraft, QuizItem
from app.quiz.answer_evaluator import parse_number


def difficulty_band(d: float) -> str:
    if d < 0.35:
        return "easy (direct application of a single concept)"
    if d < 0.7:
        return "medium (combine two concepts, or apply in a slightly new context)"
    return "hard (multi-step reasoning, connecting several concepts, or edge cases)"


def target_difficulties(mastery: float, n: int) -> list[float]:
    """Spread from a little below current mastery to a stretch above it."""
    lo, hi = max(0.1, mastery - 0.15), min(1.0, mastery + 0.3)
    if n == 1:
        return [round((lo + hi) / 2, 2)]
    return [round(lo + (hi - lo) * i / (n - 1), 2) for i in range(n)]


def build_prompt(concept: Concept, difficulties: list[float], context: str, grade: int, board: str) -> str:
    lines = "\n".join(f"{i + 1}. difficulty {d:.2f}: {difficulty_band(d)}" for i, d in enumerate(difficulties))
    return f"""Generate {len(difficulties)} quiz questions about "{concept.name}" for a Class {grade} {board} mathematics student.
Concept scope: {concept.description}

Questions, in order, with target difficulty:
{lines}

Rules:
- Mix question types: roughly half "mcq" (exactly 4 options, one correct, plausible distractors based on common mistakes) and half "numerical" (a single exact numeric answer: integer, decimal or simple fraction like 3/4).
- Stay within the syllabus content below. Do not require anything beyond Class {grade}.
- Solve each question yourself before writing the answer key, and double-check it.
- Use LaTeX for maths ($...$). Keep explanations to 1–3 short steps.

SYLLABUS CONTENT ({SYLLABUS_NOTE}):
{context}"""


def validate_item(item: QuizItem) -> bool:
    if item.type == "mcq":
        return (
            item.options is not None
            and len(item.options) == 4
            and len({o.strip() for o in item.options}) == 4
            and item.answer_index is not None
            and 0 <= item.answer_index < 4
        )
    return item.numeric_answer is not None and parse_number(item.numeric_answer) is not None


class QuizGenerator:
    def __init__(self, db: Session, llm: LLMClient, retriever: Retriever, settings: Settings):
        self.db, self.llm, self.retriever, self.settings = db, llm, retriever, settings

    def generate(self, concept: Concept, mastery: float, n: int) -> list[dict]:
        diffs = target_difficulties(mastery, n)
        hits = self.retriever.retrieve(self.db, concept.description, concept, self.settings.rag_top_k)
        prompt = build_prompt(
            concept, diffs, format_context(concept, hits), self.settings.default_grade, self.settings.default_board
        )
        system = [
            {"type": "text", "text": "You write accurate, syllabus-aligned maths assessment items for school students."}
        ]
        draft = self.llm.structured(
            system,
            [{"role": "user", "content": prompt}],
            QuizDraft,
            self.settings.quiz_effort,
            self.settings.quiz_model,
        )
        items = [q for q in draft.questions if validate_item(q)][:n]
        if not items:
            raise LLMError("Couldn't generate valid questions. Please try again.")
        out = []
        for q, d in zip(items, diffs, strict=False):
            out.append(
                {
                    "id": uuid.uuid4().hex[:12],
                    "type": q.type,
                    "prompt": q.prompt,
                    "options": q.options if q.type == "mcq" else None,
                    "answer_index": q.answer_index,
                    "numeric_answer": q.numeric_answer,
                    "explanation": q.explanation,
                    # Trust our target over the model's self-rating, which drifts.
                    "difficulty": d,
                }
            )
        return out


def public_question(q: dict) -> dict:
    return {k: q[k] for k in ("id", "type", "prompt", "options", "difficulty")}
