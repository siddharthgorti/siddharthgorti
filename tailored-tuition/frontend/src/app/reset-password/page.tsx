"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { PasswordField } from "@/components/forms";
import { Button, Card, ErrorNote, Loading, errorMessage, isLimit } from "@/components/ui";

function Reset() {
  const token = useSearchParams().get("token");
  const { setMe } = useAuth();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; limit: boolean } | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    if (password.length < 10) return setError({ message: "Please use at least 10 characters.", limit: false });
    if (password !== confirm) return setError({ message: "The two passwords don't match.", limit: false });
    setBusy(true);
    setError(null);
    try {
      const res = await api.resetPassword(token, password);
      setMe({ role: "guardian", guardian: res.guardian });
      router.replace("/guardian");
    } catch (err) {
      setError({ message: errorMessage(err), limit: isLimit(err) });
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-semibold">Choose a new password</h1>
      <Card>
        {!token ? (
          <ErrorNote message="This link is missing its code. Request a new reset link." />
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <PasswordField label="New password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" required minLength={10} maxLength={128} hint="At least 10 characters. You'll be logged out on other devices." />
            <PasswordField label="Repeat new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" required />
            <div aria-live="polite">
              <ErrorNote message={error?.message ?? null} limit={error?.limit} />
            </div>
            <Button type="submit" disabled={busy || !password || !confirm} className="w-full">
              {busy ? "Saving…" : "Save new password"}
            </Button>
          </form>
        )}
      </Card>
      <Link href="/forgot-password" className="text-sm text-accent underline">
        Request a new link
      </Link>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Reset />
    </Suspense>
  );
}
