"use client";

import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SessionState } from "@/lib/types";
import ChatWindow from "@/components/ChatWindow";
import { ErrorNote, Loading, errorMessage } from "@/components/ui";
import { useRequiredStudent } from "@/components/AuthProvider";

export default function ChatPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const student = useRequiredStudent();
  const [session, setSession] = useState<SessionState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!student) return;
    api
      .getSession(sessionId)
      .then((s) => {
        if (s.student_id !== student.id) setError("This session belongs to a different student.");
        else setSession(s);
      })
      .catch((e) => setError(errorMessage(e)));
  }, [sessionId, student]);

  if (error) return <ErrorNote message={error} />;
  if (!student || !session) return <Loading label="Opening your session…" />;
  return <ChatWindow initial={session} />;
}
