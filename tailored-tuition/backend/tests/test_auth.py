"""Accounts, consent, ownership and abuse protections."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.config import Settings, get_settings
from app.models import AuthSession, EmailToken, Guardian, Mastery, Message, Quiz, Student, TutorSession
from app.security.auth import COOKIE
from app.security.tokens import hash_token
from tests.conftest import (
    GUARDIAN_PASSWORD,
    STUDENT_PASSWORD,
    add_child,
    make_client,
    policy_version,
    signup_guardian,
    student_login,
)

# ---------------------------------------------------------------- guardians


def test_signup_logs_in_unverified_and_blocks_children_until_verified(client):
    g = signup_guardian(client, verify=False)
    assert g["email_verified"] is False
    assert client.get("/api/auth/me").json()["role"] == "guardian"
    r = client.post(
        "/api/guardian/students",
        json={
            "name": "A",
            "username": "kid1",
            "password": STUDENT_PASSWORD,
            "consent": True,
            "policy_version": policy_version(client),
        },
    )
    assert r.status_code == 403 and "verify" in r.json()["detail"].lower()


def test_duplicate_email_and_bad_email(client):
    signup_guardian(client, email="Dup@Example.com")
    with make_client() as c2:
        r = c2.post(
            "/api/auth/guardian/signup", json={"name": "B", "email": "dup@example.com", "password": GUARDIAN_PASSWORD}
        )
        assert r.status_code == 409
        r = c2.post(
            "/api/auth/guardian/signup", json={"name": "B", "email": "not-an-email", "password": GUARDIAN_PASSWORD}
        )
        assert r.status_code == 422


def test_verification_link_is_single_use_and_rejects_garbage(client):
    r = client.post(
        "/api/auth/guardian/signup", json={"name": "P", "email": "p@example.com", "password": GUARDIAN_PASSWORD}
    )
    token = r.json()["dev_verification_url"].split("token=")[1]
    assert client.post("/api/auth/guardian/verify", json={"token": token}).status_code == 200
    assert client.post("/api/auth/guardian/verify", json={"token": token}).status_code == 400
    assert client.post("/api/auth/guardian/verify", json={"token": "x" * 40}).status_code == 400


def test_expired_verification_link(client, db):
    r = client.post(
        "/api/auth/guardian/signup", json={"name": "P", "email": "p@example.com", "password": GUARDIAN_PASSWORD}
    )
    token = r.json()["dev_verification_url"].split("token=")[1]
    row = db.get(EmailToken, hash_token(token))
    row.expires_at = row.expires_at - timedelta(days=3)
    db.commit()
    assert client.post("/api/auth/guardian/verify", json={"token": token}).status_code == 400


def test_dev_links_only_in_development():
    assert Settings(app_env="development", email_backend="console").dev_links_enabled
    assert not Settings(app_env="production", email_backend="console").dev_links_enabled
    assert not Settings(app_env="development", email_backend="smtp").dev_links_enabled


def test_login_logout_and_wrong_password(client):
    signup_guardian(client, email="g@example.com")
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.post(
            "/api/auth/guardian/login", json={"email": "g@example.com", "password": "wrong-password"}
        ).status_code
        == 401
    )
    assert (
        client.post("/api/auth/guardian/login", json={"email": "nobody@example.com", "password": "x" * 12}).status_code
        == 401
    )
    r = client.post("/api/auth/guardian/login", json={"email": "G@EXAMPLE.COM", "password": GUARDIAN_PASSWORD})
    assert r.status_code == 200 and client.get("/api/auth/me").json()["guardian"]["email"] == "g@example.com"


def test_lockout_after_ten_failures_even_with_right_password(client):
    signup_guardian(client, email="g@example.com")
    for _ in range(10):
        client.post("/api/auth/guardian/login", json={"email": "g@example.com", "password": "wrong-password"})
    r = client.post("/api/auth/guardian/login", json={"email": "g@example.com", "password": GUARDIAN_PASSWORD})
    assert r.status_code == 429 and "minute" in r.json()["detail"]


def test_forgot_password_does_not_reveal_accounts_and_reset_ends_other_sessions(client):
    signup_guardian(client, email="g@example.com")
    with make_client() as other:
        assert other.post("/api/auth/guardian/forgot-password", json={"email": "nobody@example.com"}).json() == {
            "dev_reset_url": None
        }
        r = other.post("/api/auth/guardian/forgot-password", json={"email": "g@example.com"})
        assert r.status_code == 202
        token = r.json()["dev_reset_url"].split("token=")[1]
        new_pw = "a-brand-new-password"
        assert (
            other.post("/api/auth/guardian/reset-password", json={"token": token, "password": new_pw}).status_code
            == 200
        )
        assert other.get("/api/auth/me").json()["role"] == "guardian"
        assert (
            other.post("/api/auth/guardian/reset-password", json={"token": token, "password": new_pw}).status_code
            == 400
        )
    assert client.get("/api/auth/me").status_code == 401  # the old session was ended


# ---------------------------------------------------------------- sessions and CSRF


def test_cookie_flags_and_token_stored_hashed(client, db):
    r = client.post(
        "/api/auth/guardian/signup", json={"name": "P", "email": "p@example.com", "password": GUARDIAN_PASSWORD}
    )
    cookie = r.headers["set-cookie"]
    assert f"{COOKIE}=" in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    assert "Secure" not in cookie  # COOKIE_SECURE is off in development
    token = client.cookies.get(COOKIE)
    assert db.get(AuthSession, token) is None and db.get(AuthSession, hash_token(token)) is not None


def test_expired_session_is_rejected(guardian_client, db):
    row = db.get(AuthSession, hash_token(guardian_client.cookies.get(COOKIE)))
    row.expires_at = row.expires_at - timedelta(days=60)
    db.commit()
    assert guardian_client.get("/api/auth/me").status_code == 401


def test_unsafe_requests_need_csrf_header(guardian_client):
    guardian_client.headers.pop("X-TT-CSRF")
    try:
        r = guardian_client.post("/api/auth/logout")
        assert r.status_code == 403
        assert guardian_client.get("/api/auth/me").status_code == 200  # GETs don't need it; still logged in
    finally:
        guardian_client.headers["X-TT-CSRF"] = "1"


# ---------------------------------------------------------------- ownership


def test_students_see_only_themselves(guardian_client):
    a = add_child(guardian_client, username="kid-a")
    b = add_child(guardian_client, username="kid-b")
    with make_client() as sa:
        student_login(sa, "kid-a")
        assert sa.get(f"/api/students/{a['id']}").status_code == 200
        for path in (
            f"/api/students/{b['id']}",
            f"/api/students/{b['id']}/mastery-map",
            f"/api/students/{b['id']}/sessions",
        ):
            assert sa.get(path).status_code == 404
        assert sa.get("/api/guardian/students").status_code == 403
        assert sa.post(f"/api/students/{b['id']}/onboarding", json={"answers": []}).status_code == 404


def test_guardian_reads_own_child_but_cannot_act_as_them(onboarded_student, guardian_client):
    sid = onboarded_student.student["id"]
    s = onboarded_student.post("/api/sessions", json={"concept_id": "sets_basics"}).json()
    assert guardian_client.get(f"/api/students/{sid}/mastery-map").status_code == 200
    assert guardian_client.get(f"/api/sessions/{s['session_id']}").status_code == 200  # transcript
    r = guardian_client.post(f"/api/sessions/{s['session_id']}/messages", json={"content": "hi", "latency_seconds": 1})
    assert r.status_code == 403
    assert guardian_client.post("/api/sessions", json={"concept_id": "sets_basics"}).status_code == 403
    assert guardian_client.post("/api/quiz", json={"concept_id": "sets_basics"}).status_code == 403


def test_other_families_cannot_see_anything(onboarded_student):
    sid = onboarded_student.student["id"]
    s = onboarded_student.post("/api/sessions", json={"concept_id": "sets_basics"}).json()
    quiz = onboarded_student.post("/api/quiz", json={"concept_id": "sets_basics", "num_questions": 1}).json()
    with make_client() as stranger:
        signup_guardian(stranger, email="stranger@example.com")
        for path in (
            f"/api/students/{sid}",
            f"/api/students/{sid}/mastery-map",
            f"/api/sessions/{s['session_id']}",
            f"/api/guardian/students/{sid}/export",
        ):
            assert stranger.get(path).status_code == 404, path
        assert stranger.delete(f"/api/guardian/students/{sid}").status_code == 404
        assert (
            stranger.put(f"/api/guardian/students/{sid}/password", json={"password": "hijack-pass-1"}).status_code
            == 404
        )
        child = add_child(stranger, username="stranger-kid")
        with make_client() as sk:
            student_login(sk, child["username"])
            r = sk.post(
                f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": quiz["questions"][0]["id"], "answer": "1"}
            )
            assert r.status_code == 404


def test_logged_out_gets_401_everywhere_private(client, onboarded_student):
    sid = onboarded_student.student["id"]
    for method, path in [
        ("get", f"/api/students/{sid}"),
        ("get", "/api/guardian/students"),
        ("post", "/api/sessions"),
        ("post", "/api/quiz"),
        ("get", "/api/syllabus/documents"),
    ]:
        r = getattr(client, method)(path, **({"json": {"concept_id": "sets_basics"}} if method == "post" else {}))
        assert r.status_code == 401, path


# ---------------------------------------------------------------- consent and children


def test_consent_must_be_true_and_current(guardian_client):
    base = {"name": "A", "username": "kid1", "password": STUDENT_PASSWORD}
    assert (
        guardian_client.post(
            "/api/guardian/students", json={**base, "consent": False, "policy_version": policy_version(guardian_client)}
        ).status_code
        == 422
    )
    assert (
        guardian_client.post(
            "/api/guardian/students", json={**base, "policy_version": policy_version(guardian_client)}
        ).status_code
        == 422
    )
    r = guardian_client.post("/api/guardian/students", json={**base, "consent": True, "policy_version": "1999-01-01"})
    assert r.status_code == 409
    for bad in ("ab", "has space", "UPPER!"):
        r = guardian_client.post(
            "/api/guardian/students",
            json={**base, "username": bad, "consent": True, "policy_version": policy_version(guardian_client)},
        )
        assert r.status_code == 422, bad


def test_consent_is_recorded(guardian_client, db):
    child = add_child(guardian_client)
    s = db.get(Student, child["id"])
    assert s.consent_given_at is not None and s.consent_policy_version == policy_version(guardian_client)
    assert s.guardian_id == guardian_client.guardian["id"]


def test_child_password_change_logs_child_out(guardian_client):
    child = add_child(guardian_client)
    with make_client() as sc:
        student_login(sc, child["username"])
        r = guardian_client.put(f"/api/guardian/students/{child['id']}/password", json={"password": "new-student-pass"})
        assert r.status_code == 204
        assert sc.get("/api/auth/me").status_code == 401
        assert (
            sc.post(
                "/api/auth/student/login", json={"username": child["username"], "password": STUDENT_PASSWORD}
            ).status_code
            == 401
        )
        student_login(sc, child["username"], "new-student-pass")


def test_children_summary(onboarded_student, guardian_client):
    onboarded_student.post("/api/sessions", json={"concept_id": "sets_basics"})
    quiz = onboarded_student.post("/api/quiz", json={"concept_id": "sets_basics", "num_questions": 1}).json()
    onboarded_student.post(
        f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": quiz["questions"][0]["id"], "answer": "1"}
    )
    [child] = guardian_client.get("/api/guardian/students").json()
    assert child["persona"] == "coach" and child["overall_progress"] > 0 and child["last_active"]
    assert "password_hash" not in child


def test_export_contains_everything_but_secrets(onboarded_student, guardian_client):
    sid = onboarded_student.student["id"]
    s = onboarded_student.post("/api/sessions", json={"concept_id": "sets_basics"}).json()
    onboarded_student.post(
        f"/api/sessions/{s['session_id']}/messages", json={"content": "my answer is 5", "latency_seconds": 2}
    )
    r = guardian_client.get(f"/api/guardian/students/{sid}/export")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["consent"]["given_by_guardian"] == "parent@example.com"
    texts = [m["text"] for t in data["tutoring_sessions"] for m in t["messages"]]
    assert "my answer is 5" in texts
    assert "password" not in r.text.lower().replace("password_hash", "")  # no secrets
    assert "scrypt$" not in r.text


def count(db, model, **where):
    q = select(func.count()).select_from(model)
    for k, v in where.items():
        q = q.where(getattr(model, k) == v)
    return db.scalar(q)


def test_delete_child_removes_all_their_data(onboarded_student, guardian_client, db):
    sid = onboarded_student.student["id"]
    s = onboarded_student.post("/api/sessions", json={"concept_id": "sets_basics"}).json()
    onboarded_student.post(f"/api/sessions/{s['session_id']}/messages", json={"content": "5", "latency_seconds": 2})
    quiz = onboarded_student.post("/api/quiz", json={"concept_id": "sets_basics", "num_questions": 1}).json()
    onboarded_student.post(
        f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": quiz["questions"][0]["id"], "answer": "1"}
    )
    assert count(db, Message) > 0 and count(db, Mastery, student_id=sid) > 0
    assert guardian_client.delete(f"/api/guardian/students/{sid}").status_code == 204
    db.expire_all()
    for model, kw in [
        (Student, {"id": sid}),
        (TutorSession, {"student_id": sid}),
        (Quiz, {"student_id": sid}),
        (Mastery, {"student_id": sid}),
        (AuthSession, {"student_id": sid}),
    ]:
        assert count(db, model, **kw) == 0, model.__name__
    assert count(db, Message) == 0
    assert onboarded_student.get("/api/auth/me").status_code == 401


def test_delete_account_needs_password_and_removes_everything(guardian_client, db):
    add_child(guardian_client, username="kid-a")
    add_child(guardian_client, username="kid-b")
    assert (
        guardian_client.request("DELETE", "/api/guardian/account", json={"password": "wrong-password"}).status_code
        == 403
    )
    assert (
        guardian_client.request("DELETE", "/api/guardian/account", json={"password": GUARDIAN_PASSWORD}).status_code
        == 204
    )
    db.expire_all()
    assert (
        count(db, Guardian) == 0
        and count(db, Student) == 0
        and count(db, AuthSession) == 0
        and count(db, EmailToken) == 0
    )
    assert guardian_client.get("/api/auth/me").status_code == 401


# ---------------------------------------------------------------- usage limits


@pytest.fixture
def tight_limits():
    s = get_settings()
    old = (s.max_messages_per_day, s.max_sessions_per_day, s.max_quizzes_per_day)
    s.max_messages_per_day, s.max_sessions_per_day, s.max_quizzes_per_day = 2, 1, 1
    yield
    s.max_messages_per_day, s.max_sessions_per_day, s.max_quizzes_per_day = old


def test_daily_limits(onboarded_student, tight_limits):
    c = onboarded_student
    s = c.post("/api/sessions", json={"concept_id": "sets_basics"}).json()
    assert c.post("/api/sessions", json={"concept_id": "sets_basics"}).status_code == 429
    for _ in range(2):
        assert (
            c.post(f"/api/sessions/{s['session_id']}/messages", json={"content": "5", "latency_seconds": 1}).status_code
            == 200
        )
    r = c.post(f"/api/sessions/{s['session_id']}/messages", json={"content": "5", "latency_seconds": 1})
    assert r.status_code == 429 and "today's limit" in r.json()["detail"]
    assert c.post("/api/quiz", json={"concept_id": "sets_basics", "num_questions": 1}).status_code == 201
    assert c.post("/api/quiz", json={"concept_id": "sets_basics", "num_questions": 1}).status_code == 429


# ---------------------------------------------------------------- production safety


def test_production_refuses_unsafe_settings():
    bad = Settings(
        app_env="production",
        database_url="sqlite:///x.db",
        email_backend="console",
        cookie_secure=False,
        public_url="http://localhost:3000",
    )
    problems = " ".join(bad.production_problems())
    for needle in ("EMAIL_BACKEND", "COOKIE_SECURE", "PUBLIC_URL", "DATABASE_URL"):
        assert needle in problems
    good = Settings(
        app_env="production",
        email_backend="smtp",
        smtp_host="smtp.example.com",
        smtp_from="no-reply@example.com",
        cookie_secure=True,
        public_url="https://tuition.example.com",
        database_url="postgresql+psycopg://u:p@db/t",
    )
    assert good.production_problems() == []
    assert Settings(**{**good.model_dump(), "seed_demo_accounts": True}).production_problems()


def test_secure_cookie_when_configured(client):
    s = get_settings()
    s.cookie_secure = True
    try:
        r = client.post(
            "/api/auth/guardian/signup", json={"name": "P", "email": "p@example.com", "password": GUARDIAN_PASSWORD}
        )
        assert "Secure" in r.headers["set-cookie"]
    finally:
        s.cookie_secure = False


def test_demo_seed_creates_logins_once_and_never_in_production(db, tmp_path):
    from app.demo_seed import DEMO_EMAIL, seed_demo_accounts

    dev = Settings(app_env="development", data_dir=tmp_path)
    seed_demo_accounts(db, dev)
    seed_demo_accounts(db, dev)  # idempotent
    assert count(db, Guardian, email=DEMO_EMAIL) == 1 and count(db, Student) == 3
    text = (tmp_path / "demo-accounts.txt").read_text()
    assert "demo1" in text and DEMO_EMAIL in text
    with make_client() as c:
        pw = next(line.split("password: ")[1] for line in text.splitlines() if "demo1" in line)
        student_login(c, "demo1", pw.strip())
    db.query(Student).delete()
    db.query(Guardian).delete()
    db.commit()
    seed_demo_accounts(db, Settings(app_env="production", data_dir=tmp_path / "p"))
    assert count(db, Guardian) == 0
