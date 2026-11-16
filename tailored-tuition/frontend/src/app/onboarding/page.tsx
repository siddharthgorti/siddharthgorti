"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { OnboardingQuestion, OnboardingResult, Persona, PersonaId, Trait } from "@/lib/types";
import { Button, Card, ErrorNote, Loading, Meter, errorMessage } from "@/components/ui";
import PersonaCard from "@/components/PersonaCard";
import { useRequiredStudent, useStudentContext } from "@/components/StudentProvider";

const TRAIT_LABEL: Record<Trait, string> = {
  openness: "Curiosity / openness",
  conscientiousness: "Structure / conscientiousness",
  extraversion: "Discussion / extraversion",
  agreeableness: "Warmth / agreeableness",
  neuroticism: "Wants reassurance",
};

export default function OnboardingPage() {
  const student = useRequiredStudent({ requirePersona: false });
  const { setStudent } = useStudentContext();
  const router = useRouter();

  const [questions, setQuestions] = useState<OnboardingQuestion[] | null>(null);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [result, setResult] = useState<OnboardingResult | null>(null);
  const [personas, setPersonas] = useState<Persona[] | null>(null);
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.onboardingQuestions().then(setQuestions).catch((e) => setError(errorMessage(e)));
  }, []);

  if (!student) return <Loading />;
  if (!questions) return error ? <ErrorNote message={error} /> : <Loading />;

  async function submit(final: Record<string, number>) {
    if (!student || !questions) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.submitOnboarding(
        student.id,
        questions.map((q) => ({ question_id: q.id, option_index: final[q.id] })),
      );
      setResult(res);
      setStudent({ ...student, persona: res.persona.id });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  function choose(qid: string, index: number) {
    const next = { ...answers, [qid]: index };
    setAnswers(next);
    if (step < questions!.length - 1) setStep(step + 1);
    else void submit(next);
  }

  async function openPicker() {
    setPicking(true);
    if (!personas) {
      try {
        setPersonas(await api.personas());
      } catch (e) {
        setError(errorMessage(e));
      }
    }
  }

  async function pick(id: PersonaId) {
    if (!student) return;
    setBusy(true);
    setError(null);
    try {
      const s = await api.setPersona(student.id, id);
      setStudent(s);
      router.push("/learn");
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  }

  if (result) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Meet your tutor</h1>
        <Card className="space-y-4">
          <PersonaCard persona={result.persona} />
          <p className="text-sm">{result.rationale}</p>
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">
              What your answers suggested
            </p>
            {(Object.keys(TRAIT_LABEL) as Trait[]).map((t) => (
              <div key={t} className="grid grid-cols-[minmax(0,10rem)_1fr] items-center gap-3 text-sm">
                <span className="truncate text-muted">{TRAIT_LABEL[t]}</span>
                <Meter value={result.trait_scores[t] ?? 0} label={TRAIT_LABEL[t]} />
              </div>
            ))}
            <p className="text-xs text-muted">
              Five questions are a rough guide, not a personality test. You can switch tutors any time.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => router.push("/learn")}>Start learning</Button>
            <Button variant="secondary" onClick={openPicker}>
              Not quite me — pick another
            </Button>
          </div>
        </Card>
        <ErrorNote message={error} />
        {picking && (
          <section aria-labelledby="pick-heading" className="space-y-3">
            <h2 id="pick-heading" className="text-lg font-semibold">
              Choose a tutor
            </h2>
            {!personas ? (
              <Loading />
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2">
                {personas.map((p) => (
                  <li key={p.id}>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => pick(p.id)}
                      aria-pressed={p.id === result.persona.id}
                      className={`h-full w-full rounded-xl border bg-surface p-4 text-left transition hover:bg-surface-2 disabled:opacity-50 ${
                        p.id === result.persona.id ? "border-accent" : "border-border"
                      }`}
                    >
                      <PersonaCard persona={p} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </div>
    );
  }

  const q = questions[step];
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <p className="text-sm text-muted">
          Question {step + 1} of {questions.length} — there are no wrong answers.
        </p>
        <Meter value={step / questions.length} label="Onboarding progress" />
      </div>
      <Card className="space-y-4">
        <h1 className="text-xl font-semibold" id="q-heading">
          {q.question}
        </h1>
        <ul className="space-y-2" aria-labelledby="q-heading">
          {q.options.map((o) => (
            <li key={o.index}>
              <button
                type="button"
                disabled={busy}
                onClick={() => choose(q.id, o.index)}
                aria-pressed={answers[q.id] === o.index}
                className={`w-full rounded-lg border px-4 py-3 text-left transition hover:bg-surface-2 disabled:opacity-50 ${
                  answers[q.id] === o.index ? "border-accent bg-accent-soft" : "border-border"
                }`}
              >
                {o.text}
              </button>
            </li>
          ))}
        </ul>
        <div className="flex items-center justify-between">
          <Button variant="ghost" disabled={step === 0 || busy} onClick={() => setStep(step - 1)}>
            Back
          </Button>
          {busy && <span className="text-sm text-muted" role="status">Finding your tutor…</span>}
        </div>
      </Card>
      <ErrorNote message={error} />
    </div>
  );
}
