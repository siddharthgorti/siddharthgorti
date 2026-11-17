import type { ButtonHTMLAttributes, ReactNode } from "react";
import { ApiError } from "@/lib/api";

type Variant = "primary" | "secondary" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-accent-fg hover:opacity-90",
  secondary: "border border-border bg-surface text-fg hover:bg-surface-2",
  ghost: "text-accent hover:bg-accent-soft",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...props}
      className={`inline-flex min-h-10 items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
    />
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-border bg-surface p-4 sm:p-5 ${className}`}>
      {children}
    </div>
  );
}

/**
 * An error for the user. Usage limits (HTTP 429) are not failures, so they get a calm,
 * neutral style; everything else uses the danger colour.
 */
export function ErrorNote({ message, limit = false }: { message: string | null; limit?: boolean }) {
  if (!message) return null;
  return limit ? (
    <p role="alert" className="rounded-lg bg-warn-soft px-3 py-2 text-sm text-warn-fg">
      {message}
    </p>
  ) : (
    <p role="alert" className="rounded-lg border border-danger/40 px-3 py-2 text-sm text-danger">
      {message}
    </p>
  );
}

/** True for usage-limit / lockout responses (HTTP 429). */
export const isLimit = (e: unknown) => e instanceof ApiError && e.status === 429;

export function Meter({ value, label }: { value: number; label: string }) {
  const v = Math.max(0, Math.min(1, value));
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(v * 100)}
      className="h-2 w-full overflow-hidden rounded-full bg-surface-2"
    >
      <div className="h-full rounded-full bg-accent transition-[width]" style={{ width: `${v * 100}%` }} />
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <p className="py-8 text-center text-sm text-muted" role="status">
      {label}
    </p>
  );
}

export const errorMessage = (e: unknown) =>
  e instanceof Error ? e.message : "Something went wrong. Please try again.";
