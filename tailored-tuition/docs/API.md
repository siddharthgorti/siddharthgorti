# API Contract (v2: accounts and consent)

Backend: FastAPI at `http://localhost:8000`, every route under `/api`. The Next.js frontend proxies
`/api/*` to it (`frontend/next.config.mjs`), so the browser always calls same-origin `/api/...`.

Bodies are JSON unless noted. Errors: `{"detail": "message"}` with a 4xx/5xx status. The frontend
shows `detail` to the user; it is always written to be readable.

## Accounts, sessions and security rules

**Who uses it.** A **guardian** (parent/guardian, an adult) signs up with an email and password,
verifies the email, and then creates **student** logins for their children, giving consent for each.
Students log in with the username and password their guardian set. There is no student self-signup.

**Sessions.** Logging in sets an `HttpOnly`, `SameSite=Lax` cookie `tt_session` (also `Secure` in
production). The browser sends it automatically on same-origin requests; the frontend never reads it.
`GET /api/auth/me` says who is logged in (401 if nobody).

**CSRF rule.** Every `POST`, `PUT`, `PATCH` and `DELETE` must carry the header `X-TT-CSRF: 1`, or the
backend answers 403. (A cross-site page cannot add a custom header without a CORS preflight the
backend refuses.) The frontend's API client adds it to every unsafe request, uploads included.

