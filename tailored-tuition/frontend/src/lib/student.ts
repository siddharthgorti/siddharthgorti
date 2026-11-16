// The student id is a per-device convenience; the backend is the source of truth.
const KEY = "tt.studentId";

export function getStudentId(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setStudentId(id: string): void {
  try {
    window.localStorage.setItem(KEY, id);
  } catch {
    // Storage blocked (private mode etc.): the app still works for this tab.
  }
}

export function clearStudentId(): void {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
