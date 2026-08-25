"use client";

import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Activity } from "@/components/activity";
import { linkifyCelexCitations } from "@/lib/celex";
import { parseSse } from "@/lib/sse";
import { ExternalLink } from "@/components/external-link";
import { CheckEmpty } from "@/components/empty-state";

export default function CheckView() {
  const [doc, setDoc] = useState("");
  const [phase, setPhase] = useState<string | null>(null);
  const [searches, setSearches] = useState<string[]>([]);
  const [report, setReport] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Abort any in-flight stream if the component unmounts (e.g. tab switch).
  useEffect(() => () => abortRef.current?.abort(), []);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) setDoc(await file.text());
  }

  const canCheck = doc.trim().length > 0 && !busy;

  async function check() {
    if (!canCheck) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
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
        signal: controller.signal,
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
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setBusy(false);
        setPhase(null);
      }
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label htmlFor="check-file" className="field-label">
          Upload a .txt file
        </label>
        <input
          id="check-file"
          type="file"
          accept=".txt"
          onChange={onFile}
          className="block w-full min-h-11 rounded-md border border-input bg-transparent px-3 py-2 font-ui text-sm outline-none file:mr-3 file:cursor-pointer file:rounded-sm file:border file:border-input file:bg-secondary file:px-2.5 file:py-1 file:font-ui file:text-sm file:font-medium file:text-secondary-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        />
      </div>
      <div className="space-y-1.5">
        <label htmlFor="check-doc" className="field-label">
          Policy document
        </label>
        <Textarea
          id="check-doc"
          value={doc}
          onChange={(e) => {
            setDoc(e.target.value);
            // A stale failure must not outlive the request it described.
            if (error) setError(null);
          }}
          placeholder="Paste a policy document, or upload a .txt file above…"
          rows={6}
        />
      </div>
      <Button onClick={check} disabled={!canCheck} className="min-h-11">
        {busy ? "Checking…" : "Check"}
      </Button>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <Activity phase={phase} searches={searches} />
      {report && (
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <Markdown components={{ a: ExternalLink }}>{linkifyCelexCitations(report)}</Markdown>
        </div>
      )}
      {!busy && !error && !report && phase === null && <CheckEmpty />}
    </div>
  );
}
