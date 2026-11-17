"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { homeFor, useAuth } from "@/components/AuthProvider";
import { CheckboxField, DevLink, Notice, PasswordField, TextField } from "@/components/forms";
import { Button, Card, ErrorNote, Loading, errorMessage, isLimit } from "@/components/ui";

export default function SignupPage() {
  const { me, setMe } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [adult, setAdult] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ message: string; limit: boolean } | null>(null);
  const [devLink, setDevLink] = useState<string | null>(null);

  // Already logged in (and not just signed up here) → go home.
  useEffect(() => {
    if (me && !devLink && !busy) router.replace(homeFor(me));
  }, [me, devLink, busy, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (password.length < 10) {
      setError({ message: "Please use a password of at least 10 characters.", limit: false });
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.guardianSignup(name.trim(), email.trim(), password);
      setMe({ role: "guardian", guardian: res.guardian });
      if (res.dev_verification_url) setDevLink(res.dev_verification_url);
      else router.push("/guardian");
    } catch (err) {
      setError({ message: errorMessage(err), limit: isLimit(err) });
    } finally {
      setBusy(false);
    }
  }

  if (devLink) {
    return (
      <div className="mx-auto max-w-md space-y-4">
        <h1 className="text-2xl font-semibold">Check your email</h1>
        <Card className="space-y-3">
          <p className="text-sm">
            Your account is created. Verify your email address before adding your child.
          </p>
          <Notice tone="warn">
            Dev mode: no email is sent on this computer. Use this button instead of the email link.
          </Notice>
          <div className="flex flex-wrap gap-2">
            <DevLink href={devLink}>Dev mode: verify email now</DevLink>
            <Button variant="secondary" onClick={() => router.push("/guardian")}>
              Go to dashboard
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  if (me === undefined) return <Loading />;

  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-semibold">Create a parent or guardian account</h1>
      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          <TextField label="Your name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" required maxLength={80} />
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
            hint="We send a link to confirm it's yours."
          />
          <PasswordField
            label="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
            minLength={10}
            maxLength={128}
            hint="At least 10 characters. A short sentence works well."
          />
          <CheckboxField checked={adult} onChange={setAdult} required>
            I am 18 or older and the parent or legal guardian of the student(s) I will add. I have read the{" "}
            <Link href="/privacy" className="text-accent underline">
              privacy notice
            </Link>
            .
          </CheckboxField>
          <div aria-live="polite">
            <ErrorNote message={error?.message ?? null} limit={error?.limit} />
          </div>
          <Button type="submit" disabled={busy || !adult || !name.trim() || !email.trim()} className="w-full">
            {busy ? "Creating account…" : "Create account"}
          </Button>
        </form>
      </Card>
      <p className="text-sm text-muted">
        Already have an account?{" "}
        <Link href="/login" className="text-accent underline">
          Log in
        </Link>
      </p>
    </div>
  );
}
