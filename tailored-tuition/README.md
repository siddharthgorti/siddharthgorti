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

## Getting and adding an Anthropic API key

1. Go to the **Claude Console** at https://console.anthropic.com and sign up or log in. A Claude.ai
   Pro/Max subscription does **not** include API usage; the API is billed separately, pay-as-you-go.
2. Add credits under **Billing** (a few dollars is plenty for testing), and set a monthly
   **spend limit** so a bug can't run up a bill.
3. Under **API Keys**, choose **Create Key**, name it (e.g. `tailored-tuition-dev`) and copy it. It
   starts with `sk-ant-` and is shown **only once**.
4. Put it in `backend/.env` (copied from `.env.example`):
   ```bash
   ANTHROPIC_API_KEY=sk-ant-...
   ```
5. Restart the backend. `http://localhost:8000/api/health` should now report `"llm_mode": "anthropic"`.

Keep the key secret: `.env` is git-ignored, so never commit it, paste it into chats or put it in
frontend code. If it leaks, delete it in the Console and create a new one. When you deploy, set
`ANTHROPIC_API_KEY` as an environment variable in your host's dashboard (Render, Railway, ...); for
Docker, run `ANTHROPIC_API_KEY=sk-ant-... docker compose up --build`.

## Choosing models

| Setting | Default | Why |
|---|---|---|
| `CHAT_MODEL` / `CHAT_EFFORT` | `claude-sonnet-5-5` / `low` | Runs on every student message, so speed matters. Roughly $0.02 per turn (estimate). |
| `QUIZ_MODEL` / `QUIZ_EFFORT` | `claude-opus-5-5` / `medium` | Runs rarely, and a wrong answer key is the most damaging error. |

These defaults are reasoned estimates, not measurements. To decide on evidence, run the
answer-checking eval. It replays 22 labelled student answers (right, wrong, unusual-but-correct
forms, sign slips, help requests) through the real tutor prompt and reports, per model, how often
each one judges correctness accurately:

```bash
cd backend
python -m evals.run_assessment_eval --dry-run    # shows the plan and estimated cost (~$1.20), spends nothing
python -m evals.run_assessment_eval              # Sonnet 5.5 vs Opus 5.5; asks before spending
python -m evals.run_assessment_eval --models claude-haiku-5-5 claude-sonnet-5-5 --repeats 3
```

Watch the **false-wrong** column most: correct answers marked wrong lower a student's mastery and
can trigger "frustration" handling for no reason. If Sonnet's false-wrong count matches Opus's, keep
Sonnet for chat. With 22 cases a difference of one or two is noise; use `--repeats 3`, or add cases
to `evals/assessment_cases.json`, before switching on a small gap.

Docker: `ANTHROPIC_API_KEY=... docker compose up --build` (the compose file and Dockerfiles are
included but haven't been built in CI yet).

## Tests and checks

```bash
cd backend && pytest && ruff check app tests evals    # 105 tests
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
