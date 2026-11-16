"""Phase 2 hook for PATS-style strategy selection.

In the MVP the persona prompt sets the default strategy mix and the engagement
engine overrides it per turn (see `engagement/response_router.py`). A future
strategizer would learn, per student, which strategies actually raise mastery
(e.g. a contextual bandit over strategies, rewarded by mastery gain).
"""


def select_strategy(persona_id: str, affect_override: str | None) -> str | None:
    return affect_override
