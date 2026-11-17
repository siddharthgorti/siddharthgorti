"""OllamaLLM against a fake Ollama HTTP server (no real model needed)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.config import Settings
from app.llm.client import LLMError
from app.llm.ollama import NUM_CTX, OllamaLLM, ollama_available
from app.llm.schemas import TutorTurn

GOOD = {
    "assessment": {"kind": "answer_attempt", "correct": True, "error_tag": None, "problem_completed": True},
    "reply": "Nice: $A \\cup B = \\{1,2,3\\}$. What is $A \\cap B$?",
}


class FakeOllama:
    def __init__(self, replies=None, status=200, error_body=""):
        self.replies = list(replies or [json.dumps(GOOD)])
        self.status, self.error_body = status, error_body
        self.requests: list[dict] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, code, payload):
                data = json.dumps(payload).encode() if not isinstance(payload, bytes) else payload
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._send(200, {"models": []})

            def do_POST(self):
                fake.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                if fake.status != 200:
                    self._send(fake.status, fake.error_body.encode())
                    return
                content = fake.replies.pop(0) if len(fake.replies) > 1 else fake.replies[0]
                self._send(200, {"message": {"role": "assistant", "content": content}, "done": True})

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


@pytest.fixture
def fake():
    servers = []

    def make(**kw):
        servers.append(FakeOllama(**kw))
        return servers[-1]

    yield make
    for s in servers:
        s.close()


def llm_for(url, model="qwen2.5:7b"):
    return OllamaLLM(Settings(ollama_url=url, ollama_model=model, anthropic_api_key=None))


SYSTEM = [
    {"type": "text", "text": "You are a tutor.", "cache_control": {"type": "ephemeral"}},
    {"type": "text", "text": "TOPIC: Sets"},
]
MSGS = [{"role": "user", "content": "{1,2,3}"}]


def test_request_shape_and_parsing(fake):
    f = fake()
    turn = llm_for(f.url).structured(SYSTEM, MSGS, TutorTurn, "low", "claude-sonnet-5-5")
    assert turn.assessment.correct is True and "A \\cup B" in turn.reply
    body = f.requests[0]
    assert body["model"] == "qwen2.5:7b"  # Claude model names are ignored locally
    assert body["stream"] is False and body["options"]["num_ctx"] == NUM_CTX
    assert body["format"]["title"] == "TutorTurn"
    assert body["messages"][0]["role"] == "system"
    assert "You are a tutor." in body["messages"][0]["content"] and "TOPIC: Sets" in body["messages"][0]["content"]
    assert "JSON schema" in body["messages"][0]["content"]
    assert body["messages"][1:] == MSGS


def test_retries_once_on_output_that_does_not_fit_schema(fake):
    f = fake(replies=['{"reply": "missing assessment"}', json.dumps(GOOD)])
    assert llm_for(f.url).structured(SYSTEM, MSGS, TutorTurn, "low").reply == GOOD["reply"]
    assert len(f.requests) == 2


def test_gives_up_after_retry(fake):
    f = fake(replies=["not json at all"])
    with pytest.raises(LLMError, match="unusable"):
        llm_for(f.url).structured(SYSTEM, MSGS, TutorTurn, "low")
    assert len(f.requests) == 2


def test_missing_model_tells_you_the_pull_command(fake):
    f = fake(status=404, error_body='{"error":"model \\"qwen2.5:7b\\" not found, try pulling it first"}')
    with pytest.raises(LLMError, match="ollama pull qwen2.5:7b"):
        llm_for(f.url).structured(SYSTEM, MSGS, TutorTurn, "low")


def test_not_running_is_a_clear_error():
    with pytest.raises(LLMError, match="Is the Ollama app running"):
        llm_for("http://127.0.0.1:9").structured(SYSTEM, MSGS, TutorTurn, "low")


def test_availability_probe(fake):
    assert ollama_available(fake().url)
    assert not ollama_available("http://127.0.0.1:9", timeout=0.3)


def test_auto_mode_prefers_key_then_ollama_then_offline(fake):
    f = fake()
    assert Settings(llm_mode="auto", anthropic_api_key="k", ollama_url=f.url).resolved_llm_mode == "anthropic"
    assert Settings(llm_mode="auto", anthropic_api_key=None, ollama_url=f.url).resolved_llm_mode == "ollama"
    assert (
        Settings(llm_mode="auto", anthropic_api_key=None, ollama_url="http://127.0.0.1:9").resolved_llm_mode
        == "offline"
    )


def test_full_tutoring_turn_through_api(fake, use_llm, onboarded_student):
    client = onboarded_student
    f = fake()
    use_llm(llm_for(f.url))
    s = client.post("/api/sessions", json={"concept_id": "set_operations"})
    assert s.status_code == 201, s.text
    t = client.post(
        f"/api/sessions/{s.json()['session_id']}/messages", json={"content": "{1,2,3}", "latency_seconds": 8}
    )
    assert t.status_code == 200, t.text
    assert t.json()["mastery"] > 0 and "A \\cup B" in t.json()["reply"]["content"]
    assert "PERSONA: The Coach" in f.requests[-1]["messages"][0]["content"]
