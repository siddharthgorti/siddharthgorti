"""Local LLM via Ollama (https://ollama.com): free, offline, no API key.

Trade-offs vs Claude: open models of a size that runs on a laptop are noticeably
weaker at multi-step maths and at judging whether a student's answer is right,
and replies are slower on a machine without a GPU. Use the assessment eval
(`python -m evals.run_assessment_eval`) to measure the gap before relying on it.

Talks to Ollama's HTTP API (`POST /api/chat`) with the standard library only.
Structured output: Ollama's `format` field takes a JSON schema and constrains
generation to it; the schema is also stated in the prompt, which helps small
models fill fields sensibly.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.config import Settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Ollama's default context window is small; the tutor's system prompt plus
# history plus syllabus context needs more, and Ollama truncates silently.
NUM_CTX = 8192
TIMEOUT_S = 300  # CPU-only laptops can take a while per reply
ATTEMPTS = 2  # one retry if the model returns JSON that doesn't fit the schema


def _opener() -> urllib.request.OpenerDirector:
    # Ollama runs on this machine (or the local network): never route it via a proxy.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def ollama_available(base_url: str, timeout: float = 1.0) -> bool:
    try:
        with _opener().open(f"{base_url.rstrip('/')}/api/tags", timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


class OllamaLLM:
    mode = "ollama"

    def __init__(self, settings: Settings):
        self.base_url = settings.ollama_url.rstrip("/")
        self.model = settings.ollama_model
        self.last_usage = None

    def structured(self, system, messages, schema: type[T], effort: str, model: str | None = None) -> T:
        # `effort` and Claude model names don't apply to local models: one model serves everything.
        from app.llm.client import LLMError  # local import: client imports this module

        schema_json = schema.model_json_schema()
        system_text = "\n\n".join(block["text"] for block in system)
        system_text += (
            "\n\nOUTPUT FORMAT: reply with ONLY a JSON object (no prose around it) matching this JSON schema:\n"
            + json.dumps(schema_json)
        )
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_text}, *messages],
            "format": schema_json,
            "stream": False,
            "options": {"num_ctx": NUM_CTX, "temperature": 0.3},
        }
        last_error: Exception | None = None
        for _ in range(ATTEMPTS):
            data = self._post("/api/chat", body, LLMError)
            content = (data.get("message") or {}).get("content", "")
            try:
                return schema.model_validate_json(content)
            except ValidationError as exc:
                last_error = exc
                log.warning("Ollama returned output that doesn't fit %s; retrying", schema.__name__)
        raise LLMError("The local model gave an unusable answer. Please try again.") from last_error

    def _post(self, path: str, body: dict, error_cls: type[Exception]) -> dict:
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with _opener().open(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            if exc.code == 404 and "not found" in detail.lower():
                raise error_cls(
                    f"The local model '{self.model}' isn't downloaded yet. Run: ollama pull {self.model}"
                ) from exc
            log.error("Ollama HTTP %s: %s", exc.code, detail)
            raise error_cls("The local model returned an error. Please try again.") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise error_cls("Can't reach Ollama. Is the Ollama app running?") from exc
        except json.JSONDecodeError as exc:
            raise error_cls("The local model sent a malformed response.") from exc
