"""LLM access behind a small interface.

`AnthropicLLM` calls Claude with structured outputs. `OfflineLLM` returns
deterministic stub content so the app (and the test-suite) run with no API key.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.config import Settings, get_settings
from app.llm.schemas import QuizDraft, QuizItem, Teaser, TurnAssessment, TutorTurn

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

SystemBlocks = list[dict]  # Anthropic system content blocks
Messages = list[dict]  # [{"role": "user"|"assistant", "content": str}]


class LLMError(RuntimeError):
    """Raised when the model cannot produce a usable response."""


class LLMClient(Protocol):
    mode: str
    model: str

    def structured(
        self, system: SystemBlocks, messages: Messages, schema: type[T], effort: str, model: str | None = None
    ) -> T: ...


class AnthropicLLM:
    mode = "anthropic"

    def __init__(self, settings: Settings):
        import anthropic

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=3, timeout=120.0)
        self.model = settings.chat_model  # default when a call doesn't name one
        self._fallbacks = settings.enable_refusal_fallbacks
        self.last_usage = None  # token usage of the most recent call (read by evals)

    def structured(
        self, system: SystemBlocks, messages: Messages, schema: type[T], effort: str, model: str | None = None
    ) -> T:
        kwargs: dict = {}
        if self._fallbacks:
            # On a safety-classifier decline the API re-runs the request on a
            # fallback model inside the same call, so students aren't left hanging.
            kwargs = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        try:
            response = self._client.beta.messages.parse(
                model=model or self.model,
                max_tokens=16000,
                system=system,
                messages=messages,
                output_format=schema,
                output_config={"effort": effort},
                **kwargs,
            )
        except self._anthropic.RateLimitError as exc:
            raise LLMError("The tutor is busy right now. Please try again in a moment.") from exc
        except self._anthropic.APIStatusError as exc:
            log.exception("Anthropic API error %s", exc.status_code)
            raise LLMError("The tutor service returned an error. Please try again.") from exc
        except self._anthropic.APIConnectionError as exc:
            raise LLMError("Could not reach the tutor service. Check your connection.") from exc

        self.last_usage = response.usage
        if response.stop_reason == "refusal":
            raise LLMError("The tutor couldn't respond to that message. Try rephrasing it.")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise LLMError("The tutor's response was incomplete. Please try again.")
        return response.parsed_output


class OfflineLLM:
    """Deterministic stand-in used when no API key is configured.

    It exercises every code path (assessment, phase changes, quizzes) but its
    content is obviously canned, and it says so.
    """

    mode = "offline"
    model = "offline-stub"

    _HELP = re.compile(r"\b(help|stuck|don'?t (get|understand)|confused|no idea|hint)\b", re.I)

    def structured(
        self, system: SystemBlocks, messages: Messages, schema: type[T], effort: str, model: str | None = None
    ) -> T:
        last = messages[-1]["content"] if messages else ""
        if schema is TutorTurn:
            return self._tutor_turn(system, last)  # type: ignore[return-value]
        if schema is QuizDraft:
            return self._quiz(last)  # type: ignore[return-value]
        if schema is Teaser:
            return Teaser(text="Next time we'll build on what you did today. Ready when you are.")  # type: ignore[return-value]
        raise LLMError(f"Offline mode has no stub for {schema.__name__}")

    def _tutor_turn(self, system: SystemBlocks, last: str) -> TutorTurn:
        sys_text = "\n".join(b["text"] for b in system)
        topic = _grab(sys_text, r"CURRENT TOPIC: (.+)") or "this topic"
        phase = _grab(sys_text, r"SESSION PHASE: (\w+)") or "warmup"
        note = "_(Offline demo mode — add an `ANTHROPIC_API_KEY` for real tutoring.)_\n\n"
        if last.startswith("[SESSION START]"):
            return TutorTurn(
                assessment=TurnAssessment(kind="other", correct=None, error_tag=None, problem_completed=False),
                reply=note + f"Hi! Today we're working on **{topic}**. Warm-up: what is $2 + 3$?",
            )
        if self._HELP.search(last):
            return TutorTurn(
                assessment=TurnAssessment(kind="help_request", correct=None, error_tag=None, problem_completed=False),
                reply=note + "No problem. What part feels unclear — the idea itself, or the first step?",
            )
        if re.search(r"\d", last):
            correct = not re.search(r"\b(wrong|not sure|guess)\b", last, re.I)
            return TutorTurn(
                assessment=TurnAssessment(
                    kind="answer_attempt",
                    correct=correct,
                    error_tag=None if correct else "unsure_attempt",
                    problem_completed=correct,
                ),
                reply=note
                + (
                    f"Nice work. ({phase} phase) Next one: what is $3 \\times 4$?"
                    if correct
                    else "Close — what would you check first?"
                ),
            )
        return TutorTurn(
            assessment=TurnAssessment(kind="question", correct=None, error_tag=None, problem_completed=False),
            reply=note + f"Good question about {topic}. What do you think the first step is?",
        )

    def _quiz(self, prompt: str) -> QuizDraft:
        n = int(_grab(prompt, r"Generate (\d+)") or 5)
        items = []
        for i in range(n):
            a, b = i + 2, i + 5
            if i % 2 == 0:
                items.append(
                    QuizItem(
                        type="mcq",
                        prompt=f"_(Offline sample)_ What is ${a} + {b}$?",
                        options=[str(a + b - 1), str(a + b), str(a + b + 1), str(a * b)],
                        answer_index=1,
                        numeric_answer=None,
                        explanation=f"${a} + {b} = {a + b}$.",
                        difficulty=round(0.2 + 0.1 * i, 2),
                    )
                )
            else:
                items.append(
                    QuizItem(
                        type="numerical",
                        prompt=f"_(Offline sample)_ Compute ${a} \\times {b}$.",
                        options=None,
                        answer_index=None,
                        numeric_answer=str(a * b),
                        explanation=f"${a} \\times {b} = {a * b}$.",
                        difficulty=round(0.2 + 0.1 * i, 2),
                    )
                )
        return QuizDraft(questions=items)


def _grab(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


@lru_cache
def get_llm() -> LLMClient:
    settings = get_settings()
    if settings.resolved_llm_mode == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("LLM_MODE=anthropic but ANTHROPIC_API_KEY is not set")
        return AnthropicLLM(settings)
    log.warning("No ANTHROPIC_API_KEY set: running in offline demo mode")
    return OfflineLLM()
