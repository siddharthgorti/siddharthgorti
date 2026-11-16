"""Compare models on the tutor's per-turn answer assessment.

Every chat turn, the model judges whether the student's answer is correct. That judgement drives
mastery and affect, so a model that marks correct answers wrong ("false wrong") does real harm.
This eval replays labelled student messages through the exact production prompt and scores each
model.

Usage (from backend/, with ANTHROPIC_API_KEY set in .env or the environment):

    python -m evals.run_assessment_eval                         # Sonnet 5.5 vs Opus 5.5
    python -m evals.run_assessment_eval --models claude-haiku-5-5 claude-sonnet-5-5
    python -m evals.run_assessment_eval --repeats 3             # measure consistency too
    python -m evals.run_assessment_eval --dry-run               # show the plan and estimated cost only

It asks for confirmation before spending money (skip with --yes).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings, get_settings
from app.domain.knowledge_graph import get_knowledge_graph
from app.domain.rag_pipeline import format_context
from app.engagement.session_designer import FlowState, SessionDesigner
from app.llm.schemas import TutorTurn
from app.tutor.tutor_engine import KICKOFF, build_system

HERE = Path(__file__).resolve().parent
CASES_FILE = HERE / "assessment_cases.json"
RESULTS_DIR = HERE / "results"

# USD per million tokens (input, output), first-party API list prices as of November 2026.
# Check https://www.anthropic.com/pricing before relying on these numbers.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-fable-5-2": (8.00, 40.00),
}
CACHE_WRITE_MULT, CACHE_READ_MULT = 1.25, 0.10
# Rough per-call size for the up-front estimate (system prompt + short history; reply + thinking).
EST_INPUT_TOKENS, EST_OUTPUT_TOKENS = 3000, 1200


@dataclass
class CaseResult:
    case_id: str
    model: str
    expected_kind: str
    expected_correct: bool | None
    kind: str | None = None
    correct: bool | None = None
    latency_s: float = 0.0
    cost_usd: float = 0.0
    error: str | None = None


def load_cases() -> list[dict]:
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]


def build_request(case: dict, settings: Settings) -> tuple[list[dict], list[dict]]:
    concept = get_knowledge_graph().get(case["concept_id"])
    if concept is None:
        raise ValueError(f"{case['id']}: unknown concept {case['concept_id']}")
    system = build_system(
        settings=settings,
        student_name="Asha",
        grade=settings.default_grade,
        board=settings.default_board,
        persona_id="coach",
        concept=concept,
        designer=SessionDesigner(FlowState(phase="stretch")),
        mastery=0.3,
        affect="neutral",
        rag_context=format_context(concept, []),
    )
    messages = [
        {"role": "user", "content": KICKOFF.format(topic=concept.name)},
        {"role": "assistant", "content": case["tutor_problem"]},
        {"role": "user", "content": case["student_answer"]},
    ]
    return system, messages


def call_cost(model: str, usage) -> float:
    if usage is None or model not in PRICES:
        return 0.0
    p_in, p_out = PRICES[model]
    tokens_in = (
        (usage.input_tokens or 0)
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * CACHE_WRITE_MULT
        + (getattr(usage, "cache_read_input_tokens", 0) or 0) * CACHE_READ_MULT
    )
    return (tokens_in * p_in + (usage.output_tokens or 0) * p_out) / 1_000_000


def run_case(llm, case: dict, model: str, effort: str, settings: Settings) -> CaseResult:
    r = CaseResult(case["id"], model, case["expected_kind"], case["expected_correct"])
    system, messages = build_request(case, settings)
    start = time.perf_counter()
    try:
        turn: TutorTurn = llm.structured(system, messages, TutorTurn, effort, model)
        r.kind, r.correct = turn.assessment.kind, turn.assessment.correct
    except Exception as exc:  # report and keep going; one failure shouldn't sink the run
        r.error = f"{type(exc).__name__}: {exc}"
    r.latency_s = round(time.perf_counter() - start, 2)
    r.cost_usd = call_cost(model, getattr(llm, "last_usage", None))
    return r


def score(results: list[CaseResult]) -> dict:
    """Aggregate metrics for one model's results."""
    ok = [r for r in results if r.error is None]
    graded = [r for r in ok if r.expected_correct is not None]
    false_wrong = [r.case_id for r in graded if r.expected_correct and r.correct is not True]
    false_right = [r.case_id for r in graded if not r.expected_correct and r.correct is True]
    kind_hits = sum(1 for r in ok if r.kind == r.expected_kind)
    correct_hits = sum(1 for r in graded if r.correct == r.expected_correct)
    latencies = [r.latency_s for r in ok]
    return {
        "calls": len(results),
        "errors": len(results) - len(ok),
        "kind_accuracy": round(kind_hits / len(ok), 3) if ok else 0.0,
        "correctness_accuracy": round(correct_hits / len(graded), 3) if graded else 0.0,
        "false_wrong": false_wrong,  # correct answers marked wrong: the costliest error for students
        "false_right": false_right,
        "median_latency_s": round(statistics.median(latencies), 2) if latencies else 0.0,
        "total_cost_usd": round(sum(r.cost_usd for r in results), 4),
        "cost_per_turn_usd": round(sum(r.cost_usd for r in results) / len(results), 5) if results else 0.0,
    }


