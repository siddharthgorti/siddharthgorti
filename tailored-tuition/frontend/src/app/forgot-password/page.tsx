"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { DevLink, Notice, TextField } from "@/components/forms";
import { Button, Card, ErrorNote, errorMessage, isLimit } from "@/components/ui";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; limit: boolean } | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.forgotPassword(email.trim());
      setDevLink(res.dev_reset_url);
      setSent(true);
    } catch (err) {
      setError({ message: errorMessage(err), limit: isLimit(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-semibold">Reset your password</h1>
      <Card className="space-y-4">
        {sent ? (
          <>
            <Notice tone="ok">
              If an account exists for that email, we&apos;ve sent a link to reset the password. It expires soon and
              works once.
            </Notice>
            {devLink && (
              <>
                <Notice tone="warn">Dev mode: no email is sent on this computer.</Notice>
                <DevLink href={devLink}>Dev mode: open reset link</DevLink>
              </>
            )}
          </>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <p className="text-sm text-muted">For parent and guardian accounts. Students: ask your parent or guardian.</p>
            <TextField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
            <div aria-live="polite">
              <ErrorNote message={error?.message ?? null} limit={error?.limit} />
            </div>
            <Button type="submit" disabled={busy || !email.trim()} className="w-full">
              {busy ? "Sending…" : "Send reset link"}
            </Button>
          </form>
        )}
      </Card>
      <Link href="/login" className="text-sm text-accent underline">
        Back to log in
      </Link>
    </div>
  );
}
