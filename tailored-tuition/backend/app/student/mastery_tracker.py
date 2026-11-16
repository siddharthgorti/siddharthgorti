"""Per-concept mastery on a 0..1 scale.

The spec called its rule an "exponential moving average" but it was additive
(+0.1·(1+d) / −0.05·d). That rule lets a student reach 1.0 by answering ~5 easy
questions, and makes wrong answers on easy questions nearly free.

This is a real EMA toward an evidence target:

    correct: target = min(1, difficulty + CEILING_MARGIN)   (only moves up)
    wrong:   target = 0
    new = old + RATE · weight · (target − old)

* Easy questions can't certify mastery: the target is capped near the
  question's difficulty, so reaching 0.8 needs problems of difficulty ≥ 0.4.
* Weighting follows surprise: a correct answer on a hard question, or a wrong
  answer on an easy one, moves the estimate more.

Phase 2 (`knowledge_tracing.py`) can replace this with BKT using the same
interface.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Mastery

RATE = 0.35
CEILING_MARGIN = 0.4


def ema_update(current: float, correct: bool, difficulty: float) -> float:
    d = min(1.0, max(0.0, difficulty))
    if correct:
        target = min(1.0, d + CEILING_MARGIN)
        if target <= current:
            return current
        weight = 0.5 + d  # 0.5 .. 1.5
    else:
        target = 0.0
        weight = 1.5 - d  # 1.5 .. 0.5
    new = current + RATE * weight * (target - current)
    return round(min(1.0, max(0.0, new)), 4)


class MasteryTracker:
    def __init__(self, db: Session):
        self.db = db

    def _row(self, student_id: str, concept_id: str) -> Mastery | None:
        return self.db.scalar(select(Mastery).where(Mastery.student_id == student_id, Mastery.concept_id == concept_id))

    def get_level(self, student_id: str, concept_id: str) -> float:
        row = self._row(student_id, concept_id)
        return row.level if row else 0.0

    def all_levels(self, student_id: str) -> dict[str, Mastery]:
        return {m.concept_id: m for m in self.db.scalars(select(Mastery).where(Mastery.student_id == student_id))}

    def update(self, student_id: str, concept_id: str, correct: bool, difficulty: float) -> float:
        row = self._row(student_id, concept_id)
        if row is None:
            row = Mastery(student_id=student_id, concept_id=concept_id, level=0.0, attempts=0, correct=0)
            self.db.add(row)
        row.level = ema_update(row.level, correct, difficulty)
        row.attempts += 1
        row.correct += int(correct)
        self.db.flush()
        return row.level
