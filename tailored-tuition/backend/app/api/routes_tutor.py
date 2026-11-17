"""Tutoring sessions. Only the logged-in student can start or continue their
sessions; their guardian can read the transcript."""

from fastapi import APIRouter, HTTPException

from app.api.deps import DB, KG, LLM, SettingsDep, concept_out, load_concept, load_session, persona_out, require_self
from app.api.schemas import SessionCreate, SessionEndOut, SessionStateOut, TurnIn, TurnOut
from app.domain.rag_pipeline import retriever
from app.engagement.session_designer import FlowState, SessionDesigner
from app.limits import check_message, check_new_session
from app.llm.client import LLMError
from app.models import TutorSession
from app.security.auth import PrincipalDep, StudentDep
from app.student.mastery_tracker import MasteryTracker
from app.tutor.tutor_engine import TutorEngine

router = APIRouter(prefix="/api/sessions", tags=["tutor"])


def _state(db, kg, session: TutorSession) -> dict:
    flow = FlowState.from_dict(session.flow_state)
    return {
        "session_id": session.id,
        "student_id": session.student_id,
        "concept": concept_out(load_concept(kg, session.concept_id)),
        "persona": persona_out(session.persona),
        "phase": flow.phase,
        "problems_in_phase": flow.problems_in_phase,
        "phase_plan": SessionDesigner.plan(),
        "mastery": MasteryTracker(db).get_level(session.student_id, session.concept_id),
        "status": session.status,
        "messages": [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in session.messages],
    }


@router.post("", response_model=SessionStateOut, status_code=201)
def create_session(body: SessionCreate, student: StudentDep, db: DB, kg: KG, llm: LLM, settings: SettingsDep):
    if not student.persona:
        raise HTTPException(409, "Complete onboarding before starting a session.")
    concept = load_concept(kg, body.concept_id)
    check_new_session(db, student.id, settings)
    engine = TutorEngine(db, llm, kg, retriever, settings)
    try:
        session = engine.start_session(student, concept)
    except LLMError as exc:
        db.rollback()
        raise HTTPException(503, str(exc)) from exc
    return _state(db, kg, session)


@router.get("/{session_id}", response_model=SessionStateOut)
def get_session(session_id: str, p: PrincipalDep, db: DB, kg: KG):
    return _state(db, kg, load_session(db, session_id, p))


@router.post("/{session_id}/messages", response_model=TurnOut)
def send_message(session_id: str, body: TurnIn, p: PrincipalDep, db: DB, kg: KG, llm: LLM, settings: SettingsDep):
    session = load_session(db, session_id, p)
    student = require_self(p, session.student_id)
    if session.status != "active":
        raise HTTPException(409, "This session has ended. Start a new one.")
    check_message(db, student.id, settings)
    engine = TutorEngine(db, llm, kg, retriever, settings)
    try:
        r = engine.handle_turn(session, student, body.content.strip(), body.latency_seconds)
    except LLMError as exc:
        db.rollback()
        raise HTTPException(503, str(exc)) from exc
    return {
        "reply": {"role": "tutor", "content": r.reply.content, "created_at": r.reply.created_at},
        "sources": r.reply.meta.get("sources", []),
        "affect": r.affect,
        "phase": r.flow.phase,
        "problems_in_phase": r.flow.problems_in_phase,
        "mastery": r.mastery,
        "advice": r.advice,
        "teaser": r.teaser,
    }


@router.post("/{session_id}/end", response_model=SessionEndOut)
def end_session(session_id: str, p: PrincipalDep, db: DB, kg: KG, llm: LLM, settings: SettingsDep):
    session = load_session(db, session_id, p)
    require_self(p, session.student_id)
    engine = TutorEngine(db, llm, kg, retriever, settings)
    teaser = engine.end_session(session)
    return {"teaser": teaser, "mastery": MasteryTracker(db).get_level(session.student_id, session.concept_id)}
