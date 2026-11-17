from app.config import get_settings
from app.llm.schemas import TurnAssessment, TutorTurn
from evals.run_assessment_eval import CaseResult, build_request, estimate_cost, load_cases, main, run_case, score


def test_cases_are_well_formed_and_balanced():
    cases = load_cases()
    assert len(cases) >= 20
    assert len({c["id"] for c in cases}) == len(cases)
    for c in cases:
        build_request(c, get_settings())  # concept exists, prompt builds
        if c["expected_kind"] == "answer_attempt":
            assert isinstance(c["expected_correct"], bool)
        else:
            assert c["expected_correct"] is None
    assert sum(c["expected_correct"] is True for c in cases) >= 5
    assert sum(c["expected_correct"] is False for c in cases) >= 5


def test_request_uses_production_prompt_and_alternates():
    system, messages = build_request(load_cases()[0], get_settings())
    assert "ASSESSMENT (structured output)" in system[0]["text"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]


def test_scoring():
    rs = [
        CaseResult("a", "m", "answer_attempt", True, "answer_attempt", True, 1.0, 0.01),
        CaseResult("b", "m", "answer_attempt", True, "answer_attempt", False, 2.0, 0.01),  # false wrong
        CaseResult("c", "m", "answer_attempt", False, "answer_attempt", True, 3.0, 0.01),  # false right
        CaseResult("d", "m", "question", None, "question", None, 1.0, 0.01),
        CaseResult("e", "m", "answer_attempt", True, error="boom"),
    ]
    s = score(rs)
    assert s["false_wrong"] == ["b"] and s["false_right"] == ["c"]
    assert s["correctness_accuracy"] == round(1 / 3, 3)
    assert s["kind_accuracy"] == 1.0 and s["errors"] == 1
    assert s["median_latency_s"] == 1.5


def test_run_case_with_fake_llm_records_model_and_errors():
    case = load_cases()[0]

    class Fake:
        last_usage = None

        def __init__(self, fail=False):
            self.fail, self.models = fail, []

        def structured(self, system, messages, schema, effort, model=None):
            self.models.append(model)
            if self.fail:
                raise RuntimeError("api down")
            a = TurnAssessment(kind="answer_attempt", correct=True, error_tag=None, problem_completed=True)
            return TutorTurn(assessment=a, reply="ok")

    fake = Fake()
    r = run_case(fake, case, "claude-sonnet-5-5", "low", get_settings())
    assert (r.kind, r.correct, r.error) == ("answer_attempt", True, None) and fake.models == ["claude-sonnet-5-5"]
    assert "api down" in run_case(Fake(fail=True), case, "x", "low", get_settings()).error


def test_cost_estimate_and_dry_run(capsys):
    assert estimate_cost(["claude-opus-5-5"], 10) == 2 * estimate_cost(["claude-sonnet-5-5"], 10)
    assert main(["--dry-run"]) == 0
    assert "Estimated cost" in capsys.readouterr().out


def test_refuses_without_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "anthropic_api_key", None)
    assert main(["--yes", "--limit", "1"]) == 2


def test_local_model_eval_runs_without_key_or_confirmation(monkeypatch, capsys):
    from tests.test_ollama import GOOD, FakeOllama

    f = FakeOllama(replies=[__import__("json").dumps(GOOD)])
    try:
        monkeypatch.setattr(get_settings(), "anthropic_api_key", None)
        monkeypatch.setattr(get_settings(), "ollama_url", f.url)
        monkeypatch.setattr(
            "evals.run_assessment_eval.RESULTS_DIR", __import__("pathlib").Path(__import__("tempfile").mkdtemp())
        )
        assert main(["--models", "qwen2.5:7b", "--limit", "2"]) == 0  # no input() prompt: would raise in pytest
        assert {r["model"] for r in f.requests} == {"qwen2.5:7b"}
        assert "qwen2.5:7b" in capsys.readouterr().out
    finally:
        f.close()
