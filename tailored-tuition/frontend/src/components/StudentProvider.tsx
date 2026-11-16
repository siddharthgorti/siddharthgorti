"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { clearStudentId, getStudentId, setStudentId } from "@/lib/student";
import type { Student } from "@/lib/types";

interface StudentCtx {
  /** undefined = still loading, null = no student on this device. */
  student: Student | null | undefined;
  setStudent: (s: Student) => void;
  signOut: () => void;
}

const Ctx = createContext<StudentCtx | null>(null);

export function StudentProvider({ children }: { children: ReactNode }) {
  const [student, setStudentState] = useState<Student | null | undefined>(undefined);

  useEffect(() => {
    // localStorage is only readable after mount (no SSR), hence the effect.
    let cancelled = false;
    const load = async (): Promise<Student | null> => {
      const id = getStudentId();
      if (!id) return null;
      try {
        return await api.getStudent(id);
      } catch (e) {
        // Unknown id (e.g. backend DB was reset): start fresh.
        if (e instanceof ApiError && e.status === 404) clearStudentId();
        return null;
      }
    };
    void load().then((s) => {
      if (!cancelled) setStudentState(s);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const setStudent = useCallback((s: Student) => {
    setStudentId(s.id);
    setStudentState(s);
  }, []);

  const signOut = useCallback(() => {
    clearStudentId();
    setStudentState(null);
  }, []);

  return <Ctx.Provider value={{ student, setStudent, signOut }}>{children}</Ctx.Provider>;
}

export function useStudentContext(): StudentCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useStudentContext must be used inside StudentProvider");
  return ctx;
}

/**
 * Returns the student once loaded and redirects when the page's preconditions
 * fail: no student → "/", no persona (and requirePersona) → "/onboarding".
 */
export function useRequiredStudent({ requirePersona = true } = {}): Student | null {
  const { student } = useStudentContext();
  const router = useRouter();

  const missing = student === null;
  const needsOnboarding = !!student && requirePersona && student.persona === null;

  useEffect(() => {
    if (missing) router.replace("/");
    else if (needsOnboarding) router.replace("/onboarding");
  }, [missing, needsOnboarding, router]);

  if (!student || needsOnboarding) return null;
  return student;
}
