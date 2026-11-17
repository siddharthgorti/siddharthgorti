"use client";

import ProgressView from "@/components/ProgressView";
import { Loading } from "@/components/ui";
import { useRequiredStudent } from "@/components/AuthProvider";

export default function ProgressPage() {
  const student = useRequiredStudent();
  if (!student) return <Loading />;
  return (
    <ProgressView
      studentId={student.id}
      audience="student"
      title="Your map of ideas"
      intro="Each box is a topic; arrows show what builds on what. Tap a topic to work on it."
    />
  );
}
