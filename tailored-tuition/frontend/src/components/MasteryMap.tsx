"use client";

import { useRouter } from "next/navigation";
import { useMemo, type KeyboardEvent } from "react";
import type { MasteryMap as MasteryMapData, MasteryStatus } from "@/lib/types";

const NODE_W = 150;
const NODE_H = 52;
const GAP_X = 20;
const GAP_Y = 56;
const PAD = 12;

export const STATUS_COLOR: Record<MasteryStatus, string> = {
  mastered: "var(--status-mastered)",
  learning: "var(--status-learning)",
  started: "var(--status-started)",
  not_started: "var(--status-none)",
};

export const STATUS_LABEL: Record<MasteryStatus, string> = {
  mastered: "Mastered",
  learning: "Learning",
  started: "Started",
  not_started: "Not started",
};

/** Depth of each concept = length of its longest prerequisite chain (cycle-safe). */
function computeDepths(ids: string[], prereqs: Map<string, string[]>): Map<string, number> {
  const depth = new Map<string, number>();
  const visiting = new Set<string>();
  const visit = (id: string): number => {
    const known = depth.get(id);
    if (known !== undefined) return known;
    if (visiting.has(id)) return 0; // break cycles defensively
    visiting.add(id);
    let d = 0;
    for (const p of prereqs.get(id) ?? []) {
      if (prereqs.has(p)) d = Math.max(d, visit(p) + 1);
    }
    visiting.delete(id);
    depth.set(id, d);
    return d;
  };
  ids.forEach(visit);
  return depth;
}

function truncate(s: string, n: number) {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

/** `interactive`: nodes link to the Learn page (students). Off for guardians viewing a child. */
export default function MasteryMap({ data, interactive = true }: { data: MasteryMapData; interactive?: boolean }) {
  const router = useRouter();

  const layout = useMemo(() => {
    const prereqs = new Map<string, string[]>(data.concepts.map((c) => [c.id, []]));
    for (const e of data.connections) prereqs.get(e.to)?.push(e.from);
    const depths = computeDepths(
      data.concepts.map((c) => c.id),
      prereqs,
    );

    const rows: (typeof data.concepts)[] = [];
    for (const c of data.concepts) {
      const d = depths.get(c.id) ?? 0;
      (rows[d] ??= []).push(c);
    }
    rows.forEach((r) => r?.sort((a, b) => a.chapter - b.chapter || a.name.localeCompare(b.name)));

    const maxCols = Math.max(1, ...rows.map((r) => r?.length ?? 0));
    const width = PAD * 2 + maxCols * NODE_W + (maxCols - 1) * GAP_X;
    const pos = new Map<string, { x: number; y: number }>();
    rows.forEach((row, ri) => {
      if (!row) return;
      const rowW = row.length * NODE_W + (row.length - 1) * GAP_X;
      const x0 = (width - rowW) / 2;
      row.forEach((c, ci) => pos.set(c.id, { x: x0 + ci * (NODE_W + GAP_X), y: PAD + ri * (NODE_H + GAP_Y) }));
    });
    const height = PAD * 2 + rows.length * NODE_H + Math.max(0, rows.length - 1) * GAP_Y;
    return { pos, width, height };
  }, [data]);

  const go = (id: string) => router.push(`/learn#concept-${id}`);

  if (data.concepts.length === 0) return <p className="text-sm text-muted">No topics yet.</p>;

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <svg
        width={layout.width}
        height={layout.height}
        viewBox={`0 0 ${layout.width} ${layout.height}`}
        role="group"
        aria-label="Map of topics and how they build on each other"
        className="mx-auto block"
      >
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--border)" />
          </marker>
        </defs>
        <g aria-hidden>
          {data.connections.map((e) => {
            const a = layout.pos.get(e.from);
            const b = layout.pos.get(e.to);
            if (!a || !b) return null;
            const x1 = a.x + NODE_W / 2;
            const y1 = a.y + NODE_H;
            const x2 = b.x + NODE_W / 2;
            const y2 = b.y;
            const my = (y1 + y2) / 2;
            return (
              <path
                key={`${e.from}-${e.to}`}
                d={`M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2 - 2}`}
                fill="none"
                stroke="var(--border)"
                strokeWidth={1.5}
                markerEnd="url(#arrow)"
              />
            );
          })}
        </g>
        {data.concepts.map((c) => {
          const p = layout.pos.get(c.id);
          if (!p) return null;
          const color = STATUS_COLOR[c.status];
          const pctText = `${Math.round(c.mastery * 100)}%`;
          return (
            <g
              key={c.id}
              transform={`translate(${p.x} ${p.y})`}
              {...(interactive
                ? {
                    role: "link",
                    tabIndex: 0,
                    "aria-label": `${c.name}, ${STATUS_LABEL[c.status]}, ${pctText} mastery. Open in Learn.`,
                    onClick: () => go(c.id),
                    onKeyDown: (e: KeyboardEvent<SVGGElement>) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        go(c.id);
                      }
                    },
                    className: "cursor-pointer outline-none [&:focus-visible>rect]:stroke-[3]",
                  }
                : { role: "img", "aria-label": `${c.name}, ${STATUS_LABEL[c.status]}, ${pctText} mastery.` })}
            >
              <title>{c.name}</title>
              <rect width={NODE_W} height={NODE_H} rx={10} fill="var(--surface)" stroke={color} strokeWidth={2} />
              {/* mastery fill along the bottom edge */}
              <rect x={6} y={NODE_H - 8} width={NODE_W - 12} height={3} rx={1.5} fill="var(--surface-2)" />
              <rect x={6} y={NODE_H - 8} width={(NODE_W - 12) * c.mastery} height={3} rx={1.5} fill={color} />
              <text x={10} y={20} fontSize={13} fontWeight={600} fill="var(--fg)">
                {truncate(c.name, 19)}
              </text>
              <text x={10} y={36} fontSize={11} fill="var(--muted)">
                Ch {c.chapter} · {pctText}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
