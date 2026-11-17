"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { pct } from "@/lib/format";
import type { Concept, MasteryMap } from "@/lib/types";
import { Button, Card, ErrorNote, Loading, Meter, errorMessage, isLimit } from "@/components/ui";
import { useRequiredStudent } from "@/components/AuthProvider";

export default function LearnPage() {
  const student = useRequiredStudent();
  const router = useRouter();
  const [concepts, setConcepts] = useState<Concept[] | null>(null);
  const [map, setMap] = useState<MasteryMap | null>(null);
  const [starting, setStarting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [limited, setLimited] = useState(false);

  useEffect(() => {
    if (!student) return;
    Promise.all([api.concepts(), api.masteryMap(student.id)])
      .then(([c, m]) => {
        setConcepts(c);
        setMap(m);
      })
      .catch((e) => setError(errorMessage(e)));
  }, [student]);

  // Arriving from the mastery map (/learn#concept-x): scroll once the cards exist.
  useEffect(() => {
    if (!concepts) return;
    const id = window.location.hash.slice(1);
    if (id) document.getElementById(id)?.scrollIntoView({ block: "center" });
  }, [concepts]);

  const mastery = useMemo(
    () => new Map(map?.concepts.map((c) => [c.id, c.mastery]) ?? []),
    [map],
  );

  const chapters = useMemo(() => {
    const groups = new Map<number, Concept[]>();
    for (const c of concepts ?? []) {
      const list = groups.get(c.chapter) ?? [];
      list.push(c);
      groups.set(c.chapter, list);
    }
    return [...groups.entries()].sort((a, b) => a[0] - b[0]);
  }, [concepts]);

  const names = useMemo(
    () => new Map((concepts ?? []).map((c) => [c.id, c.name])),
    [concepts],
  );

  async function startSession(conceptId: string) {
    if (!student) return;
    setStarting(conceptId);
    setError(null);
    setLimited(false);
    try {
      const s = await api.createSession(conceptId);
      router.push(`/chat/${s.session_id}`);
    } catch (e) {
      setError(errorMessage(e));
      setLimited(isLimit(e));
      setStarting(null);
    }
  }

  if (!student) return <Loading />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">What would you like to work on?</h1>
        <p className="text-sm text-muted">
          Pick any topic. Topics build on each other, so the ones listed under “builds on” are good
          places to start if something feels shaky.
        </p>
      </div>
      <ErrorNote message={error} limit={limited} />
      {!concepts ? (
        !error && <Loading />
      ) : (
        chapters.map(([chapter, list]) => (
          <section key={chapter} aria-labelledby={`ch-${chapter}`} className="space-y-2">
            <h2 id={`ch-${chapter}`} className="text-sm font-medium uppercase tracking-wide text-muted">
              Chapter {chapter}
            </h2>
            <ul className="grid gap-3 sm:grid-cols-2">
              {list.map((c) => {
                const m = mastery.get(c.id) ?? 0;
                return (
                  <li key={c.id} id={`concept-${c.id}`}>
                    <Card className="flex h-full flex-col gap-3">
                      <div className="flex items-baseline justify-between gap-2">
                        <h3 className="font-semibold">{c.name}</h3>
                        <span className="shrink-0 text-sm text-muted">{pct(m)}</span>
                      </div>
                      <Meter value={m} label={`${c.name} mastery`} />
                      {c.prerequisites.length > 0 && (
                        <p className="text-xs text-muted">
                          Builds on: {c.prerequisites.map((p) => names.get(p) ?? p).join(", ")}
                        </p>
                      )}
                      <div className="mt-auto flex flex-wrap gap-2">
                        <Button
                          onClick={() => startSession(c.id)}
                          disabled={starting !== null}
                          aria-label={`Start a tutor session on ${c.name}`}
                        >
                          {starting === c.id ? "Starting…" : "Tutor session"}
                        </Button>
                        <Link
                          href={`/quiz?concept=${encodeURIComponent(c.id)}`}
                          aria-label={`Take a quick quiz on ${c.name}`}
                          className="inline-flex min-h-10 items-center rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-surface-2"
                        >
                          Quick quiz
                        </Link>
                      </div>
                    </Card>
                  </li>
                );
              })}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}