**Status codes the frontend must handle.**
- `401`: not logged in, or the session expired → go to `/login`.
- `403`: logged in but not allowed (wrong role, someone else's data, email not verified, not admin).
- `404`: not found, also used for "exists but isn't yours".
- `409`: conflict (username taken, onboarding not done yet).
- `413`: request too large.
- `429`: a usage limit or a login lockout; `detail` says what and when it resets.
- `503`: the AI is unavailable; `detail` is user-facing.

**Ownership.** A student may access only their own data. A guardian may *read* their own children's
data (profile, mastery map, session history, a session's transcript) but cannot chat or take quizzes
as them. Admin guardians (emails in `ADMIN_EMAILS`) may upload syllabus files.

**Usage limits (per student, per UTC day, configurable).** Tutor messages: 200. New tutor sessions:
30. Quizzes: 20. Exceeding one returns 429.

**Login protection.** 10 failed logins for one email or username within 15 minutes locks that login
for 15 minutes (429). Sign-ups are capped at 30 per hour across the service.

**Passwords.** Guardian: 10–128 characters. Student: 8–128 characters. Usernames: 3–30 characters of
`a-z 0-9 . _ -`, case-insensitive, unique.

## Types

```ts
type PersonaId = "coach" | "challenger" | "explainer" | "mentor";

interface Persona { id: PersonaId; name: string; tagline: string; description: string; }

interface Guardian {
  id: string; name: string; email: string;
  email_verified: boolean;   // must be true before adding children
  is_admin: boolean;         // may upload syllabus files
  created_at: string;        // ISO 8601
}

interface Student {
  id: string; name: string; username: string;
  grade: number; board: string;
  persona: PersonaId | null; // null until onboarding is done
  created_at: string;
}

interface ChildSummary extends Student {
  overall_progress: number;  // 0..1, mean mastery
  mastered: number;          // concepts mastered
  last_active: string | null;
}

type Me = { role: "guardian"; guardian: Guardian } | { role: "student"; student: Student };

interface PrivacyPolicy { version: string; updated: string; }  // the text lives on the /privacy page

interface OnboardingQuestion { id: string; question: string; options: { index: number; text: string }[]; }

interface OnboardingResult {
  persona: Persona;
  trait_scores: Record<"openness"|"conscientiousness"|"extraversion"|"agreeableness"|"neuroticism", number>;
  // shown once on the reveal screen; NOT stored by the backend (data minimisation)
  rationale: string;
}

interface Concept { id: string; name: string; chapter: number; prerequisites: string[]; }

type Phase = "warmup" | "stretch" | "peak" | "end_high" | "complete";
type Affect = "frustration" | "boredom" | "confusion" | "flow" | "fatigue" | "neutral";
type SessionAdvice = "continue" | "gentle_check" | "suggest_stop";

interface Source { document: string; section: string; snippet: string; }
interface ChatMessage { role: "student" | "tutor"; content: string; created_at: string; }  // Markdown + KaTeX

interface SessionState {
  session_id: string; student_id: string; concept: Concept; persona: Persona;
  phase: Phase; problems_in_phase: number;
  phase_plan: { phase: Phase; target_problems: number }[];
  mastery: number; status: "active" | "ended"; messages: ChatMessage[];
}

interface TurnResponse {
  reply: ChatMessage; sources: Source[]; affect: Affect; phase: Phase; problems_in_phase: number;
  mastery: number; advice: SessionAdvice; teaser: string | null;
}

interface QuizQuestion { id: string; type: "mcq" | "numerical"; prompt: string; options: string[] | null; difficulty: number; }
interface Quiz { quiz_id: string; concept: Concept; questions: QuizQuestion[]; }
interface AnswerResult { correct: boolean; correct_answer: string; explanation: string; mastery_after: number; }

interface MasteryMap {
  concepts: { id: string; name: string; chapter: number; mastery: number;
              status: "mastered" | "learning" | "started" | "not_started" }[];
  connections: { from: string; to: string }[];
  summary: { total_concepts: number; mastered: number; learning: number;
             started: number; not_started: number; overall_progress: number };
}

interface SessionSummary {
  session_id: string; concept: Concept; started_at: string; ended_at: string | null;
  turns: number; mastery_start: number; mastery_end: number;  // current level while open
}

interface SyllabusDocument { id: string; filename: string; sections: number; chunks: number; uploaded_at: string; }
```

## Endpoints

Access: **public** = no login · **any** = any logged-in user · **guardian** · **student** ·
**admin** (guardian in `ADMIN_EMAILS`) · **owner** = the student themself or their guardian (read).

### Meta and public data
| Method | Path | Access | Body | Returns |
|---|---|---|---|---|
| GET | `/api/health` | public | – | `{status, llm_mode: "anthropic"\|"ollama"\|"offline", model, quiz_model}` |
| GET | `/api/privacy/policy` | public | – | `PrivacyPolicy` |
| GET | `/api/onboarding/questions` | public | – | `OnboardingQuestion[]` |
| GET | `/api/personas` | public | – | `Persona[]` |
| GET | `/api/syllabus/concepts` | public | – | `Concept[]` |

### Auth
| Method | Path | Access | Body | Returns |
|---|---|---|---|---|
| POST | `/api/auth/guardian/signup` | public | `{name, email, password}` | 201 `{guardian: Guardian, dev_verification_url: string \| null}` and logs in (unverified) |
| POST | `/api/auth/guardian/verify` | public | `{token}` | `{guardian}`, logs in |
| POST | `/api/auth/guardian/resend-verification` | guardian | – | `{dev_verification_url: string \| null}` |
| POST | `/api/auth/guardian/login` | public | `{email, password}` | `{guardian}` |
| POST | `/api/auth/guardian/forgot-password` | public | `{email}` | 202 `{dev_reset_url: string \| null}` (same answer whether or not the email exists) |
| POST | `/api/auth/guardian/reset-password` | public | `{token, password}` | `{guardian}`, logs in, ends all other sessions |
| POST | `/api/auth/student/login` | public | `{username, password}` | `{student}` |
| POST | `/api/auth/logout` | any | – | 204 |
| GET | `/api/auth/me` | any | – | `Me` (401 if not logged in) |

`dev_verification_url` / `dev_reset_url` are non-null **only** in local development with the console
email backend (no real email is sent), so local demos work without an email server. The frontend
shows them as a "Dev mode: open verification link" button. In production they are always null and
the link arrives by email. Links point to `/verify?token=...` and `/reset-password?token=...`.

### Guardian
| Method | Path | Access | Body | Returns |
|---|---|---|---|---|
| GET | `/api/guardian/students` | guardian | – | `ChildSummary[]` |
| POST | `/api/guardian/students` | guardian (verified) | `{name, username, password, consent: true, policy_version: string}` | 201 `Student` |
| PUT | `/api/guardian/students/{id}/password` | guardian | `{password}` | 204; logs the child out everywhere |
| GET | `/api/guardian/students/{id}/export` | guardian | – | all of the child's data as JSON (download) |
| DELETE | `/api/guardian/students/{id}` | guardian | – | 204; permanently deletes the child's data (withdraws consent) |
| DELETE | `/api/guardian/account` | guardian | `{password}` | 204; deletes the guardian and every child |

`consent` must be literally `true` and `policy_version` must equal the current policy version.
The backend records who consented, when, and to which version.

### Students, onboarding and progress
| Method | Path | Access | Body | Returns |
|---|---|---|---|---|
| GET | `/api/students/{id}` | owner | – | `Student` |
| POST | `/api/students/{id}/onboarding` | student (self) | `{answers: {question_id, option_index}[]}` | `OnboardingResult` |
| PUT | `/api/students/{id}/persona` | student (self) | `{persona_id}` | `Student` |
| GET | `/api/students/{id}/sessions` | owner | – | `SessionSummary[]` (newest first) |
| GET | `/api/students/{id}/mastery-map` | owner | – | `MasteryMap` |

### Tutoring and quizzes (the logged-in student is implied)
| Method | Path | Access | Body | Returns |
|---|---|---|---|---|
| POST | `/api/sessions` | student | `{concept_id}` | 201 `SessionState` (409 if no persona yet; 429 at the daily limit) |
| GET | `/api/sessions/{id}` | owner | – | `SessionState` |
| POST | `/api/sessions/{id}/messages` | student (self) | `{content, latency_seconds: number \| null}` | `TurnResponse` |
| POST | `/api/sessions/{id}/end` | student (self) | – | `{teaser, mastery}` |
| POST | `/api/quiz` | student | `{concept_id, num_questions?: 1-10}` | 201 `Quiz` |
| POST | `/api/quiz/{quiz_id}/answers` | student (self) | `{question_id, answer}` | `AnswerResult` |

MCQ `answer` = the 0-based option index as a string; numerical = the number (`12`, `0.5`, `3/4`).
`latency_seconds` = seconds from the tutor's last message rendering to the student pressing send.

### Syllabus files
| Method | Path | Access | Body | Returns |
|---|---|---|---|---|
| GET | `/api/syllabus/documents` | any | – | `SyllabusDocument[]` |
| POST | `/api/syllabus/upload` | admin | multipart field `file` (.pdf/.txt/.md, ≤ 20 MB) | 201 `SyllabusDocument` |

## Configuration (backend environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `APP_ENV` | `development` | `production` turns on the startup safety checks below |
| `PUBLIC_URL` | `http://localhost:3000` | Base of links in emails |
| `EMAIL_BACKEND` | `console` | `console` (log only; dev links returned) or `smtp` |
| `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | – | SMTP settings (STARTTLS) |
| `COOKIE_SECURE` | `false` | `true` behind HTTPS |
| `ADMIN_EMAILS` | empty | Comma-separated guardian emails allowed to upload syllabus files |
| `PRIVACY_POLICY_VERSION` | `2026-11-17` | Bump when the privacy notice changes |
| `MAX_MESSAGES_PER_DAY`, `MAX_SESSIONS_PER_DAY`, `MAX_QUIZZES_PER_DAY` | 200, 30, 20 | Per-student daily limits |
| `SEED_DEMO_ACCOUNTS` | `false` | Development only: create a demo guardian and 3 students; logins written to `backend/data/demo-accounts.txt` |
| `DATABASE_URL` | SQLite file | Postgres in production: `postgresql+psycopg://user:pass@host/db` |

With `APP_ENV=production` the backend **refuses to start** unless `EMAIL_BACKEND=smtp`,
`COOKIE_SECURE=true`, `PUBLIC_URL` starts with `https://`, and `DATABASE_URL` is not SQLite.
