"use client";

import { useState, type FormEvent } from "react";
import type { AnswerResult, QuizQuestion } from "@/lib/types";
import Markdown from "./Markdown";
import { Button, Card, ErrorNote } from "./ui";

function difficultyLabel(d: number) {
  if (d < 0.35) return "Gentle";
  if (d < 0.65) return "Steady";
  return "Stretch";
}

export default function QuizCard({
  question,
  index,
  total,
  result,
  busy,
  error,
  onSubmit,
  onNext,
  isLast,
}: {
  question: QuizQuestion;
  index: number;
  total: number;
  result: AnswerResult | null;
  busy: boolean;
  error: string | null;
  onSubmit: (answer: string) => void;
  onNext: () => void;
  isLast: boolean;
}) {
  const [numeric, setNumeric] = useState("");
  const [chosen, setChosen] = useState<number | null>(null);
  const answered = result !== null;

  function submitNumeric(e: FormEvent) {
    e.preventDefault();
    if (numeric.trim()) onSubmit(numeric.trim());
  }

  // Contract: MCQ answers are sent as the 0-based option index, as a string.
  function pickOption(index: number) {
    if (answered || busy) return;
    setChosen(index);
    onSubmit(String(index));
  }

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between text-sm text-muted">
        <span>
          Question {index + 1} of {total}
        </span>
        <span>{difficultyLabel(question.difficulty)}</span>
      </div>
      <div className="text-base" id={`q-${question.id}`}>
        <Markdown>{question.prompt}</Markdown>
      </div>

      {question.type === "mcq" && question.options ? (
        <ul className="space-y-2" aria-labelledby={`q-${question.id}`}>
          {question.options.map((opt, i) => {
            const isChosen = chosen === i;
            const tone = !answered
              ? "border-border hover:bg-surface-2"
              : isChosen && result.correct
                ? "border-ok"
                : isChosen
                  ? "border-danger"
                  : "border-border opacity-80";
            return (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => pickOption(i)}
                  disabled={answered || busy}
                  aria-pressed={isChosen}
                  className={`w-full rounded-lg border px-4 py-3 text-left transition disabled:cursor-default ${tone}`}
                >
                  <Markdown>{opt}</Markdown>
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <form onSubmit={submitNumeric} className="flex flex-wrap items-end gap-2">
          <div className="min-w-0 flex-1">
            <label htmlFor={`ans-${question.id}`} className="mb-1 block text-sm font-medium">
              Your answer
            </label>
            <input
              id={`ans-${question.id}`}
              value={numeric}
              onChange={(e) => setNumeric(e.target.value)}
              disabled={answered || busy}
              inputMode="decimal"
              autoComplete="off"
              placeholder="e.g. 12 or 3/4"
              className="w-full rounded-lg border border-border bg-bg px-3 py-2"
            />
          </div>
          <Button type="submit" disabled={answered || busy || !numeric.trim()}>
            Check
          </Button>
        </form>
      )}

      {busy && !answered && (
        <p className="text-sm text-muted" role="status">
          Checking…
        </p>
      )}
      <ErrorNote message={error} />

      {result && (
        <div role="status" className="space-y-2 rounded-lg bg-surface-2 p-3">
          <p className={`font-semibold ${result.correct ? "text-ok" : "text-fg"}`}>
            {result.correct ? "That's right." : "Not this time — here's how it works."}
          </p>
          {!result.correct && (
            <div className="text-sm">
              <span className="font-medium">Answer: </span>
              <Markdown>{result.correct_answer}</Markdown>
            </div>
          )}
          <div className="text-sm">
            <Markdown>{result.explanation}</Markdown>
          </div>
          <div className="pt-1">
            <Button onClick={onNext}>{isLast ? "See summary" : "Next question"}</Button>
          </div>
        </div>
      )}
    </Card>
  );
}
