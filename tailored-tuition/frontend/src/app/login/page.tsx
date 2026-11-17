"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { homeFor, useAuth } from "@/components/AuthProvider";
import { Notice, PasswordField, TextField } from "@/components/forms";
import { Button, Card, ErrorNote, Loading, errorMessage, isLimit } from "@/components/ui";

type Tab = "guardian" | "student";

function Login() {
  const params = useSearchParams();
  const { me, setMe } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>(params.get("as") === "student" ? "student" : "guardian");
  const [ident, setIdent] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; limit: boolean } | null>(null);

  useEffect(() => {
    if (me) router.replace(homeFor(me));
  }, [me, router]);

  function switchTab(t: Tab) {
    setTab(t);
    setIdent("");
    setPassword("");
    setError(null);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (tab === "guardian") {
        const res = await api.guardianLogin(ident.trim(), password);
        setMe({ role: "guardian", guardian: res.guardian });
      } else {
        const res = await api.studentLogin(ident.trim().toLowerCase(), password);
        setMe({ role: "student", student: res.student });
      }
      // The effect above redirects once `me` is set.
    } catch (err) {
      setError({ message: errorMessage(err), limit: isLimit(err) });
      setBusy(false);
    }
  }

  if (me === undefined) return <Loading />;

  const tabCls = (t: Tab) =>
    `flex-1 rounded-md px-3 py-2 text-sm font-medium ${tab === t ? "bg-surface text-fg shadow-sm" : "text-muted hover:text-fg"}`;

  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-semibold">Log in</h1>
      {params.get("expired") && <Notice>Your session ended. Please log in again.</Notice>}
      {params.get("reset") && <Notice tone="ok">Password changed. You can log in now.</Notice>}
      <div role="tablist" aria-label="Who is logging in" className="flex gap-1 rounded-lg bg-surface-2 p-1">
        <button role="tab" type="button" aria-selected={tab === "guardian"} aria-controls="login-form" id="tab-guardian" className={tabCls("guardian")} onClick={() => switchTab("guardian")}>
          Parent / guardian
        </button>
        <button role="tab" type="button" aria-selected={tab === "student"} aria-controls="login-form" id="tab-student" className={tabCls("student")} onClick={() => switchTab("student")}>
          Student
        </button>
      </div>
      <Card>
        <form id="login-form" role="tabpanel" aria-labelledby={`tab-${tab}`} onSubmit={onSubmit} className="space-y-4">
          {tab === "guardian" ? (
            <TextField key="email" label="Email" type="email" value={ident} onChange={(e) => setIdent(e.target.value)} autoComplete="email" required />
          ) : (
            <TextField
              key="username"
              label="Username"
              value={ident}
              onChange={(e) => setIdent(e.target.value)}
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              required
              hint="Your parent or guardian set this up for you."
            />
          )}
          <PasswordField
            key={`pw-${tab}`}
            label="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <div aria-live="polite">
            <ErrorNote message={error?.message ?? null} limit={error?.limit} />
          </div>
          <Button type="submit" disabled={busy || !ident.trim() || !password} className="w-full">
            {busy ? "Logging in…" : "Log in"}
          </Button>
        </form>
      </Card>
      {tab === "guardian" ? (
        <div className="flex flex-wrap justify-between gap-2 text-sm">
          <Link href="/forgot-password" className="text-accent underline">
            Forgot password?
          </Link>
          <Link href="/signup" className="text-accent underline">
            Create an account
          </Link>
        </div>
      ) : (
        <p className="text-sm text-muted">Forgot your password? Ask your parent or guardian to set a new one.</p>
      )}
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Login />
    </Suspense>
  );
}
