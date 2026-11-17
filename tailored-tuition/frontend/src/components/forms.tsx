"use client";

import { useId, useState, type InputHTMLAttributes, type ReactNode } from "react";

const INPUT = "w-full rounded-lg border border-border bg-bg px-3 py-2";

export function TextField({
  label,
  hint,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: ReactNode }) {
  const id = useId();
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <input id={id} aria-describedby={hint ? `${id}-hint` : undefined} className={INPUT} {...props} />
      {hint && (
        <p id={`${id}-hint`} className="text-xs text-muted">
          {hint}
        </p>
      )}
    </div>
  );
}

/** Password input with a show/hide toggle. */
export function PasswordField({
  label,
  hint,
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { label: string; hint?: ReactNode }) {
  const id = useId();
  const [shown, setShown] = useState(false);
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <div className="flex gap-2">
        <input
          id={id}
          type={shown ? "text" : "password"}
          aria-describedby={hint ? `${id}-hint` : undefined}
          className={`${INPUT} min-w-0 flex-1`}
          {...props}
        />
        <button
          type="button"
          onClick={() => setShown((s) => !s)}
          aria-pressed={shown}
          aria-controls={id}
          className="shrink-0 rounded-lg border border-border px-3 text-sm hover:bg-surface-2"
        >
          {shown ? "Hide" : "Show"}
        </button>
      </div>
      {hint && (
        <p id={`${id}-hint`} className="text-xs text-muted">
          {hint}
        </p>
      )}
    </div>
  );
}

export function CheckboxField({
  checked,
  onChange,
  children,
  required,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  children: ReactNode;
  required?: boolean;
}) {
  return (
    <label className="flex items-start gap-3 rounded-lg bg-surface-2 p-3 text-sm">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        required={required}
        className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--accent)]"
      />
      <span>{children}</span>
    </label>
  );
}

/** Success / info note announced to screen readers. */
export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "ok" | "warn" }) {
  const cls =
    tone === "warn"
      ? "border-transparent bg-warn-soft text-warn-fg"
      : tone === "ok"
        ? "border-ok/40 text-ok"
        : "border-border bg-surface-2";
  return (
    <div role="status" className={`rounded-lg border px-3 py-2 text-sm ${cls}`}>
      {children}
    </div>
  );
}

/** Clearly labelled dev-only link (backend returns these only in local development). */
export function DevLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      className="inline-flex min-h-10 items-center rounded-lg border border-dashed border-warn-fg px-4 py-2 text-sm font-medium text-warn-fg hover:bg-warn-soft"
    >
      {children}
    </a>
  );
}
