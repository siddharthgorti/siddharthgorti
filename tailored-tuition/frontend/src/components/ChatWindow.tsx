"use client";

import Link from "next/link";
import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { api } from "@/lib/api";
import { pct } from "@/lib/format";
import type { ChatMessage, SessionAdvice, SessionState, Source } from "@/lib/types";
import Markdown from "./Markdown";
import MessageBubble from "./MessageBubble";
import PersonaCard from "./PersonaCard";
import SessionFlow from "./SessionFlow";
import { Button, Card, ErrorNote, Meter, errorMessage, isLimit } from "./ui";

const ADVICE_COPY: Record<Exclude<SessionAdvice, "continue">, string> = {
  gentle_check: "Want to keep going or save this for next time?",
  suggest_stop: "You've worked hard — this is a great place to stop.",
};

export default function ChatWindow({ initial }: { initial: SessionState }) {
  const [session, setSession] = useState(initial);
  const [messages, setMessages] = useState<ChatMessage[]>(initial.messages);
  // Sources are returned per turn; keyed by message index (not persisted across reloads).
  const [sources, setSources] = useState<Record<number, Source[]>>({});
  const [draft, setDraft] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [advice, setAdvice] = useState<SessionAdvice>("continue");
  const [teaser, setTeaser] = useState<string | null>(null);
  const [ended, setEnded] = useState(initial.status === "ended");
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limited, setLimited] = useState(false);

  const lastTutorAt = useRef<number | null>(null);
  const hiddenSinceTutor = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Latency = time from the tutor's message appearing to the student pressing send.
  // If the tab was hidden in between, the number says nothing about the student, so send null.
  const lastMessage = messages[messages.length - 1];
  useLayoutEffect(() => {
    if (lastMessage?.role === "tutor") {
      lastTutorAt.current = performance.now();
      hiddenSinceTutor.current = document.visibilityState === "hidden";
    }
  }, [lastMessage]);

  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState === "hidden") hiddenSinceTutor.current = true;
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, waiting, teaser]);

  async function send(e?: FormEvent) {
    e?.preventDefault();
    const content = draft.trim();
    if (!content || waiting || ended) return;

    const latency =
      lastTutorAt.current !== null && !hiddenSinceTutor.current
        ? Math.round(((performance.now() - lastTutorAt.current) / 1000) * 10) / 10
        : null;

    const studentMsg: ChatMessage = {
      role: "student",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, studentMsg]);
    setDraft("");
    setWaiting(true);
    setError(null);
    setLimited(false);
    try {
      const res = await api.sendMessage(session.session_id, content, latency);
      // `messages` is the pre-send list: the student's message sits at messages.length,
      // so the reply lands at messages.length + 1.
      const replyIndex = messages.length + 1;
      setMessages((m) => [...m, res.reply]);
      setSources((s) => ({ ...s, [replyIndex]: res.sources }));
      setSession((s) => ({
        ...s,
        phase: res.phase,
        problems_in_phase: res.problems_in_phase,
        mastery: res.mastery,
      }));
      setAdvice(res.advice);
      if (res.teaser) setTeaser(res.teaser);
    } catch (err) {
      // Roll back the optimistic message so the student can retry without retyping.
      setMessages((m) => m.slice(0, -1));
      setDraft(content);
      setError(errorMessage(err));
      setLimited(isLimit(err));
    } finally {
      setWaiting(false);
      inputRef.current?.focus();
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void send();
    }
  }

  async function endSession() {
    setEnding(true);
    setError(null);
    try {
      const res = await api.endSession(session.session_id);
      setTeaser(res.teaser);
      setSession((s) => ({ ...s, mastery: res.mastery, status: "ended" }));
      setEnded(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setEnding(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100dvh-7rem)] flex-col gap-4">
      <Card className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <PersonaCard persona={session.persona} compact />
          {!ended && (
            <Button variant="secondary" onClick={endSession} disabled={ending || waiting}>
              {ending ? "Ending…" : "End session"}
            </Button>
          )}
        </div>
        <div>
          <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
            <span className="truncate font-medium">{session.concept.name}</span>
            <span className="shrink-0 text-muted">Mastery {pct(session.mastery)}</span>
          </div>
          <Meter value={session.mastery} label={`${session.concept.name} mastery`} />
        </div>
        <SessionFlow
          plan={session.phase_plan}
          phase={session.phase}
          problemsInPhase={session.problems_in_phase}
        />
      </Card>

      <div
        className="flex-1 space-y-3"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Conversation"
      >
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} sources={sources[i]} tutorName={session.persona.name} />
        ))}
        {waiting && (
          <div className="flex justify-start" role="status" aria-label={`${session.persona.name} is typing`}>
            <div className="flex gap-1 rounded-2xl rounded-bl-sm border border-border bg-surface px-4 py-3">
              <span className="tt-dot h-2 w-2 rounded-full bg-muted" />
              <span className="tt-dot h-2 w-2 rounded-full bg-muted" />
              <span className="tt-dot h-2 w-2 rounded-full bg-muted" />
            </div>
          </div>
        )}
      </div>

      {teaser && (
        <Card className="space-y-2 border-accent">
          <p className="text-xs font-medium uppercase tracking-wide text-accent">Next time</p>
          <Markdown>{teaser}</Markdown>
          {ended && (
            <div className="flex flex-wrap gap-2 pt-1">
              <Link href="/learn" className="inline-flex min-h-10 items-center rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-fg">
                Back to topics
              </Link>
              <Link href="/progress" className="inline-flex min-h-10 items-center rounded-lg border border-border px-4 py-2 text-sm font-medium">
                See progress
              </Link>
            </div>
          )}
        </Card>
      )}

      {!ended && advice !== "continue" && (
        <div role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-warn-soft px-4 py-3 text-sm text-warn-fg">
          <span>{ADVICE_COPY[advice]}</span>
          <div className="flex gap-2">
            {advice === "gentle_check" && (
              <Button variant="ghost" onClick={() => setAdvice("continue")}>
                Keep going
              </Button>
            )}
            <Button onClick={endSession} disabled={ending || waiting}>
              End session
            </Button>
          </div>
        </div>
      )}

      <ErrorNote message={error} limit={limited} />

      {ended ? (
        !teaser && <p className="text-center text-sm text-muted">This session has ended.</p>
      ) : (
        <form onSubmit={send} className="sticky bottom-0 -mx-4 border-t border-border bg-bg px-4 py-3">
          <label htmlFor="chat-input" className="sr-only">
            Your reply
          </label>
          <div className="flex items-end gap-2">
            <textarea
              id="chat-input"
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKeyDown}
              rows={2}
              maxLength={4000}
              placeholder="Type your thinking — partial ideas are welcome"
              className="min-h-12 flex-1 resize-y rounded-lg border border-border bg-surface px-3 py-2"
            />
            <Button type="submit" disabled={waiting || !draft.trim()}>
              Send
            </Button>
          </div>
          <p className="mt-1 hidden text-xs text-muted sm:block">Enter to send · Shift+Enter for a new line</p>
        </form>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
