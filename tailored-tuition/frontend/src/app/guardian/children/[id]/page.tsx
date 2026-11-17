"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Student } from "@/lib/types";
import ProgressView from "@/components/ProgressView";
import { ErrorNote, Loading, errorMessage } from "@/components/ui";
import { useRequiredGuardian } from "@/components/AuthProvider";

export default function ChildProgressPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const guardian = useRequiredGuardian();
  const [child, setChild] = useState<Student | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!guardian) return;
    api
      .getStudent(id)
      .then(setChild)
      .catch((e) => setError(errorMessage(e)));
  }, [guardian, id]);

  if (!guardian) return <Loading />;
  return (
    <div className="space-y-4">
      <Link href="/guardian" className="text-sm text-accent underline">
        ← Back to dashboard
      </Link>
      {error ? (
        <ErrorNote message={error} />
      ) : !child ? (
        <Loading />
      ) : (
        <ProgressView
          studentId={child.id}
          audience="guardian"
          title={`${child.name}'s progress`}
          intro="Each box is a topic; arrows show what builds on what. Open a session to read the conversation."
        />
      )}
    </div>
  );
}
