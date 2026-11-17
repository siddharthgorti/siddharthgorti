"""API contract tests (offline LLM): public data, uploads, tutoring, quizzes, progress."""

from pathlib import Path

from tests.conftest import ANSWERS_COACH, add_child, make_client, signup_guardian, student_login

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample_syllabi" / "class11_sets_and_functions_notes.md"


def test_health(client):
    assert client.get("/api/health").json() == {
        "status": "ok",
        "llm_mode": "offline",
        "model": "offline-stub",
        "quiz_model": "offline-stub",
    }


def test_public_endpoints_need_no_login(client):
    assert len(client.get("/api/onboarding/questions").json()) == 5
    assert len(client.get("/api/personas").json()) == 4
    assert client.get("/api/syllabus/concepts").json()[0]["id"] == "sets_basics"
    assert client.get("/api/privacy/policy").json()["version"]


def test_onboarding_hides_scores_and_does_not_store_traits(student_client, db):
    from app.models import Student

    qs = student_client.get("/api/onboarding/questions").json()
    assert all("scores" not in o for q in qs for o in q["options"])
    sid = student_client.student["id"]
    r = student_client.post(
        f"/api/students/{sid}/onboarding",
        json={"answers": [{"question_id": k, "option_index": v} for k, v in ANSWERS_COACH.items()]},
    ).json()
    assert r["persona"]["id"] == "coach" and "neuroticism" in r["trait_scores"]
    assert not hasattr(db.get(Student, sid), "trait_scores")  # shown once, never stored
    assert (
        student_client.put(f"/api/students/{sid}/persona", json={"persona_id": "mentor"}).json()["persona"] == "mentor"
    )
    assert student_client.put(f"/api/students/{sid}/persona", json={"persona_id": "nope"}).status_code == 422


def test_incomplete_onboarding_rejected(student_client):
    sid = student_client.student["id"]
    r = student_client.post(f"/api/students/{sid}/onboarding", json={"answers": []})
    assert r.status_code == 422 and "Missing answers" in r.json()["detail"]


def test_session_requires_onboarding_and_known_concept(student_client):
    assert student_client.post("/api/sessions", json={"concept_id": "sets_basics"}).status_code == 409


def test_unknown_concept_404(onboarded_student):
    assert onboarded_student.post("/api/sessions", json={"concept_id": "nope"}).status_code == 404


def test_upload_is_admin_only(guardian_client):
    files = {"file": (SAMPLE.name, SAMPLE.read_bytes(), "text/markdown")}
    assert guardian_client.post("/api/syllabus/upload", files=files).status_code == 403
    with make_client() as admin:
        signup_guardian(admin, email="admin@example.com")
        r = admin.post("/api/syllabus/upload", files=files)
        assert r.status_code == 201, r.text
        assert r.json()["sections"] >= 8
        assert any(d["id"] == r.json()["id"] for d in admin.get("/api/syllabus/documents").json())
        bad = admin.post("/api/syllabus/upload", files={"file": ("x.docx", b"data", "application/octet-stream")})
        assert bad.status_code == 415


def test_unverified_admin_cannot_upload():
    with make_client() as admin:
        signup_guardian(admin, email="admin@example.com", verify=False)
        files = {"file": (SAMPLE.name, SAMPLE.read_bytes(), "text/markdown")}
        assert admin.post("/api/syllabus/upload", files=files).status_code == 403


def test_offline_chat_roundtrip(onboarded_student):
    c = onboarded_student
    s = c.post("/api/sessions", json={"concept_id": "sets_basics"}).json()
    assert "Offline demo mode" in s["messages"][0]["content"]
    t = c.post(f"/api/sessions/{s['session_id']}/messages", json={"content": "5", "latency_seconds": 4}).json()
    assert t["mastery"] > 0 and t["advice"] == "continue"
    state = c.get(f"/api/sessions/{s['session_id']}").json()
    assert [m["role"] for m in state["messages"]] == ["tutor", "student", "tutor"]


def test_quiz_flow_updates_mastery_once_per_question(onboarded_student):
    c = onboarded_student
    quiz = c.post("/api/quiz", json={"concept_id": "sets_basics", "num_questions": 4}).json()
    assert len(quiz["questions"]) == 4
    q = quiz["questions"][0]
    assert "answer_index" not in q and "explanation" not in q  # no answer keys leak
    r1 = c.post(f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": q["id"], "answer": "1"}).json()
    assert r1["correct"] and r1["mastery_after"] > 0
    r2 = c.post(f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": q["id"], "answer": "1"}).json()
    assert r2["mastery_after"] == r1["mastery_after"]  # no farming by resubmitting
    num = quiz["questions"][1]
    r3 = c.post(f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": num["id"], "answer": "999"}).json()
    assert not r3["correct"] and r3["correct_answer"]


def test_mastery_map_shape_and_counts(onboarded_student):
    c = onboarded_student
    sid = c.student["id"]
    quiz = c.post("/api/quiz", json={"concept_id": "sets_basics", "num_questions": 1}).json()
    c.post(f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": quiz["questions"][0]["id"], "answer": "1"})
    m = c.get(f"/api/students/{sid}/mastery-map").json()
    s = m["summary"]
    assert s["mastered"] + s["learning"] + s["started"] + s["not_started"] == s["total_concepts"] == len(m["concepts"])
    assert {"from": "sets_basics", "to": "set_operations"} in m["connections"]
    assert 0 < s["overall_progress"] < 1


def test_open_session_history_reports_current_mastery(onboarded_student):
    c = onboarded_student
    s = c.post("/api/sessions", json={"concept_id": "sets_basics"}).json()
    c.post(f"/api/sessions/{s['session_id']}/messages", json={"content": "5", "latency_seconds": 3})
    hist = c.get(f"/api/students/{c.student['id']}/sessions").json()
    assert hist[0]["ended_at"] is None and hist[0]["mastery_end"] > hist[0]["mastery_start"]


def test_oversized_upload_rejected_before_reading(client):
    from app.config import get_settings

    too_big = (get_settings().max_upload_mb + 2) * 1024 * 1024
    r = client.post(
        "/api/syllabus/upload",
        content=b"x",
        headers={"Content-Type": "multipart/form-data; boundary=b", "Content-Length": str(too_big)},
    )
    assert r.status_code == 413


def test_oversized_json_body_rejected(client):
    r = client.post(
        "/api/auth/guardian/login", content=b"{" + b" " * 70_000 + b"}", headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 413


def test_validation_errors_are_readable_text(client):
    r = client.post("/api/auth/guardian/signup", json={"name": "A", "email": "a@b.co", "password": "short"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str) and "password" in r.json()["detail"]


def test_second_family_is_independent():
    """Two guardians each with a child: usernames unique service-wide, data separate."""
    with make_client() as g1, make_client() as g2:
        signup_guardian(g1, email="one@example.com")
        signup_guardian(g2, email="two@example.com")
        add_child(g1, username="kid-one")
        r = g2.post(
            "/api/guardian/students",
            json={
                "name": "X",
                "username": "KID-ONE",
                "password": "student-pass-1",
                "consent": True,
                "policy_version": g2.get("/api/privacy/policy").json()["version"],
            },
        )
        assert r.status_code == 409  # case-insensitive uniqueness
        assert [c["username"] for c in g1.get("/api/guardian/students").json()] == ["kid-one"]
        assert g2.get("/api/guardian/students").json() == []
    with make_client() as s:
        assert student_login(s, "Kid-One")["username"] == "kid-one"  # case-insensitive login
