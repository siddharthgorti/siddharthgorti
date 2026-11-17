"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { formatDate, pct } from "@/lib/format";
import type { ChildSummary, Guardian, PrivacyPolicy } from "@/lib/types";
import { useAuth, useRequiredGuardian } from "@/components/AuthProvider";
import { CheckboxField, DevLink, Notice, PasswordField, TextField } from "@/components/forms";
import SyllabusPanel from "@/components/SyllabusPanel";
import { Button, Card, ErrorNote, Loading, Meter, errorMessage, isLimit } from "@/components/ui";

type Err = { message: string; limit: boolean } | null;
const toErr = (e: unknown): Err => ({ message: errorMessage(e), limit: isLimit(e) });

function VerifyBanner() {
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState<string | null>(null);
  const [error, setError] = useState<Err>(null);

  async function resend() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.resendVerification();
      setDevLink(res.dev_verification_url);
      setSent(true);
    } catch (e) {
      setError(toErr(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2 rounded-xl bg-warn-soft p-4 text-warn-fg" role="region" aria-label="Email not verified">
      <p className="text-sm">
        <strong>Please verify your email.</strong> We sent you a link. You can add your child once your email is
        confirmed — this helps make sure only a real parent or guardian creates a child&apos;s account.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={resend} disabled={busy}>
          {busy ? "Sending…" : sent ? "Send again" : "Resend verification"}
        </Button>
        {devLink && <DevLink href={devLink}>Dev mode: verify email now</DevLink>}
      </div>
      {sent && !devLink && <p className="text-sm">Sent. Check your inbox (and spam folder).</p>}
      <ErrorNote message={error?.message ?? null} limit={error?.limit} />
    </div>
  );
}

function AddChild({ guardian, onAdded }: { guardian: Guardian; onAdded: () => void }) {
  const [policy, setPolicy] = useState<PrivacyPolicy | null>(null);
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Err>(null);
  const [added, setAdded] = useState<string | null>(null);

  useEffect(() => {
    api.privacyPolicy().then(setPolicy).catch((e) => setError(toErr(e)));
  }, []);

  const usernameOk = /^[a-z0-9._-]{3,30}$/.test(username);
  const disabled = !guardian.email_verified;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!policy) return;
    if (!usernameOk) return setError({ message: "Usernames are 3–30 characters: letters, numbers, . _ or -", limit: false });
    if (password.length < 8) return setError({ message: "The password needs at least 8 characters.", limit: false });
    setBusy(true);
    setError(null);
    try {
      const s = await api.addChild(name.trim(), username, password, policy.version);
      setAdded(`${s.name} can now log in as “${s.username}” with the password you chose.`);
      setName("");
      setUsername("");
      setPassword("");
      setConsent(false);
      onAdded();
    } catch (err) {
      setError(toErr(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Add a child</h2>
        <p className="text-sm text-muted">You create their login; they use it to sign in on their own device.</p>
      </div>
      {disabled && <Notice tone="warn">Verify your email first to add a child.</Notice>}
      {added && <Notice tone="ok">{added}</Notice>}
      <form onSubmit={onSubmit} className="space-y-4">
        <fieldset disabled={disabled || busy} className="space-y-4 disabled:opacity-60">
          <TextField label="Child's first name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={80} autoComplete="off" />
          <TextField
            label="Username for your child"
            value={username}
            onChange={(e) => setUsername(e.target.value.toLowerCase())}
            required
            minLength={3}
            maxLength={30}
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            hint="3–30 characters: lowercase letters, numbers, . _ or -. Avoid their full name."
          />
          <PasswordField
            label="Password for your child"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
            hint="At least 8 characters. You can change it later."
          />
          <div className="space-y-2 rounded-lg border border-border p-3">
            <h3 className="text-sm font-semibold">Your consent</h3>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
              <li>We store your child&apos;s name, username and learning activity: chat messages with the tutor, quiz answers, mastery levels and chosen tutor style.</li>
              <li>We use it only to tutor your child and show their progress — no ads, never sold.</li>
              <li>Messages are sent to an AI service to generate the tutor&apos;s replies.</li>
              <li>You can download or permanently delete this data at any time from this page.</li>
            </ul>
            <p className="text-sm">
              Full details: <Link href="/privacy" className="text-accent underline">privacy notice</Link>
              {policy ? ` (version ${policy.version})` : ""}.
            </p>
            <CheckboxField checked={consent} onChange={setConsent} required>
              I am this child&apos;s parent or legal guardian and I consent to Tailored Tuition processing their learning
              data as described in the privacy notice{policy ? ` (version ${policy.version})` : ""}.
            </CheckboxField>
          </div>
          <div aria-live="polite">
            <ErrorNote message={error?.message ?? null} limit={error?.limit} />
          </div>
          <Button type="submit" disabled={!consent || !policy || !name.trim() || !username || !password}>
            {busy ? "Adding…" : "Add child"}
          </Button>
        </fieldset>
      </form>
    </Card>
  );
}

function ChildRow({ child, onChanged }: { child: ChildSummary; onChanged: () => void }) {
  const [mode, setMode] = useState<"none" | "password" | "delete">("none");
  const [password, setPassword] = useState("");
  const [confirmName, setConfirmName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Err>(null);
  const [note, setNote] = useState<string | null>(null);

  function open(m: typeof mode) {
    setMode(mode === m ? "none" : m);
    setError(null);
    setNote(null);
    setPassword("");
    setConfirmName("");
  }

  async function savePassword(e: FormEvent) {
    e.preventDefault();
    if (password.length < 8) return setError({ message: "At least 8 characters, please.", limit: false });
    setBusy(true);
    setError(null);
    try {
      await api.setChildPassword(child.id, password);
      setMode("none");
      setNote(`Password changed. ${child.name} has been logged out on all devices.`);
    } catch (err) {
      setError(toErr(err));
    } finally {
      setBusy(false);
    }
  }

  async function download() {
    setError(null);
    try {
      const blob = await api.exportChild(child.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tailored-tuition-${child.username}-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(toErr(err));
    }
  }

  async function remove(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.deleteChild(child.id);
      onChanged();
    } catch (err) {
      setError(toErr(err));
      setBusy(false);
    }
  }

  return (
    <li className="space-y-3 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <div className="min-w-0">
          <h3 className="font-semibold">{child.name}</h3>
          <p className="break-all text-sm text-muted">Username: {child.username}</p>
        </div>
        <p className="text-sm text-muted">
          {child.last_active ? `Last active ${formatDate(child.last_active)}` : "Not active yet"}
        </p>
      </div>
      <div>
        <div className="mb-1 flex justify-between text-sm">
          <span className="text-muted">Overall understanding · {child.mastered} topics mastered</span>
          <span>{pct(child.overall_progress)}</span>
        </div>
        <Meter value={child.overall_progress} label={`${child.name}'s overall understanding`} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Link
          href={`/guardian/children/${encodeURIComponent(child.id)}`}
          className="inline-flex min-h-10 items-center rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-fg hover:opacity-90"
        >
          View progress
        </Link>
        <Button variant="secondary" onClick={() => open("password")} aria-expanded={mode === "password"}>
          Change password
        </Button>
        <Button variant="secondary" onClick={download}>
          Download data
        </Button>
        <Button variant="ghost" className="text-danger" onClick={() => open("delete")} aria-expanded={mode === "delete"}>
          Delete
        </Button>
      </div>
      {note && <Notice tone="ok">{note}</Notice>}
      {mode === "password" && (
        <form onSubmit={savePassword} className="space-y-3 rounded-lg border border-border p-3">
          <PasswordField label={`New password for ${child.name}`} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} maxLength={128} autoComplete="new-password" />
          <div className="flex gap-2">
            <Button type="submit" disabled={busy || !password}>
              {busy ? "Saving…" : "Save password"}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setMode("none")}>
              Cancel
            </Button>
          </div>
        </form>
      )}
      {mode === "delete" && (
        <form onSubmit={remove} className="space-y-3 rounded-lg border border-danger/40 p-3">
          <p className="text-sm">
            This <strong>permanently deletes</strong> {child.name}&apos;s account and all their learning data (chats,
            quizzes, progress) and withdraws your consent. It cannot be undone. You may want to{" "}
            <button type="button" onClick={download} className="text-accent underline">
              download their data
            </button>{" "}
            first.
          </p>
          <TextField label={`Type “${child.name}” to confirm`} value={confirmName} onChange={(e) => setConfirmName(e.target.value)} autoComplete="off" />
          <div className="flex gap-2">
            <Button type="submit" className="!bg-danger !text-bg" disabled={busy || confirmName.trim() !== child.name.trim()}>
              {busy ? "Deleting…" : "Delete permanently"}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setMode("none")}>
              Cancel
            </Button>
          </div>
        </form>
      )}
      <ErrorNote message={error?.message ?? null} limit={error?.limit} />
    </li>
  );
}

