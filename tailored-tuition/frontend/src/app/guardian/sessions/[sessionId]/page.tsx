"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatDate, pct } from "@/lib/format";
import type { SessionState } from "@/lib/types";
import MessageBubble from "@/components/MessageBubble";
import { Card, ErrorNote, Loading, errorMessage } from "@/components/ui";
import { useRequiredGuardian } from "@/components/AuthProvider";

function Transcript({ sessionId }: { sessionId: string }) {
  const child = useSearchParams().get("child");
  const guardian = useRequiredGuardian();
  const [session, setSession] = useState<SessionState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!guardian) return;
    api
      .getSession(sessionId)
      .then(setSession)
      .catch((e) => setError(errorMessage(e)));
  }, [guardian, sessionId]);

  if (!guardian) return <Loading />;
  const back = child ? `/guardian/children/${encodeURIComponent(child)}` : "/guardian";
  return (
    <div className="space-y-4">
      <Link href={back} className="text-sm text-accent underline">
        ← Back to progress
      </Link>
      {error ? (
        <ErrorNote message={error} />
      ) : !session ? (
        <Loading />
      ) : (
        <>
          <div>
            <h1 className="text-2xl font-semibold">{session.concept.name}</h1>
            <p className="text-sm text-muted">
              With {session.persona.name}
              {session.messages[0] ? ` · ${formatDate(session.messages[0].created_at)}` : ""} · mastery now{" "}
              {pct(session.mastery)} · {session.status === "ended" ? "ended" : "open"}. Read-only.
            </p>
          </div>
          <Card className="space-y-3">
            {session.messages.length === 0 ? (
              <p className="text-sm text-muted">No messages.</p>
            ) : (
              session.messages.map((m, i) => <MessageBubble key={i} message={m} tutorName={session.persona.name} />)
            )}
          </Card>
        </>
      )}
    </div>
  );
}

export default function GuardianSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  return (
    <Suspense fallback={<Loading />}>
      <Transcript sessionId={sessionId} />
    </Suspense>
  );
}
