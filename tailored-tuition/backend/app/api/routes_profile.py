"""Students, onboarding and personas."""

from fastapi import APIRouter, HTTPException

from app.api.deps import DB, SettingsDep, load_student, persona_out, student_out
from app.api.schemas import (
    OnboardingResult,
    OnboardingSubmit,
    PersonaOut,
    PersonaUpdate,
    StudentCreate,
    StudentOut,
)
from app.models import Student, utcnow
from app.student.personality_model import InvalidAnswersError, match_persona, public_questions
from app.tutor.persona_manager import PERSONAS

router = APIRouter(prefix="/api", tags=["profile"])


@router.post("/students", response_model=StudentOut, status_code=201)
def create_student(body: StudentCreate, db: DB, settings: SettingsDep):
    # Students are typically 15-17. India's DPDP Act 2023 requires verifiable
    # parental consent to process a child's data; this checkbox is the MVP
    # placeholder for a real verification flow.
    if not body.guardian_consent:
        raise HTTPException(400, "A parent or guardian must agree before we can save learning data.")
    student = Student(
        name=body.name.strip(),
        grade=settings.default_grade,
        board=settings.default_board,
        guardian_consent_at=utcnow(),
    )
    db.add(student)
    db.commit()
    return student_out(student)


@router.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: str, db: DB):
    return student_out(load_student(db, student_id))


@router.get("/onboarding/questions")
def onboarding_questions() -> list[dict]:
    return public_questions()


@router.post("/students/{student_id}/onboarding", response_model=OnboardingResult)
def submit_onboarding(student_id: str, body: OnboardingSubmit, db: DB):
    student = load_student(db, student_id)
    try:
        match = match_persona({a.question_id: a.option_index for a in body.answers})
    except InvalidAnswersError as exc:
        raise HTTPException(422, str(exc)) from exc
    student.persona = match.persona
    student.trait_scores = match.traits
    db.commit()
    return {"persona": persona_out(match.persona), "trait_scores": match.traits, "rationale": match.rationale}


@router.get("/personas", response_model=list[PersonaOut])
def list_personas():
    return [p.public() for p in PERSONAS.values()]


@router.put("/students/{student_id}/persona", response_model=StudentOut)
def set_persona(student_id: str, body: PersonaUpdate, db: DB):
    student = load_student(db, student_id)
    student.persona = body.persona_id
    db.commit()
    return student_out(student)