function DeleteAccount({ count }: { count: number }) {
  const { setMe } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Err>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.deleteAccount(password);
      setMe(null);
      router.replace("/");
    } catch (err) {
      setError(toErr(err));
      setBusy(false);
    }
  }

  return (
    <Card className="space-y-3">
      <h2 className="text-lg font-semibold">Delete my account</h2>
      <p className="text-sm text-muted">
        Permanently deletes your account{count > 0 ? ` and the data of your ${count === 1 ? "child" : `${count} children`}` : ""}. This
        cannot be undone.
      </p>
      {!open ? (
        <Button variant="secondary" onClick={() => setOpen(true)}>
          Delete my account…
        </Button>
      ) : (
        <form onSubmit={onSubmit} className="space-y-3">
          <PasswordField label="Enter your password to confirm" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          <div aria-live="polite">
            <ErrorNote message={error?.message ?? null} limit={error?.limit} />
          </div>
          <div className="flex gap-2">
            <Button type="submit" className="!bg-danger !text-bg" disabled={busy || !password}>
              {busy ? "Deleting…" : "Delete everything"}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
}

function Dashboard() {
  const guardian = useRequiredGuardian();
  const verified = useSearchParams().get("verified");
  const [children, setChildren] = useState<ChildSummary[] | null>(null);
  const [error, setError] = useState<Err>(null);

  const load = useCallback(() => {
    api
      .children()
      .then(setChildren)
      .catch((e) => setError(toErr(e)));
  }, []);

  useEffect(() => {
    if (guardian) load();
  }, [guardian, load]);

  if (!guardian) return <Loading />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Hello, {guardian.name}</h1>
        <p className="text-sm text-muted">Manage your children&apos;s accounts and see how they&apos;re getting on.</p>
      </div>
      {verified && guardian.email_verified && <Notice tone="ok">Email verified. You can add your child now.</Notice>}
      {!guardian.email_verified && <VerifyBanner />}

      <section aria-labelledby="children-heading" className="space-y-2">
        <h2 id="children-heading" className="text-lg font-semibold">
          Your children
        </h2>
        <ErrorNote message={error?.message ?? null} limit={error?.limit} />
        {!children ? (
          !error && <Loading />
        ) : children.length === 0 ? (
          <p className="text-sm text-muted">No children added yet.</p>
        ) : (
          <ul className="divide-y divide-border rounded-xl border border-border bg-surface">
            {children.map((c) => (
              <ChildRow key={c.id} child={c} onChanged={load} />
            ))}
          </ul>
        )}
      </section>

      <AddChild guardian={guardian} onAdded={load} />
      {guardian.is_admin && <SyllabusPanel />}
      <DeleteAccount count={children?.length ?? 0} />
    </div>
  );
}

export default function GuardianPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Dashboard />
    </Suspense>
  );
}
