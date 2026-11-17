"""Test configuration: isolated database, offline LLM, fresh tables per test,
cheap password hashing, and helpers for logged-in guardian/student clients."""

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="tt-tests-"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp / 'test.db'}")  # CI may point this at Postgres
os.environ["DATA_DIR"] = str(_tmp)
os.environ["LLM_MODE"] = "offline"
os.environ["APP_ENV"] = "development"
os.environ["EMAIL_BACKEND"] = "console"
os.environ["ADMIN_EMAILS"] = "admin@example.com"
os.environ["SEED_DEMO_ACCOUNTS"] = "false"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.security import passwords  # noqa: E402

passwords.set_cost_for_tests(2**8)  # real cost is 2**15; tests hash hundreds of passwords

from app.db import Base, SessionLocal, engine, init_db  # noqa: E402
from app.domain.rag_pipeline import retriever  # noqa: E402
from app.llm.client import get_llm  # noqa: E402
from app.main import app  # noqa: E402
from app.security.ratelimit import login_failures, signups  # noqa: E402

GUARDIAN_PASSWORD = "correct-horse-battery"
STUDENT_PASSWORD = "student-pass-1"

ANSWERS_COACH = {
    "motivation_style": 0,
    "pace_preference": 0,
    "engagement_style": 3,
    "feedback_preference": 2,
    "structure_need": 3,
}


def reset_database() -> None:
    """Empty database, then the real migrations (so every test also exercises them)."""
    from sqlalchemy import text

    from app import models  # noqa: F401

    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    init_db()


@pytest.fixture(autouse=True)
def fresh_db():
    reset_database()
    retriever.invalidate()
    login_failures.reset()
    signups.reset()
    yield
    app.dependency_overrides.clear()


def make_client() -> TestClient:
    c = TestClient(app)
    c.headers["X-TT-CSRF"] = "1"  # what the real frontend sends on every unsafe request
    return c


def signup_guardian(c: TestClient, email: str = "parent@example.com", name: str = "Priya", verify: bool = True):
    r = c.post("/api/auth/guardian/signup", json={"name": name, "email": email, "password": GUARDIAN_PASSWORD})
    assert r.status_code == 201, r.text
    if verify:
        token = r.json()["dev_verification_url"].split("token=")[1]
        v = c.post("/api/auth/guardian/verify", json={"token": token})
        assert v.status_code == 200, v.text
        return v.json()["guardian"]
    return r.json()["guardian"]


def policy_version(c: TestClient) -> str:
    return c.get("/api/privacy/policy").json()["version"]


def add_child(c: TestClient, username: str = "asha11", name: str = "Asha", password: str = STUDENT_PASSWORD):
    r = c.post(
        "/api/guardian/students",
        json={
            "name": name,
            "username": username,
            "password": password,
            "consent": True,
            "policy_version": policy_version(c),
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def student_login(c: TestClient, username: str, password: str = STUDENT_PASSWORD):
    r = c.post("/api/auth/student/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["student"]


@pytest.fixture
def client():
    """A logged-out client."""
    with make_client() as c:
        yield c


@pytest.fixture
def guardian_client():
    with make_client() as c:
        c.guardian = signup_guardian(c)
        yield c


@pytest.fixture
def student_client(guardian_client):
    child = add_child(guardian_client)
    with make_client() as c:
        c.student = student_login(c, child["username"])
        yield c


@pytest.fixture
def onboarded_student(student_client):
    """The logged-in student's client, after onboarding (matches The Coach)."""
    sid = student_client.student["id"]
    r = student_client.post(
        f"/api/students/{sid}/onboarding",
        json={"answers": [{"question_id": k, "option_index": v} for k, v in ANSWERS_COACH.items()]},
    )
    assert r.status_code == 200, r.text
    return student_client


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def use_llm():
    """Swap in a specific LLM implementation for API tests."""

    def _use(llm):
        app.dependency_overrides[get_llm] = lambda: llm
        return llm

    return _use
