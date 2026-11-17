"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { pct } from "@/lib/format";
import type { AnswerResult, Quiz } from "@/lib/types";
import QuizCard from "@/components/QuizCard";
import { Card, ErrorNote, Loading, Meter, errorMessage, isLimit } from "@/components/ui";
import { useRequiredStudent } from "@/components/AuthProvider";

function QuizFlow() {
  const conceptId = useSearchParams().get("concept");
  const student = useRequiredStudent();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [index, setIndex] = useState(0);
  const [results, setResults] = useState<Record<string, AnswerResult>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limited, setLimited] = useState(false);
  const [answerError, setAnswerError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const requested = useRef(false);

  useEffect(() => {
    // Guard against React strict-mode double effects generating two quizzes.
    if (!student || !conceptId || requested.current) return;
    requested.current = true;
    api
      .createQuiz(conceptId)
      .then(setQuiz)
      .catch((e) => {
        setError(errorMessage(e));
        setLimited(isLimit(e));
      });
  }, [student, conceptId]);

  if (!conceptId) {
    return (
      <p className="text-sm">
        No topic chosen. <Link href="/learn" className="text-accent underline">Pick one on the Learn page.</Link>
      </p>
    );
  }
  if (error)
    return (
      <div className="space-y-3">
        <ErrorNote message={error} limit={limited} />
        <Link href="/learn" className="text-sm text-accent underline">
          Back to topics
        </Link>
      </div>
    );
  if (!student || !quiz) return <Loading label="Preparing questions at your level…" />;

  const question = quiz.questions[index];
  const answeredCount = Object.keys(results).length;
  const correctCount = Object.values(results).filter((r) => r.correct).length;
  const latest = Object.values(results).at(-1);

  async function submit(answer: string) {
    if (!quiz) return;
    setBusy(true);
    setAnswerError(null);
    try {
      const r = await api.answerQuiz(quiz.quiz_id, question.id, answer);
      setResults((prev) => ({ ...prev, [question.id]: r }));
    } catch (e) {
      setAnswerError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  function next() {
    setAnswerError(null);
    if (index < quiz!.questions.length - 1) setIndex(index + 1);
    else setDone(true);
  }

  if (done) {
    const missed = quiz.questions.filter((q) => results[q.id] && !results[q.id].correct).length;
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">{quiz.concept.name}: how it went</h1>
        <Card className="space-y-3">
          <p>
            You worked through {answeredCount} {answeredCount === 1 ? "question" : "questions"} and got{" "}
            {correctCount} right.
            {missed > 0
              ? " The ones you missed show exactly what to look at next — that is useful, not a setback."
              : " Solid understanding of this topic."}
          </p>
          {latest && (
            <div>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-muted">Mastery of {quiz.concept.name}</span>
                <span>{pct(latest.mastery_after)}</span>
              </div>
              <Meter value={latest.mastery_after} label={`${quiz.concept.name} mastery`} />
            </div>
          )}
          <div className="flex flex-wrap gap-2 pt-1">
            <Link href="/learn" className="inline-flex min-h-10 items-center rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-fg">
              Back to topics
            </Link>
            <Link href="/progress" className="inline-flex min-h-10 items-center rounded-lg border border-border px-4 py-2 text-sm font-medium">
              See progress
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Quick quiz: {quiz.concept.name}</h1>
      <QuizCard
        key={question.id}
        question={question}
        index={index}
        total={quiz.questions.length}
        result={results[question.id] ?? null}
        busy={busy}
        error={answerError}
        onSubmit={submit}
        onNext={next}
        isLast={index === quiz.questions.length - 1}
      />
    </div>
  );
}

export default function QuizPage() {
  return (
    <Suspense fallback={<Loading />}>
      <QuizFlow />
    </Suspense>
  );
}
