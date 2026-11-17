# API Contract (v1)

Backend: FastAPI at `http://localhost:8000`. All routes are prefixed with `/api`.
The Next.js frontend proxies `/api/*` to the backend (see `frontend/next.config.mjs`),
so the browser always calls same-origin `/api/...`.

All bodies are JSON unless noted. Errors use FastAPI's shape: `{"detail": "message"}`
with an appropriate 4xx/5xx status.

## Types

```ts
type PersonaId = "coach" | "challenger" | "explainer" | "mentor";

interface Persona {
  id: PersonaId;
  name: string;          // "The Coach"
  tagline: string;       // one line
  description: string;   // 2-3 sentences, shown on the persona reveal card
}

interface Student {
  id: string;            // uuid
  name: string;
  grade: number;         // 11
  board: string;         // "CBSE"
  persona: PersonaId | null;   // null until onboarding is done
  created_at: string;    // ISO 8601
}

interface OnboardingQuestion {
  id: string;            // "motivation_style"
  question: string;
  options: { index: number; text: string }[];
}

interface OnboardingResult {
  persona: Persona;
  trait_scores: Record<"openness"|"conscientiousness"|"extraversion"|"agreeableness"|"neuroticism", number>; // normalised 0..1
  rationale: string;     // human-readable "why this persona"
}

interface Concept {
  id: string;            // "sets"
  name: string;          // "Sets"
  chapter: number;       // NCERT chapter number
  prerequisites: string[]; // concept ids
}

type Phase = "warmup" | "stretch" | "peak" | "end_high" | "complete";
type Affect = "frustration" | "boredom" | "confusion" | "flow" | "fatigue" | "neutral";
type SessionAdvice = "continue" | "gentle_check" | "suggest_stop";

interface Source { document: string; section: string; snippet: string; }

interface ChatMessage {
  role: "student" | "tutor";
  content: string;       // Markdown; maths in $...$ / $$...$$ (render with KaTeX)
  created_at: string;
}

interface SessionState {
  session_id: string;
  student_id: string;
  concept: Concept;
  persona: Persona;
  phase: Phase;
  problems_in_phase: number;
  phase_plan: { phase: Phase; target_problems: number }[]; // for the flow bar
  mastery: number;       // 0..1 for the session concept
  status: "active" | "ended";
  messages: ChatMessage[];
}

interface TurnResponse {
  reply: ChatMessage;
  sources: Source[];
  affect: Affect;
  phase: Phase;
  problems_in_phase: number;
  mastery: number;
  advice: SessionAdvice;  // UI shows a soft "take a break?" banner on gentle_check / suggest_stop
  teaser: string | null;  // set when the session wraps up
}

interface QuizQuestion {
  id: string;
  type: "mcq" | "numerical";
  prompt: string;         // Markdown + KaTeX
  options: string[] | null;   // MCQ only
  difficulty: number;     // 0..1
}

interface Quiz { quiz_id: string; concept: Concept; questions: QuizQuestion[]; }

interface AnswerResult {
  correct: boolean;
  correct_answer: string;
  explanation: string;    // Markdown + KaTeX
  mastery_after: number;
}

interface MasteryMap {
  concepts: { id: string; name: string; chapter: number; mastery: number;
              status: "mastered" | "learning" | "started" | "not_started" }[];
  connections: { from: string; to: string }[];   // prerequisite -> dependent
  summary: { total_concepts: number; mastered: number; learning: number;
             started: number; not_started: number; overall_progress: number };
}

interface SessionSummary {
  session_id: string; concept: Concept; started_at: string; ended_at: string | null;
  turns: number; mastery_start: number; mastery_end: number;
}

interface SyllabusDocument { id: string; filename: string; sections: number; chunks: number; uploaded_at: string; }
```

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | – | `{status: "ok", llm_mode: "anthropic" \| "ollama" \| "offline", model: string, quiz_model: string}` (`model` = chat model) |
| POST | `/api/students` | `{name: string, guardian_consent: boolean}` | `Student` (400 if consent is false) |
| GET | `/api/students/{id}` | – | `Student` |
| GET | `/api/onboarding/questions` | – | `OnboardingQuestion[]` |
| POST | `/api/students/{id}/onboarding` | `{answers: {question_id: string, option_index: number}[]}` | `OnboardingResult` |
| GET | `/api/personas` | – | `Persona[]` |
| PUT | `/api/students/{id}/persona` | `{persona_id: PersonaId}` | `Student` (student may override the match) |
| GET | `/api/syllabus/concepts` | – | `Concept[]` (ordered by chapter) |
| GET | `/api/syllabus/documents` | – | `SyllabusDocument[]` |
| POST | `/api/syllabus/upload` | multipart form, field `file` (.pdf, .txt, .md; ≤ 20 MB) | `SyllabusDocument` |
| POST | `/api/sessions` | `{student_id: string, concept_id: string}` | `SessionState` (first tutor message already in `messages`) |
| GET | `/api/sessions/{id}` | – | `SessionState` |
| POST | `/api/sessions/{id}/messages` | `{content: string, latency_seconds: number \| null}` | `TurnResponse` |
| POST | `/api/sessions/{id}/end` | – | `{teaser: string, mastery: number}` |
| GET | `/api/students/{id}/sessions` | – | `SessionSummary[]` (newest first) |
| GET | `/api/students/{id}/mastery-map` | – | `MasteryMap` |
| POST | `/api/quiz` | `{student_id: string, concept_id: string, num_questions?: number (1-10, default 5)}` | `Quiz` |
| POST | `/api/quiz/{quiz_id}/answers` | `{question_id: string, answer: string}` | `AnswerResult` |

For MCQ questions, `answer` is the **0-based option index** as a string (e.g. `"2"`); for numerical
questions it is the student's number (integer, decimal or fraction like `3/4`).

`latency_seconds`: seconds between the tutor's last message rendering and the student
pressing send (measured client-side). Send `null` if unknown.

Onboarding must precede sessions: `POST /api/sessions` returns 409 if the student has no persona.
