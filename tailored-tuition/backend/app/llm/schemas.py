"""Structured-output schemas the LLM must fill.

Asking for structure (instead of free text) is what lets the tutor's judgement
feed the mastery tracker and affect detector without a second LLM call.
"""

from typing import Literal

from pydantic import BaseModel, Field


class TurnAssessment(BaseModel):
    """The tutor's reading of the student's most recent message."""

    kind: Literal["answer_attempt", "question", "help_request", "chitchat", "other"] = Field(
        description="What the student's latest message mainly is."
    )
    correct: bool | None = Field(
        description="For answer_attempt only: is the student's answer/step mathematically correct? null otherwise."
    )
    error_tag: str | None = Field(
        description=(
            "For incorrect attempts: a short snake_case label for the misconception, "
            "e.g. 'sign_error' or 'confuses_union_intersection'. Reuse the same label "
            "if the student repeats the same mistake. null otherwise."
        )
    )
    problem_completed: bool = Field(
        description=(
            "True if this exchange finishes the current practice problem (the student "
            "solved it, or you have now walked through the full solution)."
        )
    )


class TutorTurn(BaseModel):
    assessment: TurnAssessment
    reply: str = Field(description="Your message to the student, in Markdown with LaTeX maths ($...$).")


class QuizItem(BaseModel):
    type: Literal["mcq", "numerical"]
    prompt: str = Field(description="Question text, Markdown with LaTeX maths ($...$).")
    options: list[str] | None = Field(description="Exactly 4 options for mcq; null for numerical.")
    answer_index: int | None = Field(description="0-based index of the correct option for mcq; null for numerical.")
    numeric_answer: str | None = Field(
        description="For numerical: the exact answer as an integer, decimal or fraction like '3/4'; null for mcq."
    )
    explanation: str = Field(description="Short worked explanation, Markdown with LaTeX.")
    difficulty: float = Field(description="0.0 (easiest) to 1.0 (hardest).")


class QuizDraft(BaseModel):
    questions: list[QuizItem]


class Teaser(BaseModel):
    text: str = Field(description="1-2 sentences previewing the next concept. No urgency or guilt.")
