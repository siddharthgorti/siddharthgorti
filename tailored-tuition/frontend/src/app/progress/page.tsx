"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatDate, pct } from "@/lib/format";
import type { MasteryMap as MasteryMapData, MasteryStatus, SessionSummary } from "@/lib/types";
import MasteryMap, { STATUS_COLOR, STATUS_LABEL } from "@/components/MasteryMap";
import { Card, ErrorNote, Loading, Meter, errorMessage } from "@/components/ui";
import { useRequiredStudent } from "@/components/StudentProvider";

const STATUSES: MasteryStatus[] = ["mastered", "learning", "started", "not_started"];

export default function ProgressPage() {
  const student = useRequiredStudent();
  const [map, setMap] = useState<MasteryMapData | null>(null);
  const [history, setHistory] = useState<SessionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!student) return;
    Promise.all([api.masteryMap(student.id), api.sessionHistory(student.id)])
      .then(([m, h]) => {
        setMap(m);
        setHistory(h);
      })
      .catch((e) => setError(errorMessage(e)));
  }, [student]);

  if (error) return <ErrorNote message={error} />;
  if (!student || !map || !history) return <Loading />;

  const s = map.summary;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Your map of ideas</h1>
        <p className="text-sm text-muted">
          Each box is a topic; arrows show what builds on what. Tap a topic to work on it.
        </p>
      </div>

      <Card className="space-y-3">
        <div className="flex items-baseline justify-between text-sm">
          <span className="font-medium">Overall understanding</span>
          <span>{pct(s.overall_progress)}</span>
        </div>
        <Meter value={s.overall_progress} label="Overall understanding" />
        <ul className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          {STATUSES.map((st) => (
            <li key={st} className="flex items-center gap-2">
              <span aria-hidden className="h-3 w-3 shrink-0 rounded-sm" style={{ background: STATUS_COLOR[st] }} />
              <span>
                {STATUS_LABEL[st]}: <strong>{s[st]}</strong>
              </span>
            </li>
          ))}
        </ul>
        <p className="text-xs text-muted">{s.total_concepts} topics in total.</p>
      </Card>

      <MasteryMap data={map} />

      <section aria-labelledby="history-heading" className="space-y-2">
        <h2 id="history-heading" className="text-lg font-semibold">
          Past sessions
        </h2>
        {history.length === 0 ? (
          <p className="text-sm text-muted">
            No sessions yet. <Link href="/learn" className="text-accent underline">Start one</Link> whenever you like.
          </p>
        ) : (
          <ul className="divide-y divide-border rounded-xl border border-border bg-surface">
            {history.map((h) => {
              const delta = h.mastery_end - h.mastery_start;
              return (
                <li key={h.session_id}>
                  <Link href={`/chat/${h.session_id}`} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3 hover:bg-surface-2">
                    <span className="font-medium">{h.concept.name}</span>
                    <span className="text-sm text-muted">
                      {formatDate(h.started_at)} · {h.turns} {h.turns === 1 ? "turn" : "turns"} · {pct(h.mastery_start)} → {pct(h.mastery_end)}
                      {delta > 0.005 ? " ↑" : ""}
                      {h.ended_at ? "" : " · open"}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
