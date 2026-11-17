"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { homeFor, useAuth } from "@/components/AuthProvider";
import { Card, Loading } from "@/components/ui";

const PRIMARY =
  "inline-flex min-h-11 items-center justify-center rounded-lg bg-accent px-5 py-2 text-sm font-medium text-accent-fg hover:opacity-90";
const SECONDARY =
  "inline-flex min-h-11 items-center justify-center rounded-lg border border-border bg-surface px-5 py-2 text-sm font-medium hover:bg-surface-2";

export default function Home() {
  const { me } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (me) router.replace(homeFor(me));
  }, [me, router]);

  if (me !== null) return <Loading />;

  return (
    <div className="space-y-8">
      <section className="space-y-3 pt-4">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          A maths tutor that teaches the way you learn.
        </h1>
        <p className="max-w-2xl text-muted">
          For CBSE Class 11 Mathematics. The tutor asks guiding questions instead of handing over answers,
          gives one hint at a time, notices when a student is stuck or tired, and shows progress as a map of
          ideas — not points.
        </p>
      </section>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">Parents and guardians</h2>
          <p className="text-sm text-muted">
            Create an account, add your child, and see their progress. You stay in control of their data: download
            or delete it any time.
          </p>
          <div className="mt-auto flex flex-wrap gap-2">
            <Link href="/signup" className={PRIMARY}>
              I&apos;m a parent or guardian
            </Link>
            <Link href="/login" className={SECONDARY}>
              Log in
            </Link>
          </div>
        </Card>
        <Card className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">Students</h2>
          <p className="text-sm text-muted">
            Log in with the username and password your parent or guardian set up for you.
          </p>
          <div className="mt-auto">
            <Link href="/login?as=student" className={PRIMARY}>
              I&apos;m a student
            </Link>
          </div>
        </Card>
      </div>

      <p className="text-sm text-muted">
        How we handle data: <Link href="/privacy" className="text-accent underline">privacy notice</Link>.
      </p>
    </div>
  );
}
