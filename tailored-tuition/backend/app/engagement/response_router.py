"""Map a detected affective state to a pedagogical adaptation."""

from __future__ import annotations

from dataclasses import dataclass

# One "difficulty step" on the 0..1 scale. The spec used ±1 without a unit.
DIFFICULTY_STEP = 0.15


@dataclass(frozen=True)
class Adaptation:
    strategy_override: str | None
    prompt_injection: str
    difficulty_adjustment: int  # in DIFFICULTY_STEP units


AFFECT_ADAPTATIONS: dict[str, Adaptation] = {
    "frustration": Adaptation(
        "step_by_step_scaffolding",
        "The student seems frustrated (repeated mistakes). Acknowledge that this is genuinely tricky, "
        "simplify, and break the problem into smaller steps. Do NOT increase the challenge.",
        -1,
    ),
    "boredom": Adaptation(
        "task_variety",
        "The student is answering quickly and correctly and may be under-challenged. Raise the challenge "
        "or switch to a different type of problem or a real-world application.",
        +1,
    ),
    "confusion": Adaptation(
        "worked_examples",
        "The student seems confused. First ask which specific part is unclear, then try a different "
        "explanation: an analogy or a short worked example of a *similar* problem.",
        0,
    ),
    "flow": Adaptation(
        None,
        "The student is engaged and doing well. Don't interrupt the momentum; keep the current approach "
        "and nudge the difficulty up slightly.",
        0,
    ),
    "fatigue": Adaptation(
        "session_wrap",
        "The student is showing signs of tiredness. Start wrapping up: give one final problem they can "
        "comfortably solve, and tell them this is a good place to stop.",
        -1,
    ),
    "neutral": Adaptation(None, "", 0),
}


def adaptation_for(affect: str) -> Adaptation:
    return AFFECT_ADAPTATIONS.get(affect, AFFECT_ADAPTATIONS["neutral"])
