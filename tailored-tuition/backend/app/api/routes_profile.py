"""Student profile, onboarding and persona. Students are created by their
guardian (routes_guardian.py); there is no open student sign-up."""

from fastapi import APIRouter, HTTPException

from app.api.deps import DB, load_student, persona_out, require_self, student_out
from app.api.schemas import OnboardingResult, OnboardingSubmit, PersonaOut, PersonaUpdate, StudentOut
from app.security.auth import PrincipalDep
from app.student.personality_model import InvalidAnswersError, match_persona, public_questions
from app.tutor.persona_manager import PERSONAS

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: str, p: PrincipalDep, db: DB):
    return student_out(load_student(db, student_id, p))


@router.get("/onboarding/questions")
def onboarding_questions() -> list[dict]:
    return public_questions()


@router.post("/students/{student_id}/onboarding", response_model=OnboardingResult)
def submit_onboarding(student_id: str, body: OnboardingSubmit, p: PrincipalDep, db: DB):
    student = require_self(p, student_id)
    try:
        match = match_persona({a.question_id: a.option_index for a in body.answers})
    except InvalidAnswersError as exc:
        raise HTTPException(422, str(exc)) from exc
    # Only the chosen persona is stored. Trait scores are returned for the
    # reveal screen and then discarded (data minimisation for minors).
    student.persona = match.persona
    db.commit()
    return {"persona": persona_out(match.persona), "trait_scores": match.traits, "rationale": match.rationale}


@router.get("/personas", response_model=list[PersonaOut])
def list_personas():
    return [p.public() for p in PERSONAS.values()]


@router.put("/students/{student_id}/persona", response_model=StudentOut)
def set_persona(student_id: str, body: PersonaUpdate, p: PrincipalDep, db: DB):
    student = require_self(p, student_id)
    student.persona = body.persona_id
    db.commit()
    return student_out(student)
