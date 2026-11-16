import type { Persona } from "@/lib/types";

const INITIAL: Record<Persona["id"], string> = {
  coach: "Co",
  challenger: "Ch",
  explainer: "Ex",
  mentor: "Me",
};

export default function PersonaCard({
  persona,
  compact = false,
}: {
  persona: Persona;
  compact?: boolean;
}) {
  return (
    <div className="flex items-start gap-3">
      <div
        aria-hidden
        className={`flex shrink-0 items-center justify-center rounded-full bg-accent-soft font-semibold text-accent ${
          compact ? "h-9 w-9 text-sm" : "h-12 w-12"
        }`}
      >
        {INITIAL[persona.id]}
      </div>
      <div className="min-w-0">
        <p className={`font-semibold ${compact ? "text-sm" : "text-lg"}`}>{persona.name}</p>
        <p className="text-sm text-muted">{persona.tagline}</p>
        {!compact && <p className="mt-2 text-sm">{persona.description}</p>}
      </div>
    </div>
  );
}
