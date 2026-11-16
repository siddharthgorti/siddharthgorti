import pytest

from app.llm.schemas import QuizItem
from app.quiz.answer_evaluator import grade, numbers_match, parse_number
from app.quiz.quiz_generator import difficulty_band, target_difficulties, validate_item


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("3/4", 0.75),
        (" 0.75 ", 0.75),
        ("$\\frac{3}{4}$", 0.75),
        ("-2", -2.0),
        ("1,000", 1000.0),
        ("abc", None),
        ("1/0", None),
    ],
)
def test_parse_number(text, value):
    assert parse_number(text) == value


def test_numbers_match_tolerance():
    assert numbers_match("0.3333", "1/3")
    assert not numbers_match("0.3", "1/3")


def test_grade_mcq_by_index_or_letter():
    q = {"type": "mcq", "options": ["1", "2", "3", "4"], "answer_index": 2}
    assert grade(q, "2") == (True, "3")
    assert grade(q, "3") == (False, "3")  # index 3, not option text "3"
    assert grade(q, "three") == (False, "3")
    assert grade(q, "c") == (True, "3")
    assert grade(q, "0") == (False, "3")


def test_grade_numerical():
    q = {"type": "numerical", "numeric_answer": "5/2"}
    assert grade(q, "2.5") == (True, "5/2")
    assert grade(q, "2") == (False, "5/2")


def test_bands_are_contiguous():
    assert difficulty_band(0.34).startswith("easy")
    assert difficulty_band(0.35).startswith("medium")
    assert difficulty_band(0.65).startswith("medium")
    assert difficulty_band(0.7).startswith("hard")


def test_target_difficulties_spread_and_bounded():
    ds = target_difficulties(0.5, 5)
    assert ds == sorted(ds) and len(ds) == 5
    assert all(0.1 <= d <= 1.0 for d in target_difficulties(0.0, 5) + target_difficulties(1.0, 5))


def item(**kw):
    base = dict(
        type="mcq",
        prompt="p",
        options=["a", "b", "c", "d"],
        answer_index=0,
        numeric_answer=None,
        explanation="e",
        difficulty=0.5,
    )
    base.update(kw)
    return QuizItem(**base)


def test_validate_item():
    assert validate_item(item())
    assert not validate_item(item(options=["a", "b", "c"]))
    assert not validate_item(item(options=["a", "a", "c", "d"]))
    assert not validate_item(item(answer_index=4))
    assert validate_item(item(type="numerical", options=None, answer_index=None, numeric_answer="3/4"))
    assert not validate_item(item(type="numerical", options=None, answer_index=None, numeric_answer="x+1"))
