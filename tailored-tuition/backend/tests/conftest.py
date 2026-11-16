"""Test configuration: isolated SQLite file, offline LLM, fresh tables per test."""

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="tt-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp / 'test.db'}"
os.environ["LLM_MODE"] = "offline"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.domain.rag_pipeline import retriever  # noqa: E402
from app.llm.client import get_llm  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    from app import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    retriever.invalidate()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def use_llm():
    """Swap in a specific LLM implementation for API tests."""

    def _use(llm):
        app.dependency_overrides[get_llm] = lambda: llm
        return llm

    return _use


ANSWERS_COACH = {
    "motivation_style": 0,
    "pace_preference": 0,
    "engagement_style": 3,
    "feedback_preference": 2,
    "structure_need": 3,
}


@pytest.fixture
def onboarded_student(client):
    s = client.post("/api/students", json={"name": "Asha", "guardian_consent": True}).json()
    r = client.post(
        f"/api/students/{s['id']}/onboarding",
        json={"answers": [{"question_id": k, "option_index": v} for k, v in ANSWERS_COACH.items()]},
    )
    assert r.status_code == 200, r.text
    return s
