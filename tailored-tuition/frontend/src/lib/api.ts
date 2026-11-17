import type {
  AnswerResult,
  ChildSummary,
  Concept,
  Guardian,
  Health,
  MasteryMap,
  Me,
  OnboardingQuestion,
  OnboardingResult,
  Persona,
  PersonaId,
  PrivacyPolicy,
  Quiz,
  SessionState,
  SessionSummary,
  Student,
  SyllabusDocument,
  TurnResponse,
} from "./types";

/** Error carrying the HTTP status and the backend's `detail` message (always user-readable). */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Called when a request that needs a login gets 401 (session expired / logged out elsewhere).
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

interface Opts extends RequestInit {
  /** Don't trigger the global "go to login" on 401 (login forms, /auth/me). */
  quiet401?: boolean;
}

async function send(path: string, { quiet401, ...init }: Opts = {}): Promise<Response> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  // CSRF rule (docs/API.md): every unsafe request carries this header.
  if (UNSAFE.has(method)) headers.set("X-TT-CSRF", "1");
  const res = await fetch(`/api${path}`, { ...init, method, headers, credentials: "same-origin" });
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
    if (res.status === 401 && !quiet401) onUnauthorized?.();
    throw new ApiError(detail, res.status);
  }
  return res;
}

async function request<T>(path: string, init?: Opts): Promise<T> {
  return (await (await send(path, init)).json()) as T;
}

async function requestNoContent(path: string, init?: Opts): Promise<void> {
  await send(path, init);
}

const post = (body?: unknown, extra?: Opts): Opts => ({
  method: "POST",
  body: body === undefined ? undefined : JSON.stringify(body),
  ...extra,
});
const put = (body: unknown): Opts => ({ method: "PUT", body: JSON.stringify(body) });
const enc = encodeURIComponent;

export const api = {
  health: () => request<Health>("/health"),
  privacyPolicy: () => request<PrivacyPolicy>("/privacy/policy"),

  // --- auth -----------------------------------------------------------------
  me: () => request<Me>("/auth/me", { quiet401: true }),
  guardianSignup: (name: string, email: string, password: string) =>
    request<{ guardian: Guardian; dev_verification_url: string | null }>(
      "/auth/guardian/signup",
      post({ name, email, password }, { quiet401: true }),
    ),
  verifyEmail: (token: string) =>
    request<{ guardian: Guardian }>("/auth/guardian/verify", post({ token }, { quiet401: true })),
  resendVerification: () =>
    request<{ dev_verification_url: string | null }>("/auth/guardian/resend-verification", post()),
  guardianLogin: (email: string, password: string) =>
    request<{ guardian: Guardian }>("/auth/guardian/login", post({ email, password }, { quiet401: true })),
  forgotPassword: (email: string) =>
    request<{ dev_reset_url: string | null }>(
      "/auth/guardian/forgot-password",
      post({ email }, { quiet401: true }),
    ),
  resetPassword: (token: string, password: string) =>
    request<{ guardian: Guardian }>(
      "/auth/guardian/reset-password",
      post({ token, password }, { quiet401: true }),
    ),
  studentLogin: (username: string, password: string) =>
    request<{ student: Student }>("/auth/student/login", post({ username, password }, { quiet401: true })),
  logout: () => requestNoContent("/auth/logout", post(undefined, { quiet401: true })),

  // --- guardian -------------------------------------------------------------
  children: () => request<ChildSummary[]>("/guardian/students"),
  addChild: (name: string, username: string, password: string, policy_version: string) =>
    request<Student>("/guardian/students", post({ name, username, password, consent: true, policy_version })),
  setChildPassword: (id: string, password: string) =>
    requestNoContent(`/guardian/students/${enc(id)}/password`, put({ password })),
  /** Raw export response, so the caller can save it as a file. */
  exportChild: async (id: string) => (await send(`/guardian/students/${enc(id)}/export`)).blob(),
  deleteChild: (id: string) => requestNoContent(`/guardian/students/${enc(id)}`, { method: "DELETE" }),
  deleteAccount: (password: string) =>
    requestNoContent("/guardian/account", { method: "DELETE", body: JSON.stringify({ password }) }),

  // --- students ---------------------------------------------------------------
  getStudent: (id: string) => request<Student>(`/students/${enc(id)}`),
  onboardingQuestions: () => request<OnboardingQuestion[]>("/onboarding/questions"),
  submitOnboarding: (studentId: string, answers: { question_id: string; option_index: number }[]) =>
    request<OnboardingResult>(`/students/${enc(studentId)}/onboarding`, post({ answers })),
  personas: () => request<Persona[]>("/personas"),
  setPersona: (studentId: string, persona_id: PersonaId) =>
    request<Student>(`/students/${enc(studentId)}/persona`, put({ persona_id })),
  sessionHistory: (studentId: string) => request<SessionSummary[]>(`/students/${enc(studentId)}/sessions`),
  masteryMap: (studentId: string) => request<MasteryMap>(`/students/${enc(studentId)}/mastery-map`),

  // --- syllabus -----------------------------------------------------------------
  concepts: () => request<Concept[]>("/syllabus/concepts"),
  documents: () => request<SyllabusDocument[]>("/syllabus/documents"),
  uploadSyllabus: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<SyllabusDocument>("/syllabus/upload", { method: "POST", body: form });
  },

  // --- tutoring and quizzes (the logged-in student is implied) ---------------------
  createSession: (concept_id: string) => request<SessionState>("/sessions", post({ concept_id })),
  getSession: (id: string) => request<SessionState>(`/sessions/${enc(id)}`),
  sendMessage: (id: string, content: string, latency_seconds: number | null) =>
    request<TurnResponse>(`/sessions/${enc(id)}/messages`, post({ content, latency_seconds })),
  endSession: (id: string) => request<{ teaser: string; mastery: number }>(`/sessions/${enc(id)}/end`, post()),
  createQuiz: (concept_id: string, num_questions = 5) => request<Quiz>("/quiz", post({ concept_id, num_questions })),
  /** `answer`: MCQ → 0-based option index as a string ("2"); numerical → the typed value. */
  answerQuiz: (quizId: string, question_id: string, answer: string) =>
    request<AnswerResult>(`/quiz/${enc(quizId)}/answers`, post({ question_id, answer })),
};
