# Tailored Tuition

An AI maths tutor for CBSE Class 11 that adapts to how each student likes to learn. It teaches
through questions rather than answer dumps, notices when a student is frustrated, bored or tired,
and shows progress as a map of ideas, with no points, streaks or leaderboards.

Phase 1 MVP of the build spec. The spec review (inconsistencies found and how each was resolved) is
in [`docs/SPEC_REVIEW.md`](docs/SPEC_REVIEW.md).

## What it does

| Feature | Where |
|---|---|
| 5-question onboarding → one of 4 tutor personas (student can switch any time) | `backend/app/student/personality_model.py` |
| Socratic tutoring with graduated hints, grounded in syllabus content (RAG) | `backend/app/tutor/` |
| One structured LLM call per turn: the reply **and** an assessment of the student's answer | `backend/app/llm/` |
| Affect detection (frustration / boredom / confusion / flow / fatigue) → teaching adaptation | `backend/app/engagement/` |
| Session flow: warm-up → stretch → peak → end-high, plus a "what's next" teaser | `engagement/session_designer.py` |
| Per-concept mastery (difficulty-weighted EMA) and a prerequisite map of 33 concepts | `student/mastery_tracker.py`, `app/data/ncert_math_11.json` |
| Adaptive quizzes with validated answer keys and deterministic grading | `backend/app/quiz/` |
| Upload a syllabus PDF / TXT / MD; it's chunked, tagged to concepts and indexed | `backend/app/domain/` |
| Dark-pattern guardrails enforced in code and in the prompt | `engagement/guardrails.py` |

**Website or app?** It's a website, built mobile-first. Students mostly use phones, and a responsive
site works on every phone and laptop with no app-store review. If you later want an installable app,
the same frontend can become a PWA, or be wrapped with Capacitor, without a rewrite.

## Run it locally

Prerequisites: Python 3.12+, Node 22+.

```bash
# 1. Backend (http://localhost:8000, API docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # add ANTHROPIC_API_KEY for real tutoring
uvicorn app.main:app --reload

# 2. Frontend (http://localhost:3000), in a second terminal
cd frontend
npm install
npm run dev
```

**Without an API key** the backend runs in *offline demo mode*: canned, clearly labelled replies that
still exercise every feature (phases, mastery, quizzes, progress map). That makes it safe to develop
and demo without spending anything. **With a key** it uses `claude-sonnet-5-5`, at low effort for
chat (fast replies) and medium effort for quiz generation (correct answer keys matter more than speed).

Docker: `ANTHROPIC_API_KEY=... docker compose up --build` (the compose file and Dockerfiles are
included but haven't been built in CI yet).

## Tests and checks

```bash
cd backend && pytest && ruff check app tests          # 99 tests
cd frontend && npm run lint && npm run typecheck && npm run build
```

GitHub Actions runs both on every change under `tailored-tuition/`.

## Architecture

```
Browser ── Next.js (frontend/) ──/api/* rewrite──▶ FastAPI (backend/app)
                                                    ├─ domain/      syllabus parsing, BM25 retrieval, concept graph
                                                    ├─ student/     persona matching, mastery
                                                    ├─ tutor/       prompts, personas, tutoring loop
                                                    ├─ engagement/  affect, session flow, guardrails, progress map
                                                    ├─ quiz/        generation + grading
                                                    └─ llm/         Anthropic client (structured outputs) + offline stub
                                                   SQLite (dev) / Postgres (prod) via SQLAlchemy
```

API contract: [`docs/API.md`](docs/API.md).

## Known limitations (MVP)

- **No real authentication.** The student id lives in the browser. Add accounts before any real
  deployment.
- **The guardian-consent checkbox is a placeholder** for verifiable parental consent (India's DPDP
  Act 2023 applies to under-18s).
- **PDF maths extraction is lossy** (fractions and superscripts flatten). Prose retrieval works;
  equation fidelity needs an OCR/LaTeX step.
- **LLM answer keys can still be wrong.** Items are structurally validated, not independently solved.
- **The concept graph is hand-curated** from the NCERT Class 11 chapter structure. Check it against
  the current edition.
- **Phase 2 stubs** (`classroom/`, BKT in `knowledge_tracing.py`, the strategizer) are placeholders.
- **SQLite on free hosting tiers is ephemeral.** Use Postgres in production.
