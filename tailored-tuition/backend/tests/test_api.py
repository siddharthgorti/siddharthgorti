"""API contract tests (offline LLM)."""

from pathlib import Path

from tests.conftest import ANSWERS_COACH

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample_syllabi" / "class11_sets_and_functions_notes.md"


def test_health(client):
    assert client.get("/api/health").json() == {
        "status": "ok",
        "llm_mode": "offline",
        "model": "offline-stub",
        "quiz_model": "offline-stub",
    }


def test_student_requires_guardian_consent(client):
    r = client.post("/api/students", json={"name": "Ravi", "guardian_consent": False})
    assert r.status_code == 400
    assert client.post("/api/students", json={"name": "", "guardian_consent": True}).status_code == 422


def test_onboarding_flow_and_override(client):
    s = client.post("/api/students", json={"name": "Ravi", "guardian_consent": True}).json()
    assert s["persona"] is None
    qs = client.get("/api/onboarding/questions").json()
    assert len(qs) == 5 and all("scores" not in o for q in qs for o in q["options"])
    r = client.post(
        f"/api/students/{s['id']}/onboarding",
        json={"answers": [{"question_id": k, "option_index": v} for k, v in ANSWERS_COACH.items()]},
    ).json()
    assert r["persona"]["id"] == "coach" and set(r["trait_scores"]) == {
        "openness",
        "conscientiousness",
        "extraversion",
        "agreeableness",
        "neuroticism",
    }
    assert client.put(f"/api/students/{s['id']}/persona", json={"persona_id": "mentor"}).json()["persona"] == "mentor"
    assert client.put(f"/api/students/{s['id']}/persona", json={"persona_id": "nope"}).status_code == 422


def test_incomplete_onboarding_rejected(client):
    s = client.post("/api/students", json={"name": "Ravi", "guardian_consent": True}).json()
    r = client.post(f"/api/students/{s['id']}/onboarding", json={"answers": []})
    assert r.status_code == 422


def test_session_requires_onboarding_and_known_ids(client):
    s = client.post("/api/students", json={"name": "Ravi", "guardian_consent": True}).json()
    assert client.post("/api/sessions", json={"student_id": s["id"], "concept_id": "sets_basics"}).status_code == 409
    assert client.post("/api/sessions", json={"student_id": "missing", "concept_id": "sets_basics"}).status_code == 404
    assert client.get("/api/students/missing").status_code == 404


def test_concepts_listed(client):
    concepts = client.get("/api/syllabus/concepts").json()
    assert concepts[0]["id"] == "sets_basics" and len(concepts) >= 30


def test_upload_and_list_documents(client):
    r = client.post("/api/syllabus/upload", files={"file": (SAMPLE.name, SAMPLE.read_bytes(), "text/markdown")})
    assert r.status_code == 201, r.text
    assert r.json()["sections"] >= 8
    assert any(d["id"] == r.json()["id"] for d in client.get("/api/syllabus/documents").json())
    bad = client.post("/api/syllabus/upload", files={"file": ("x.docx", b"data", "application/octet-stream")})
    assert bad.status_code == 415


def test_offline_chat_roundtrip(client, onboarded_student):
    s = client.post("/api/sessions", json={"student_id": onboarded_student["id"], "concept_id": "sets_basics"}).json()
    assert "Offline demo mode" in s["messages"][0]["content"]
    t = client.post(f"/api/sessions/{s['session_id']}/messages", json={"content": "5", "latency_seconds": 4}).json()
    assert t["mastery"] > 0 and t["advice"] == "continue"
    state = client.get(f"/api/sessions/{s['session_id']}").json()
    assert [m["role"] for m in state["messages"]] == ["tutor", "student", "tutor"]


def test_quiz_flow_updates_mastery_once_per_question(client, onboarded_student):
    sid = onboarded_student["id"]
    quiz = client.post("/api/quiz", json={"student_id": sid, "concept_id": "sets_basics", "num_questions": 4}).json()
    assert len(quiz["questions"]) == 4
    q = quiz["questions"][0]
    assert "answer_index" not in q and "explanation" not in q  # no answer keys leak
    r1 = client.post(f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": q["id"], "answer": "1"}).json()
    assert r1["correct"] and r1["mastery_after"] > 0
    r2 = client.post(f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": q["id"], "answer": "1"}).json()
    assert r2["mastery_after"] == r1["mastery_after"]  # no farming by resubmitting
    num = quiz["questions"][1]
    assert num["type"] == "numerical"
    r3 = client.post(f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": num["id"], "answer": "999"}).json()
    assert not r3["correct"] and r3["correct_answer"]


def test_mastery_map_shape_and_counts(client, onboarded_student):
    sid = onboarded_student["id"]
    quiz = client.post("/api/quiz", json={"student_id": sid, "concept_id": "sets_basics", "num_questions": 1}).json()
    client.post(f"/api/quiz/{quiz['quiz_id']}/answers", json={"question_id": quiz["questions"][0]["id"], "answer": "1"})
    m = client.get(f"/api/students/{sid}/mastery-map").json()
    s = m["summary"]
    assert s["mastered"] + s["learning"] + s["started"] + s["not_started"] == s["total_concepts"] == len(m["concepts"])
    assert {"from": "sets_basics", "to": "set_operations"} in m["connections"]
    assert next(c for c in m["concepts"] if c["id"] == "sets_basics")["status"] != "not_started"
    assert 0 < s["overall_progress"] < 1


def test_open_session_history_reports_current_mastery(client, onboarded_student):
    sid = onboarded_student["id"]
    s = client.post("/api/sessions", json={"student_id": sid, "concept_id": "sets_basics"}).json()
    client.post(f"/api/sessions/{s['session_id']}/messages", json={"content": "5", "latency_seconds": 3})
    hist = client.get(f"/api/students/{sid}/sessions").json()
    assert hist[0]["ended_at"] is None and hist[0]["mastery_end"] > hist[0]["mastery_start"]
