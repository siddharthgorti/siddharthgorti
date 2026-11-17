"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, setUnauthorizedHandler } from "@/lib/api";
import type { Guardian, Me, Student } from "@/lib/types";

interface AuthCtx {
  /** undefined = still loading, null = nobody logged in. */
  me: Me | null | undefined;
  refresh: () => Promise<Me | null>;
  /** Replace the cached identity after an action that returns the new state (login, onboarding). */
  setMe: (me: Me | null) => void;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

// Pages anyone may see; a 401 on them is not a reason to bounce to /login.
const PUBLIC_PATHS = ["/", "/login", "/signup", "/verify", "/forgot-password", "/reset-password", "/privacy"];

export const homeFor = (me: Me) =>
  me.role === "guardian" ? "/guardian" : me.student.persona ? "/learn" : "/onboarding";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const router = useRouter();

  const refresh = useCallback(async (): Promise<Me | null> => {
    try {
      const m = await api.me();
      setMe(m);
      return m;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setMe(null);
        return null;
      }
      throw e;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((m) => !cancelled && setMe(m))
      .catch(() => !cancelled && setMe(null));
    return () => {
      cancelled = true;
    };
  }, []);

  // Session expired mid-use → forget the identity and go to the login page.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setMe(null);
      if (!PUBLIC_PATHS.includes(window.location.pathname)) router.replace("/login?expired=1");
    });
    return () => setUnauthorizedHandler(null);
  }, [router]);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setMe(null);
      router.replace("/login");
    }
  }, [router]);

  return <Ctx.Provider value={{ me, refresh, setMe, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/**
 * The logged-in student, once loaded. Redirects: nobody → /login, guardian → /guardian,
 * no persona yet (when requirePersona) → /onboarding. Returns null while redirecting/loading.
 */
export function useRequiredStudent({ requirePersona = true } = {}): Student | null {
  const { me } = useAuth();
  const router = useRouter();
  const target =
    me === undefined
      ? null
      : me === null
        ? "/login"
        : me.role !== "student"
          ? "/guardian"
          : requirePersona && me.student.persona === null
            ? "/onboarding"
            : null;

  useEffect(() => {
    if (target) router.replace(target);
  }, [target, router]);

  if (!me || target || me.role !== "student") return null;
  return me.student;
}

/** The logged-in guardian, once loaded. Redirects: nobody → /login, student → their home. */
export function useRequiredGuardian(): Guardian | null {
  const { me } = useAuth();
  const router = useRouter();
  const target = me === undefined ? null : me === null ? "/login" : me.role !== "guardian" ? homeFor(me) : null;

  useEffect(() => {
    if (target) router.replace(target);
  }, [target, router]);

  if (!me || target || me.role !== "guardian") return null;
  return me.guardian;
}
