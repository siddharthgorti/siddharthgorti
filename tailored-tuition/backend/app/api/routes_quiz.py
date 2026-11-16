"""Adaptive quizzes."""

from fastapi import APIRouter, HTTPException

from app.api.deps import DB, KG, LLM, SettingsDep, concept_out, load_concept, load_student
from app.api.schemas import AnswerIn, AnswerOut, QuizCreate, QuizOut
from app.domain.rag_pipeline import retriever
from app.llm.client import LLMError
from app.models import Quiz
from app.quiz.answer_evaluator import grade
from app.quiz.quiz_generator import QuizGenerator, public_question
from app.student.mastery_tracker import MasteryTracker

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.post("", response_model=QuizOut, status_code=201)
def create_quiz(body: QuizCreate, db: DB, kg: KG, llm: LLM, settings: SettingsDep):
    student = load_student(db, body.student_id)
    concept = load_concept(kg, body.concept_id)
    mastery = MasteryTracker(db).get_level(student.id, concept.id)
    try:
        questions = QuizGenerator(db, llm, retriever, settings).generate(concept, mastery, body.num_questions)
    except LLMError as exc:
        raise HTTPException(503, str(exc)) from exc
    quiz = Quiz(student_id=student.id, concept_id=concept.id, questions=questions, answered={})
    db.add(quiz)
    db.commit()
    return {"quiz_id": quiz.id, "concept": concept_out(concept), "questions": [public_question(q) for q in questions]}


@router.post("/{quiz_id}/answers", response_model=AnswerOut)
def answer(quiz_id: str, body: AnswerIn, db: DB):
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    question = next((q for q in quiz.questions if q["id"] == body.question_id), None)
    if question is None:
        raise HTTPException(404, "Question not found")
    correct, key = grade(question, body.answer)
    tracker = MasteryTracker(db)
    if body.question_id in quiz.answered:
        # Re-submitting can't farm mastery: only the first answer counts.
        mastery = tracker.get_level(quiz.student_id, quiz.concept_id)
    else:
        mastery = tracker.update(quiz.student_id, quiz.concept_id, correct, question["difficulty"])
        quiz.answered = {**quiz.answered, body.question_id: correct}
    db.commit()
    return {"correct": correct, "correct_answer": key, "explanation": question["explanation"], "mastery_after": mastery}
