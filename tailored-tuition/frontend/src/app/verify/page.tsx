"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Card, ErrorNote, Loading, errorMessage } from "@/components/ui";

function Verify() {
  const token = useSearchParams().get("token");
  const { setMe } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true; // tokens are single-use: never send twice (strict mode)
    api
      .verifyEmail(token)
      .then((res) => {
        setMe({ role: "guardian", guardian: res.guardian });
        router.replace("/guardian?verified=1");
      })
      .catch((e) => setError(errorMessage(e)));
  }, [token, setMe, router]);

  if (!token || error) {
    return (
      <div className="mx-auto max-w-md space-y-4">
        <h1 className="text-2xl font-semibold">Email verification</h1>
        <Card className="space-y-3">
          <ErrorNote message={error ?? "This link is missing its code."} />
          <p className="text-sm text-muted">
            Links expire after a while and work only once. Log in and use &ldquo;Resend verification&rdquo; on your
            dashboard to get a new one.
          </p>
          <Link href="/login" className="text-sm text-accent underline">
            Go to log in
          </Link>
        </Card>
      </div>
    );
  }
  return <Loading label="Verifying your email…" />;
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Verify />
    </Suspense>
  );
}
