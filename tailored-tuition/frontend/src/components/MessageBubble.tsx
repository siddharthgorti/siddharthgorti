import type { ChatMessage, Source } from "@/lib/types";
import Markdown from "./Markdown";

export default function MessageBubble({
  message,
  sources,
  tutorName,
}: {
  message: ChatMessage;
  sources?: Source[];
  tutorName: string;
}) {
  const isTutor = message.role === "tutor";
  return (
    <div className={`flex ${isTutor ? "justify-start" : "justify-end"}`}>
      <div
        className={`min-w-0 max-w-[92%] rounded-2xl px-4 py-2.5 sm:max-w-[80%] ${
          isTutor ? "rounded-bl-sm border border-border bg-surface" : "rounded-br-sm bg-accent-soft"
        }`}
      >
        <p className="sr-only">{isTutor ? `${tutorName} said:` : "You said:"}</p>
        <Markdown>{message.content}</Markdown>
        {isTutor && sources && sources.length > 0 && (
          <details className="mt-2 border-t border-border pt-2 text-xs text-muted">
            <summary className="cursor-pointer select-none">
              Based on {sources.length} syllabus {sources.length === 1 ? "passage" : "passages"}
            </summary>
            <ul className="mt-2 space-y-2">
              {sources.map((s, i) => (
                <li key={i}>
                  <p className="font-medium text-fg">
                    {s.document} — {s.section}
                  </p>
                  <p className="line-clamp-4">{s.snippet}</p>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}
