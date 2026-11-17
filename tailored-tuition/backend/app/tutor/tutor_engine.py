"""Core tutoring loop.

Per student turn:
  1. Derive affect signals from this message + earlier turns' assessments.
  2. Detect affect -> adaptation (prompt injection, difficulty nudge, wrap-up).
  3. Retrieve syllabus context for the topic + message (RAG).
  4. Build system prompt = stable (base + persona + guardrails) + dynamic
     (mastery, phase, affect, context).
  5. One structured LLM call returns the reply AND an assessment of the
     student's message.
  6. Assessment -> mastery update + session-phase progression.
  7. Guardrails decide whether to suggest a break; persist everything.

Design note: affect is detected *before* the LLM assesses the current message,
so error-based signals lag by one turn. Surface signals (length, latency, help
phrases) are current. The alternative, a second LLM call per turn, doubles
latency and cost for little gain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.knowledge_graph import Concept, KnowledgeGraph
from app.domain.rag_pipeline import SYLLABUS_NOTE, Retrieved, Retriever, format_context
from app.engagement import guardrails
from app.engagement.affect_detector import AffectDetector, AffectSignals, is_help_request
from app.engagement.response_router import adaptation_for
from app.engagement.session_designer import FlowState, SessionDesigner
from app.llm.client import LLMClient
from app.llm.schemas import TutorTurn
from app.models import Message, Student, TutorSession, utcnow
from app.student.mastery_tracker import MasteryTracker
from app.tutor.persona_manager import get_persona
from app.tutor.prompts.base_system import DYNAMIC_TEMPLATE, STABLE_TEMPLATE

KICKOFF = "[SESSION START] The student has just opened a tutoring session on {topic}. Greet them by name in one short line and pose the first warm-up problem."
_WANTS_TO_STOP = re.compile(
    r"\b(i'?m (tired|done|exhausted)|let'?s stop|can we stop|stop for (now|today)|bye|good ?night)\b", re.I
)


@dataclass
class TurnResult:
    reply: Message
    sources: list[Retrieved]
    affect: str
    flow: FlowState
    mastery: float
    advice: str
    teaser: str | None = None
    assessment: dict = field(default_factory=dict)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class TutorEngine:
    def __init__(self, db: Session, llm: LLMClient, kg: KnowledgeGraph, retriever: Retriever, settings: Settings):
        self.db, self.llm, self.kg, self.retriever, self.settings = db, llm, kg, retriever, settings
        self.mastery = MasteryTracker(db)
        self.detector = AffectDetector()

    # -- session lifecycle ---------------------------------------------------
    def start_session(self, student: Student, concept: Concept) -> TutorSession:
        level = self.mastery.get_level(student.id, concept.id)
        session = TutorSession(
            student_id=student.id,
            concept_id=concept.id,
            persona=student.persona,
            flow_state=FlowState().to_dict(),
            mastery_start=level,
        )
        self.db.add(session)
        self.db.flush()
        designer = SessionDesigner(FlowState())
        kickoff = KICKOFF.format(topic=concept.name)
        hits = self.retriever.retrieve(self.db, concept.name, concept, self.settings.rag_top_k)
        turn = self._call_llm(student, session, concept, designer, level, "neutral", hits, [], kickoff)
        self.db.add(Message(session=session, role="tutor", content=turn.reply, meta={"sources": _sources(hits)}))
        self.db.commit()
        return session

    def end_session(self, session: TutorSession) -> str:
        if session.status != "ended":
            level = self.mastery.get_level(session.student_id, session.concept_id)
            session.status = "ended"
            session.ended_at = utcnow()
            session.mastery_end = level
            session.teaser = session.teaser or self.teaser(session.student_id, session.concept_id)
            self.db.commit()
        return session.teaser or ""

    def teaser(self, student_id: str, concept_id: str) -> str:
        """Zeigarnik-style preview of the next concept, built from the graph.
        Deterministic (no LLM) and checked against the guardrails."""
        levels = {cid: m.level for cid, m in self.mastery.all_levels(student_id).items()}
        nxt = self.kg.next_unlockable(concept_id, levels)
        current = self.kg.get(concept_id)
        if nxt:
            c = nxt[0]
            known = [self.kg.get(p).name for p in c.prerequisites if self.kg.get(p)]
            opens = [d.name for d in self.kg.dependents(c.id)][:2]
            text = f"Next time, we could explore **{c.name}**"
            if known:
                text += f" — it builds directly on {', '.join(known)}"
            if opens:
                text += f", and it's the key to {' and '.join(opens)}"
            text += ". You're closer than you think. Ready when you are."
        else:
            name = current.name if current else "this topic"
            text = f"Great session on {name}! We'll pick up right where we left off. Ready when you are."
        return text if guardrails.validate_notification(text) else "Great session! Ready when you are."

    # -- a student turn ------------------------------------------------------
    def handle_turn(self, session: TutorSession, student: Student, content: str, latency: float | None) -> TurnResult:
        concept = self.kg.get(session.concept_id)
        if concept is None:  # graph changed under an old session
            raise ValueError(f"Unknown concept {session.concept_id}")
        designer = SessionDesigner(FlowState.from_dict(session.flow_state))
        history = list(session.messages)
        mastery_before = self.mastery.get_level(student.id, concept.id)

        # 1-2. affect
        signals = self._signals(session, history, content, latency)
        affect = self.detector.detect(signals)
        adaptation = adaptation_for(affect)
        if affect == "fatigue" or _WANTS_TO_STOP.search(content):
            designer.request_wrap_up()
        else:
            designer.apply_affect(adaptation.difficulty_adjustment)
        difficulty = designer.target_difficulty(mastery_before)

        # 3. retrieval
        hits = self.retriever.retrieve(self.db, content, concept, self.settings.rag_top_k)

        # 4-5. LLM
        turn = self._call_llm(student, session, concept, designer, mastery_before, affect, hits, history, content)
        a = turn.assessment

        # 6. mastery + flow
        mastery = mastery_before
        if a.kind == "answer_attempt" and a.correct is not None:
            mastery = self.mastery.update(student.id, concept.id, a.correct, difficulty)
        if a.problem_completed:
            designer.record_problem_completed(solved_independently=bool(a.correct))

        teaser = None
        if designer.state.phase == "complete" and not session.teaser:
            teaser = session.teaser = self.teaser(student.id, concept.id)

        # 7. guardrails + persistence
        minutes = (datetime.now(UTC) - _aware(session.started_at)).total_seconds() / 60
        student_turns = sum(1 for m in history if m.role == "student") + 1
        advice = guardrails.session_advice(
            affect == "fatigue" or designer.state.phase == "complete",
            minutes,
            student_turns,
            self.settings.max_turns_per_session,
        )
        assessment = a.model_dump()
        self.db.add(
            Message(
                session=session,
                role="student",
                content=content,
                meta={"latency": latency, "help": is_help_request(content), "assessment": assessment},
            )
        )
        reply = Message(
            session=session,
            role="tutor",
            content=turn.reply,
            meta={"affect": affect, "phase": designer.state.phase, "difficulty": difficulty, "sources": _sources(hits)},
        )
        self.db.add(reply)
        session.flow_state = designer.state.to_dict()
        self.db.commit()
        return TurnResult(reply, hits, affect, designer.state, mastery, advice, teaser, assessment)

    # -- internals -----------------------------------------------------------
    def _signals(
        self, session: TutorSession, history: list[Message], content: str, latency: float | None
    ) -> AffectSignals:
        student_msgs = [m for m in history if m.role == "student"]
        assessments = [m.meta.get("assessment") or {} for m in student_msgs]
        attempts = [x for x in assessments if x.get("kind") == "answer_attempt" and x.get("correct") is not None]

        same_error = 0
        if attempts and attempts[-1].get("correct") is False and attempts[-1].get("error_tag"):
            tag = attempts[-1]["error_tag"]
            for x in reversed(attempts):
                if x.get("correct") is False and x.get("error_tag") == tag:
                    same_error += 1
                else:
                    break
        streak = 0
        for x in reversed(attempts):
            if x.get("correct"):
                streak += 1
            else:
                break
        recent_help = sum(
            1
            for m in student_msgs[-4:]
            if m.meta.get("help") or (m.meta.get("assessment") or {}).get("kind") == "help_request"
        ) + int(is_help_request(content))
        return AffectSignals(
            response_latency_seconds=latency,
            response_length_chars=len(content.strip()),
            error_count_recent=sum(1 for x in attempts[-3:] if x.get("correct") is False),
            same_error_repeated=same_error,
            help_requests_recent=recent_help,
            session_duration_minutes=(datetime.now(UTC) - _aware(session.started_at)).total_seconds() / 60,
            correct_streak=streak,
        )

    def _call_llm(
        self,
        student: Student,
        session: TutorSession,
        concept: Concept,
        designer: SessionDesigner,
        mastery: float,
        affect: str,
        hits: list[Retrieved],
        history: list[Message],
        content: str,
    ) -> TutorTurn:
        system = build_system(
            settings=self.settings,
            student_name=student.name,
            grade=student.grade,
            board=student.board,
            persona_id=session.persona,
            concept=concept,
            designer=designer,
            mastery=mastery,
            affect=affect,
            rag_context=format_context(concept, hits),
        )
        messages = self._history_messages(concept, history) + [{"role": "user", "content": content}]
        return self.llm.structured(system, messages, TutorTurn, self.settings.chat_effort, self.settings.chat_model)

    def _history_messages(self, concept: Concept, history: list[Message]) -> list[dict]:
        if not history:
            return []
        recent = history[-self.settings.history_turns_in_prompt :]
        while recent and recent[0].role != "tutor":  # keep strict user/assistant alternation
            recent = recent[1:]
        kickoff = {"role": "user", "content": KICKOFF.format(topic=concept.name)}
        return [kickoff] + [
            {"role": "assistant" if m.role == "tutor" else "user", "content": m.content} for m in recent
        ]


def build_system(
    *,
    settings: Settings,
    student_name: str,
    grade: int,
    board: str,
    persona_id: str,
    concept: Concept,
    designer: SessionDesigner,
    mastery: float,
    affect: str,
    rag_context: str,
) -> list[dict]:
    """System prompt blocks: a cacheable stable block, then per-turn state.
    Module-level so the assessment eval (evals/) uses the exact production prompt."""
    stable = STABLE_TEMPLATE.format(
        grade=grade,
        board=board,
        subject=settings.subject,
        student_name=student_name,
        guardrails=guardrails.GUARDRAIL_PROMPT,
        persona=get_persona(persona_id).prompt,
    )
    injection = adaptation_for(affect).prompt_injection
    dynamic = DYNAMIC_TEMPLATE.format(
        topic=concept.name,
        mastery=mastery,
        phase=designer.state.phase,
        phase_instruction=designer.phase_instruction(mastery),
        affect_block=f"STUDENT STATE: {affect}. {injection}\n" if injection else "",
        rag_context=rag_context,
        syllabus_note=SYLLABUS_NOTE,
    )
    return [
        {"type": "text", "text": stable, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": dynamic},
    ]


def _sources(hits: list[Retrieved]) -> list[dict]:
    return [{"document": h.document, "section": h.section, "snippet": h.text[:280]} for h in hits]
