"""Phase 2 placeholder: Bayesian Knowledge Tracing.

Note on the spec: FSRS is a spaced-repetition *scheduler* (when to review),
not a knowledge-tracing model (what the student knows). They are complementary:
BKT/DKT would replace `mastery_tracker.ema_update`, and FSRS would decide when
to resurface a mastered concept for review.
"""


def bkt_update(
    p_known: float, correct: bool, p_slip: float = 0.1, p_guess: float = 0.2, p_learn: float = 0.15
) -> float:
    """Standard BKT posterior + learning transition (reference implementation, unused in MVP)."""
    if correct:
        evidence = p_known * (1 - p_slip) / (p_known * (1 - p_slip) + (1 - p_known) * p_guess)
    else:
        evidence = p_known * p_slip / (p_known * p_slip + (1 - p_known) * (1 - p_guess))
    return evidence + (1 - evidence) * p_learn