def estimate_cost(models: list[str], n_calls_per_model: int) -> float:
    total = 0.0
    for m in models:
        p_in, p_out = PRICES.get(m, (0.0, 0.0))
        total += n_calls_per_model * (EST_INPUT_TOKENS * p_in + EST_OUTPUT_TOKENS * p_out) / 1_000_000
    return total


def print_report(summary: dict[str, dict]) -> None:
    header = f"{'model':<22}{'correct':>9}{'kind':>7}{'false-wrong':>13}{'false-right':>13}{'p50 s':>8}{'$/turn':>10}"
    print("\n" + header + "\n" + "-" * len(header))
    for model, s in summary.items():
        print(
            f"{model:<22}{s['correctness_accuracy']:>9.0%}{s['kind_accuracy']:>7.0%}"
            f"{len(s['false_wrong']):>13}{len(s['false_right']):>13}{s['median_latency_s']:>8}{s['cost_per_turn_usd']:>10.4f}"
        )
    for model, s in summary.items():
        if s["false_wrong"]:
            print(f"\n{model} marked these CORRECT answers wrong: {', '.join(s['false_wrong'])}")
        if s["false_right"]:
            print(f"{model} accepted these WRONG answers: {', '.join(s['false_right'])}")
        if s["errors"]:
            print(f"{model}: {s['errors']} call(s) failed (see results file)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=["claude-sonnet-5-5", "claude-opus-5-5"])
    parser.add_argument("--effort", default=None, help="defaults to CHAT_EFFORT (production setting)")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None, help="only the first N cases")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="don't ask before spending money")
    args = parser.parse_args(argv)

    settings = get_settings()
    effort = args.effort or settings.chat_effort
    cases = load_cases()[: args.limit]
    for case in cases:  # validate before any spend
        build_request(case, settings)
    n_calls = len(cases) * args.repeats
    estimate = estimate_cost(args.models, n_calls)
    print(f"{len(cases)} cases x {args.repeats} repeat(s) x {len(args.models)} model(s) at effort={effort}")
    print(f"Estimated cost: about ${estimate:.2f} (rough; actual cost is reported after the run)")

    if args.dry_run:
        return 0
    if not settings.anthropic_api_key:
        print("ANTHROPIC_API_KEY is not set. Add it to backend/.env (see README).", file=sys.stderr)
        return 2
    if not args.yes and input("Run it? [y/N] ").strip().lower() != "y":
        print("Cancelled.")
        return 1

    from app.llm.client import AnthropicLLM

    results: dict[str, list[CaseResult]] = {}
    for model in args.models:
        llm = AnthropicLLM(settings)
        print(f"Running {model}...", flush=True)
        # Sequential on purpose: per-call cost is read from llm.last_usage, and
        # sequential calls also give comparable latency numbers.
        results[model] = [run_case(llm, c, model, effort, settings) for c in cases for _ in range(args.repeats)]

    summary = {m: score(rs) for m, rs in results.items()}
    print_report(summary)

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"assessment-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    out.write_text(
        json.dumps(
            {
                "effort": effort,
                "repeats": args.repeats,
                "summary": summary,
                "results": {m: [asdict(r) for r in rs] for m, rs in results.items()},
            },
            indent=1,
        )
    )
    print(f"\nFull results: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
