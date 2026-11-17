// Mirrors docs/API.md (contract v1). Keep in sync with the backend.

export type PersonaId = "coach" | "challenger" | "explainer" | "mentor";

export interface Persona {
  id: PersonaId;
  name: string;
  tagline: string;
  description: string;
}

export interface Student {
  id: string;
  name: string;
  grade: number;
  board: string;
  persona: PersonaId | null;
  created_at: string;
}

export interface OnboardingQuestion {
  id: string;
  question: string;
  options: { index: number; text: string }[];
}

export type Trait =
  | "openness"
  | "conscientiousness"
  | "extraversion"
  | "agreeableness"
  | "neuroticism";

export interface OnboardingResult {
  persona: Persona;
  trait_scores: Record<Trait, number>;
  rationale: string;
}

export interface Concept {
  id: string;
  name: string;
  chapter: number;
  prerequisites: string[];
}

export type Phase = "warmup" | "stretch" | "peak" | "end_high" | "complete";
export type Affect =
  | "frustration"
  | "boredom"
  | "confusion"
  | "flow"
  | "fatigue"
  | "neutral";
export type SessionAdvice = "continue" | "gentle_check" | "suggest_stop";

export interface Source {
  document: string;
  section: string;
  snippet: string;
}

export interface ChatMessage {
  role: "student" | "tutor";
  content: string;
  created_at: string;
}

export interface SessionState {
  session_id: string;
  student_id: string;
  concept: Concept;
  persona: Persona;
  phase: Phase;
  problems_in_phase: number;
  phase_plan: { phase: Phase; target_problems: number }[];
  mastery: number;
  status: "active" | "ended";
  messages: ChatMessage[];
}

export interface TurnResponse {
  reply: ChatMessage;
  sources: Source[];
  affect: Affect;
  phase: Phase;
  problems_in_phase: number;
  mastery: number;
  advice: SessionAdvice;
  teaser: string | null;
}

export interface QuizQuestion {
  id: string;
  type: "mcq" | "numerical";
  prompt: string;
  options: string[] | null;
  difficulty: number;
}

export interface Quiz {
  quiz_id: string;
  concept: Concept;
  questions: QuizQuestion[];
}

export interface AnswerResult {
  correct: boolean;
  correct_answer: string;
  explanation: string;
  mastery_after: number;
}

export type MasteryStatus = "mastered" | "learning" | "started" | "not_started";

export interface MasteryConcept {
  id: string;
  name: string;
  chapter: number;
  mastery: number;
  status: MasteryStatus;
}

export interface MasteryMap {
  concepts: MasteryConcept[];
  connections: { from: string; to: string }[];
  summary: {
    total_concepts: number;
    mastered: number;
    learning: number;
    started: number;
    not_started: number;
    overall_progress: number;
  };
}

export interface SessionSummary {
  session_id: string;
  concept: Concept;
  started_at: string;
  ended_at: string | null;
  turns: number;
  mastery_start: number;
  mastery_end: number;
}

export interface SyllabusDocument {
  id: string;
  filename: string;
  sections: number;
  chunks: number;
  uploaded_at: string;
}

export interface Health {
  status: "ok";
  llm_mode: "anthropic" | "ollama" | "offline";
  model: string;
  quiz_model: string;
}
