"""End-to-end behaviour of the tutoring loop, through the API, with a scripted LLM."""

from tests.fakes import ScriptedLLM, attempt


def start(client, concept="set_operations"):
    r = client.post("/api/sessions", json={"concept_id": concept})
    assert r.status_code == 201, r.text
    return r.json()


def say(client, session_id, text, latency=10.0):
    r = client.post(f"/api/sessions/{session_id}/messages", json={"content": text, "latency_seconds": latency})
    assert r.status_code == 200, r.text
    return r.json()


def system_text(call):
    return "\n".join(b["text"] for b in call["system"])


def test_session_opens_with_tutor_message_and_plan(use_llm, onboarded_student):
    client = onboarded_student
    llm = use_llm(ScriptedLLM())
    s = start(client)
    assert [m["role"] for m in s["messages"]] == ["tutor"]
    assert s["phase"] == "warmup" and s["persona"]["id"] == "coach"
    assert [p["phase"] for p in s["phase_plan"]] == ["warmup", "stretch", "peak", "end_high"]
    prompt = system_text(llm.calls[0])
    assert "PERSONA: The Coach" in prompt and "CURRENT TOPIC: Union, Intersection & Complement" in prompt
    assert "ENGAGEMENT ETHICS" in prompt
    assert llm.calls[0]["system"][0].get("cache_control")  # stable block is cacheable


def test_rag_context_from_sample_notes_reaches_prompt(use_llm, onboarded_student):
    client = onboarded_student
    llm = use_llm(ScriptedLLM())
    s = start(client)
    turn = say(client, s["session_id"], "what is De Morgan's law?")
    assert any("Operations on Sets" in src["section"] for src in turn["sources"])
    assert "De Morgan" in system_text(llm.calls[-1])


def test_correct_answers_raise_mastery_and_advance_phase(use_llm, onboarded_student):
    client = onboarded_student
    use_llm(ScriptedLLM([attempt(True), attempt(True), attempt(True)]))
    s = start(client)
    t1 = say(client, s["session_id"], "{1,2,3,4}")
    assert t1["mastery"] > 0 and t1["phase"] == "warmup" and t1["problems_in_phase"] == 1
    t2 = say(client, s["session_id"], "{2}")
    assert t2["phase"] == "stretch" and t2["mastery"] > t1["mastery"]


def test_repeated_same_error_triggers_frustration_and_easier_difficulty(use_llm, onboarded_student):
    client = onboarded_student
    llm = use_llm(ScriptedLLM([attempt(False, "confuses_union_intersection")] * 3))
    s = start(client)
    say(client, s["session_id"], "{1}")
    say(client, s["session_id"], "{1,2}")
    t3 = say(client, s["session_id"], "{3}")
    assert t3["affect"] == "frustration"
    assert "STUDENT STATE: frustration" in system_text(llm.calls[-1])


def test_wanting_to_stop_wraps_up_and_ends_high(use_llm, onboarded_student):
    client = onboarded_student
    use_llm(ScriptedLLM([attempt(True, done=False), attempt(True)]))
    s = start(client)
    t = say(client, s["session_id"], "I'm tired, can we stop for today")
    assert t["phase"] == "end_high"
    t = say(client, s["session_id"], "4")
    assert t["phase"] == "complete" and t["advice"] == "suggest_stop"
    assert t["teaser"] and "Ready when you are" in t["teaser"]


def test_history_alternates_and_starts_with_user(use_llm, onboarded_student):
    client = onboarded_student
    llm = use_llm(ScriptedLLM())
    s = start(client)
    for i in range(4):
        say(client, s["session_id"], f"message {i}")
    roles = [m["role"] for m in llm.calls[-1]["messages"]]
    assert roles[0] == "user"
    assert all(a != b for a, b in zip(roles, roles[1:], strict=False))


def test_end_session_is_idempotent_and_blocks_further_messages(use_llm, onboarded_student):
    client = onboarded_student
    use_llm(ScriptedLLM())
    s = start(client)
    e1 = client.post(f"/api/sessions/{s['session_id']}/end").json()
    e2 = client.post(f"/api/sessions/{s['session_id']}/end").json()
    assert e1 == e2 and e1["teaser"]
    r = client.post(f"/api/sessions/{s['session_id']}/messages", json={"content": "hi", "latency_seconds": None})
    assert r.status_code == 409
    hist = client.get(f"/api/students/{client.student['id']}/sessions").json()
    assert hist[0]["ended_at"] is not None


def test_llm_failure_returns_503_and_persists_nothing(use_llm, onboarded_student):
    client = onboarded_student
    from app.llm.client import LLMError

    class Failing(ScriptedLLM):
        def structured(self, system, messages, schema, effort, model=None):
            if not messages[-1]["content"].startswith("[SESSION START]"):
                raise LLMError("down")
            return super().structured(system, messages, schema, effort, model)

    use_llm(Failing())
    s = start(client)
    r = client.post(f"/api/sessions/{s['session_id']}/messages", json={"content": "x", "latency_seconds": 1})
    assert r.status_code == 503 and r.json()["detail"] == "down"
    assert len(client.get(f"/api/sessions/{s['session_id']}").json()["messages"]) == 1


def test_prompt_marks_syllabus_as_untrusted(use_llm, onboarded_student):
    client = onboarded_student
    llm = use_llm(ScriptedLLM())
    start(client)
    text = system_text(llm.calls[0])
    assert "<syllabus_material>" in text and "ignore it" in text
