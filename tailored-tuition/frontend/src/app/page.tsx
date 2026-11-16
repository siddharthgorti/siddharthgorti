"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { Button, Card, ErrorNote, errorMessage } from "@/components/ui";
import { useStudentContext } from "@/components/StudentProvider";
import SyllabusPanel from "@/components/SyllabusPanel";

export default function Home() {
  const { student, setStudent, signOut } = useStudentContext();
  const router = useRouter();
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onStart(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !consent) return;
    setBusy(true);
    setError(null);
    try {
      const s = await api.createStudent(name.trim(), consent);
      setStudent(s);
      router.push("/onboarding");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="space-y-3 pt-4">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          A maths tutor that teaches the way you learn.
        </h1>
        <p className="max-w-2xl text-muted">
          For CBSE Class 11 Mathematics. Your tutor asks guiding questions instead of handing
          over answers, gives one hint at a time, notices when you are stuck or tired, and
          shows your progress as a map of ideas — not points.
        </p>
      </section>

      {student === undefined ? null : student ? (
        <Card className="space-y-3">
          <p>
            Welcome back, <strong>{student.name}</strong>. Ready when you are.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link
              href={student.persona ? "/learn" : "/onboarding"}
              className="inline-flex min-h-10 items-center rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-fg hover:opacity-90"
            >
              Continue
            </Link>
            <Button variant="ghost" onClick={signOut}>
              Not {student.name}? Start fresh
            </Button>
          </div>
        </Card>
      ) : (
        <Card>
          <form onSubmit={onStart} className="space-y-4" aria-labelledby="start-heading">
            <h2 id="start-heading" className="text-lg font-semibold">
              Get started
            </h2>
            <div className="space-y-1">
              <label htmlFor="name" className="block text-sm font-medium">
                Your first name
              </label>
              <input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={60}
                autoComplete="given-name"
                required
                className="w-full rounded-lg border border-border bg-bg px-3 py-2"
              />
            </div>
            <label className="flex items-start gap-3 rounded-lg bg-surface-2 p-3 text-sm">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                required
                className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--accent)]"
              />
              <span>
                I am a parent or guardian of this student (who is under 18), and I agree to
                Tailored Tuition storing their learning data — chat messages, quiz answers and
                progress — so the tutor can adapt to them. It is never shown to other students
                or used for advertising.
              </span>
            </label>
            <ErrorNote message={error} />
            <Button type="submit" disabled={busy || !name.trim() || !consent}>
              {busy ? "Setting up…" : "Start"}
            </Button>
          </form>
        </Card>
      )}

      <SyllabusPanel />
    </div>
  );
}
