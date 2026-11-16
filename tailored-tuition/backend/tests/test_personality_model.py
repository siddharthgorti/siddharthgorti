import itertools

import pytest

from app.student.personality_model import (
    ONBOARDING_QUESTIONS,
    PERSONA_ORDER,
    InvalidAnswersError,
    match_persona,
    public_questions,
    score_answers,
)
from tests.conftest import ANSWERS_COACH

IDS = [q["id"] for q in ONBOARDING_QUESTIONS]


def test_every_persona_is_reachable():
    seen = {
        match_persona(dict(zip(IDS, combo, strict=True))).persona for combo in itertools.product(range(4), repeat=5)
    }
    assert seen == set(PERSONA_ORDER)


def test_scores_are_normalised():
    for combo in itertools.product(range(4), repeat=5):
        traits = score_answers(dict(zip(IDS, combo, strict=True)))
        assert all(0.0 <= v <= 1.0 for v in traits.values())


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        (ANSWERS_COACH, "coach"),
        (
            {
                "motivation_style": 1,
                "pace_preference": 0,
                "engagement_style": 1,
                "feedback_preference": 1,
                "structure_need": 2,
            },
            "challenger",
        ),
        (
            {
                "motivation_style": 2,
                "pace_preference": 2,
                "engagement_style": 2,
                "feedback_preference": 0,
                "structure_need": 0,
            },
            "explainer",
        ),
        (
            {
                "motivation_style": 3,
                "pace_preference": 3,
                "engagement_style": 0,
                "feedback_preference": 3,
                "structure_need": 1,
            },
            "mentor",
        ),
    ],
)
def test_archetypal_answers(answers, expected):
    assert match_persona(answers).persona == expected


def test_missing_and_invalid_answers_rejected():
    with pytest.raises(InvalidAnswersError):
        match_persona({"motivation_style": 0})
    bad = dict(ANSWERS_COACH, motivation_style=7)
    with pytest.raises(InvalidAnswersError):
        match_persona(bad)


def test_public_questions_hide_scores():
    for q in public_questions():
        assert all("scores" not in o for o in q["options"])
