import type { Phase } from "./types";

export const pct = (x: number) => `${Math.round(Math.max(0, Math.min(1, x)) * 100)}%`;

export const PHASE_LABEL: Record<Phase, string> = {
  warmup: "Warm-up",
  stretch: "Stretch",
  peak: "Peak",
  end_high: "End high",
  complete: "Done",
};

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
