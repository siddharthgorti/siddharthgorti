"""Deterministic grading. No LLM is needed to check an MCQ index or a number,
and deterministic grading can't be talked into marking a wrong answer right."""

from __future__ import annotations

import math
import re
from fractions import Fraction

_LATEX_FRAC = re.compile(r"\\[dt]?frac\{([^{}]+)\}\{([^{}]+)\}")


def parse_number(text: str) -> float | None:
    s = text.strip().strip("$").replace(" ", "").replace(",", "")
    s = _LATEX_FRAC.sub(r"(\1)/(\2)", s)
    s = s.replace("(", "").replace(")", "")
    if not s:
        return None
    try:
        return float(Fraction(s))
    except (ValueError, ZeroDivisionError):
        pass
    try:
        value = float(s)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def numbers_match(given: str, expected: str, rel_tol: float = 1e-3, abs_tol: float = 1e-6) -> bool:
    a, b = parse_number(given), parse_number(expected)
    return a is not None and b is not None and math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


def grade(question: dict, answer: str) -> tuple[bool, str]:
    """Returns (correct, correct_answer_display)."""
    if question["type"] == "mcq":
        # MCQ answers are the 0-based option index (a letter A-D is also accepted).
        # Matching on option *text* is deliberately not supported: with options
        # like ["1", "2", "3", "4"], "3" would be ambiguous.
        options: list[str] = question["options"]
        key = options[question["answer_index"]]
        given = answer.strip().upper()
        if given.isdigit():
            chosen = int(given)
        elif len(given) == 1 and given in "ABCD":
            chosen = "ABCD".index(given)
        else:
            return False, key
        return chosen == question["answer_index"], key
    return numbers_match(answer, question["numeric_answer"]), question["numeric_answer"]
