"use client";

import { useState } from "react";
import Markdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Activity } from "@/components/activity";
import { parseSse } from "@/lib/sse";

export default function CheckView() {
  const [doc, setDoc] = useState("");
  const [phase, setPhase] = useState<string | null>(null);
  const [searches, setSearches] = useState<string[]>([]);
  const [report, setReport] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) setDoc(await file.text());
  }

  async function check() {
    if (!doc.trim()) return;
    setBusy(true);
    setError(null);
    setSearches([]);
    setReport("");
    setPhase("thinking");
    try {
      const res = await fetch("/api/check", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ document: doc }),
      });
      if (!res.ok || !res.body) throw new Error(`Request failed (${res.status})`);
      for await (const event of parseSse(res)) {
        if (event.type === "status") setPhase(event.data.phase);
        else if (event.type === "tool") setSearches((s) => [...s, event.data.query]);
        else if (event.type === "token") setReport((r) => r + event.data.text);
        else if (event.type === "error") setError(event.data.message);
        else if (event.type === "done") setPhase(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
      setPhase(null);
    }
  }

  return (
    <div className="space-y-4">
      <input type="file" accept=".txt" onChange={onFile} className="text-sm" />
      <Textarea
        value={doc}
        onChange={(e) => setDoc(e.target.value)}
        placeholder="Paste a policy document, or upload a .txt file above…"
        rows={6}
      />
      <Button onClick={check} disabled={busy}>
        {busy ? "Checking…" : "Check"}
      </Button>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Activity phase={phase} searches={searches} />
      {report && (
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <Markdown>{report}</Markdown>
        </div>
      )}
    </div>
  );
}
