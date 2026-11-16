import type {
  AnswerResult,
  Concept,
  Health,
  MasteryMap,
  OnboardingQuestion,
  OnboardingResult,
  Persona,
  PersonaId,
  Quiz,
  SessionState,
  SessionSummary,
  Student,
  SyllabusDocument,
  TurnResponse,
} from "./types";

/** Error carrying the HTTP status and the backend's `detail` message. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData;
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: isForm
      ? init?.headers
      : { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body: unknown = await res.json();
      if (body && typeof body === "object" && "detail" in body) {
        const d = (body as { detail: unknown }).detail;
        // FastAPI validation errors return an array of {msg} objects.
        if (typeof d === "string") detail = d;
        else if (Array.isArray(d))
          detail = d
            .map((e) => (e && typeof e === "object" && "msg" in e ? String(e.msg) : String(e)))
            .join("; ");
      }
    } catch {
      // Non-JSON error body: keep the generic message.
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/health"),

  createStudent: (name: string, guardian_consent: boolean) =>
    request<Student>("/students", json({ name, guardian_consent })),
  getStudent: (id: string) =>
    request<Student>(`/students/${encodeURIComponent(id)}`),

  onboardingQuestions: () => request<OnboardingQuestion[]>("/onboarding/questions"),
  submitOnboarding: (
    studentId: string,
    answers: { question_id: string; option_index: number }[],
  ) =>
    request<OnboardingResult>(
      `/students/${encodeURIComponent(studentId)}/onboarding`,
      json({ answers }),
    ),

  personas: () => request<Persona[]>("/personas"),
  setPersona: (studentId: string, persona_id: PersonaId) =>
    request<Student>(`/students/${encodeURIComponent(studentId)}/persona`, {
      method: "PUT",
      body: JSON.stringify({ persona_id }),
    }),

  concepts: () => request<Concept[]>("/syllabus/concepts"),
  documents: () => request<SyllabusDocument[]>("/syllabus/documents"),
  uploadSyllabus: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<SyllabusDocument>("/syllabus/upload", {
      method: "POST",
      body: form,
    });
  },

  createSession: (student_id: string, concept_id: string) =>
    request<SessionState>("/sessions", json({ student_id, concept_id })),
  getSession: (id: string) =>
    request<SessionState>(`/sessions/${encodeURIComponent(id)}`),
  sendMessage: (id: string, content: string, latency_seconds: number | null) =>
    request<TurnResponse>(
      `/sessions/${encodeURIComponent(id)}/messages`,
      json({ content, latency_seconds }),
    ),
  endSession: (id: string) =>
    request<{ teaser: string; mastery: number }>(
      `/sessions/${encodeURIComponent(id)}/end`,
      { method: "POST" },
    ),
  sessionHistory: (studentId: string) =>
    request<SessionSummary[]>(`/students/${encodeURIComponent(studentId)}/sessions`),

  masteryMap: (studentId: string) =>
    request<MasteryMap>(`/students/${encodeURIComponent(studentId)}/mastery-map`),

  createQuiz: (student_id: string, concept_id: string, num_questions = 5) =>
    request<Quiz>("/quiz", json({ student_id, concept_id, num_questions })),
  /** `answer`: MCQ → 0-based option index as a string ("2"); numerical → the typed value. */
  answerQuiz: (quizId: string, question_id: string, answer: string) =>
    request<AnswerResult>(
      `/quiz/${encodeURIComponent(quizId)}/answers`,
      json({ question_id, answer }),
    ),
};
