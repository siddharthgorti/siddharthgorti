"""The four tutor personas: metadata for the UI plus prompt text for the LLM.

Note: the spec lists both `persona_manager.py` ("strategy selection") and
`strategizer.py` (PATS: personality -> strategy) with overlapping jobs. In the
MVP, persona choice lives here and per-turn strategy changes come from the
engagement engine (`response_router.py`); `strategizer.py` is a Phase 2 hook.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.tutor.prompts.challenger import CHALLENGER_PERSONA
from app.tutor.prompts.coach import COACH_PERSONA
from app.tutor.prompts.explainer import EXPLAINER_PERSONA
from app.tutor.prompts.mentor import MENTOR_PERSONA


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    tagline: str
    description: str
    prompt: str

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "tagline": self.tagline, "description": self.description}


PERSONAS: dict[str, Persona] = {
    p.id: p
    for p in [
        Persona(
            "coach",
            "The Coach",
            "Warm, patient, in your corner.",
            "Breaks problems into small wins and keeps you going when things get tough. Mistakes are just part of the process.",
            COACH_PERSONA,
        ),
        Persona(
            "challenger",
            "The Challenger",
            "Pushes you to think harder.",
            "Asks 'why?' a lot, raises the bar when you're ready, and enjoys a good puzzle as much as you do.",
            CHALLENGER_PERSONA,
        ),
        Persona(
            "explainer",
            "The Explainer",
            "Clear steps, nothing skipped.",
            "Lays ideas out in order with worked examples, and checks you've got each step before moving on.",
            EXPLAINER_PERSONA,
        ),
        Persona(
            "mentor",
            "The Mentor",
            "Big-picture and curious.",
            "Connects maths to the real world and to other topics, and lets you explore ideas through conversation.",
            MENTOR_PERSONA,
        ),
    ]
}


def get_persona(persona_id: str) -> Persona:
    try:
        return PERSONAS[persona_id]
    except KeyError:
        raise ValueError(f"Unknown persona: {persona_id}") from None
