"""A scripted LLM for deterministic engine/API tests."""

from app.llm.schemas import TurnAssessment, TutorTurn


class ScriptedLLM:
    mode = "offline"
    model = "scripted"

    def __init__(self, assessments=None):
        self.assessments = list(assessments or [])
        self.calls: list[dict] = []

    def structured(self, system, messages, schema, effort):
        self.calls.append({"system": system, "messages": messages, "schema": schema, "effort": effort})
        if messages[-1]["content"].startswith("[SESSION START]") or not self.assessments:
            a = TurnAssessment(kind="other", correct=None, error_tag=None, problem_completed=False)
        else:
            a = self.assessments.pop(0)
        return TutorTurn(assessment=a, reply=f"reply #{len(self.calls)}")


def attempt(correct: bool, tag: str | None = None, done: bool | None = None) -> TurnAssessment:
    return TurnAssessment(
        kind="answer_attempt",
        correct=correct,
        error_tag=None if correct else (tag or "slip"),
        problem_completed=correct if done is None else done,
    )
