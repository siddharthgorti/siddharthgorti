"""Session flow: warm-up -> stretch -> peak -> end-high (Peak-End rule).

Fixes vs. the spec:
  * The spec returned `transition_after` but had no method that advanced the
    phase, and `peak_achieved` was never set. This is an explicit state machine.
  * Difficulties are clamped to [0.1, 1.0] in every phase (stretch wasn't).
  * Unknown phases no longer fall through and return None.
  * Fatigue (or the student asking to stop) jumps straight to end-high, so the
    session always ends on a success rather than being cut off mid-struggle.
  * State is a plain dict so it persists with the session row.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.engagement.response_router import DIFFICULTY_STEP

PHASE_PLAN: list[tuple[str, int]] = [("warmup", 2), ("stretch", 4), ("peak", 1), ("end_high", 1)]
PHASE_OFFSETS = {"warmup": -0.2, "stretch": 0.1, "peak": 0.3, "end_high": -0.3}
PHASES = [p for p, _ in PHASE_PLAN] + ["complete"]
MIN_D, MAX_D = 0.1, 1.0


@dataclass
class FlowState:
    phase: str = "warmup"
    problems_in_phase: int = 0
    peak_achieved: bool = False
    difficulty_offset: float = 0.0  # running affect adjustment, bounded
    wrap_requested: bool = False

    @classmethod
    def from_dict(cls, d: dict | None) -> FlowState:
        return cls(**{k: v for k, v in (d or {}).items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> dict:
        return asdict(self)


def _clamp(x: float) -> float:
    return round(min(MAX_D, max(MIN_D, x)), 3)


class SessionDesigner:
    def __init__(self, state: FlowState):
        self.state = state

    @staticmethod
    def plan() -> list[dict]:
        return [{"phase": p, "target_problems": n} for p, n in PHASE_PLAN]

    def target_difficulty(self, mastery: float) -> float:
        if self.state.phase == "complete":
            return _clamp(mastery - 0.3)
        return _clamp(mastery + PHASE_OFFSETS[self.state.phase] + self.state.difficulty_offset)

    def apply_affect(self, difficulty_adjustment: int) -> None:
        """Accumulate affect-driven nudges, bounded to ±2 steps."""
        if self.state.phase in ("end_high", "complete"):
            return
        new = self.state.difficulty_offset + difficulty_adjustment * DIFFICULTY_STEP
        self.state.difficulty_offset = round(max(-2 * DIFFICULTY_STEP, min(2 * DIFFICULTY_STEP, new)), 3)

    def request_wrap_up(self) -> None:
        """Skip to the end-high problem (fatigue or student wants to stop)."""
        if self.state.phase not in ("end_high", "complete"):
            self.state.phase = "end_high"
            self.state.problems_in_phase = 0
            self.state.difficulty_offset = 0.0
            self.state.wrap_requested = True

    def record_problem_completed(self, solved_independently: bool) -> None:
        if self.state.phase == "complete":
            return
        if self.state.phase == "peak" and solved_independently:
            self.state.peak_achieved = True
        self.state.problems_in_phase += 1
        target = dict(PHASE_PLAN)[self.state.phase]
        if self.state.problems_in_phase >= target:
            self.state.phase = PHASES[PHASES.index(self.state.phase) + 1]
            self.state.problems_in_phase = 0
            if self.state.phase in ("end_high", "complete"):
                self.state.difficulty_offset = 0.0

    def phase_instruction(self, mastery: float) -> str:
        d = self.target_difficulty(mastery)
        phase = self.state.phase
        if phase == "complete":
            return (
                "The planned session is complete. Congratulate the student specifically on what they did today, "
                "and let them know this is a natural place to stop. If they want to continue, keep problems easy-to-moderate."
            )
        guidance = {
            "warmup": "Warm-up: pose a problem a little BELOW their current level to build confidence.",
            "stretch": "Stretch: pose problems slightly ABOVE their current level (their zone of proximal development).",
            "peak": "Peak: pose the hardest problem they can realistically crack with effort — a memorable win.",
            "end_high": "End-high: pose one problem they can comfortably solve so the session ends on success.",
        }[phase]
        total = dict(PHASE_PLAN)[phase]
        return (
            f"{guidance} Target difficulty ≈ {d:.2f} on a 0–1 scale "
            f"(0.0–0.35 single-step recall/application, 0.35–0.7 combine two ideas or a new context, "
            f"0.7–1.0 multi-step reasoning or edge cases). Problem {self.state.problems_in_phase + 1} of {total} in this phase. "
            "Work on ONE problem at a time."
        )
