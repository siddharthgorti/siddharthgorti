import { PHASE_LABEL } from "@/lib/format";
import type { Phase } from "@/lib/types";

/** Shows the planned session arc (warm-up → stretch → peak → end high) and where we are. */
export default function SessionFlow({
  plan,
  phase,
  problemsInPhase,
}: {
  plan: { phase: Phase; target_problems: number }[];
  phase: Phase;
  problemsInPhase: number;
}) {
  const found = plan.findIndex((p) => p.phase === phase);
  const currentIdx = phase === "complete" || found === -1 ? plan.length : found;
  return (
    <ol aria-label="Session flow" className="flex w-full gap-1">
      {plan.map((p, i) => {
        const done = i < currentIdx;
        const current = i === currentIdx;
        const fill = done
          ? 1
          : current
            ? Math.min(1, problemsInPhase / Math.max(1, p.target_problems))
            : 0;
        return (
          <li
            key={p.phase}
            aria-current={current ? "step" : undefined}
            className="min-w-0 basis-0"
            style={{ flexGrow: Math.max(1, p.target_problems) }}
          >
            <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
              <div
                className="h-full rounded-full bg-accent transition-[width]"
                style={{ width: `${fill * 100}%` }}
              />
            </div>
            <p
              className={`mt-1 truncate text-[11px] sm:text-xs ${
                current ? "font-semibold text-fg" : done ? "text-fg" : "text-muted"
              }`}
            >
              {PHASE_LABEL[p.phase]}
              {current && (
                <span className="sr-only">
                  {" "}
                  (current, {problemsInPhase} of {p.target_problems} problems)
                </span>
              )}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
