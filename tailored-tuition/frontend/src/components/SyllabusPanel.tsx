"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { SyllabusDocument } from "@/lib/types";
import { Button, Card, ErrorNote, errorMessage } from "./ui";

const MAX_BYTES = 20 * 1024 * 1024;
const ACCEPT = ".pdf,.txt,.md";

export default function SyllabusPanel() {
  const [docs, setDocs] = useState<SyllabusDocument[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.documents().then(setDocs).catch(() => setDocs([]));
  }, []);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    if (file.size > MAX_BYTES) {
      setError("That file is larger than 20 MB.");
      return;
    }
    if (!/\.(pdf|txt|md)$/i.test(file.name)) {
      setError("Please choose a .pdf, .txt or .md file.");
      return;
    }
    setBusy(true);
    try {
      const doc = await api.uploadSyllabus(file);
      setDocs((d) => [doc, ...(d ?? []).filter((x) => x.id !== doc.id)]);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <Card className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold">Syllabus material</h2>
        <p className="text-sm text-muted">
          Upload textbook chapters or notes (PDF, TXT or Markdown, up to 20 MB). The tutor
          grounds its explanations in them and cites the section it used.
        </p>
      </div>
      <input
        ref={inputRef}
        id="syllabus-file"
        type="file"
        accept={ACCEPT}
        className="sr-only"
        onChange={(e) => onFile(e.target.files?.[0])}
      />
      <Button variant="secondary" disabled={busy} onClick={() => inputRef.current?.click()}>
        {busy ? "Uploading and indexing…" : "Upload a file"}
      </Button>
      <ErrorNote message={error} />
      {docs && docs.length > 0 && (
        <ul className="divide-y divide-border text-sm">
          {docs.map((d) => (
            <li key={d.id} className="flex flex-wrap items-baseline justify-between gap-x-3 py-2">
              <span className="min-w-0 break-all font-medium">{d.filename}</span>
              <span className="text-muted">
                {d.sections} sections · {d.chunks} passages · {formatDate(d.uploaded_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
      {docs && docs.length === 0 && (
        <p className="text-sm text-muted">No files uploaded yet.</p>
      )}
    </Card>
  );
}
