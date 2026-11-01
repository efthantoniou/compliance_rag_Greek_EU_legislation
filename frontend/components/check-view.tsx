"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Markdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Composer } from "@/components/composer";
import { RetrievalTrace, type TraceStep } from "@/components/retrieval-trace";
import { Sources } from "@/components/sources";
import { citedCelexIds, linkifyCelexCitations } from "@/lib/celex";
import { parseSse } from "@/lib/sse";
import { ExternalLink, SnippetContext } from "@/components/external-link";
import { CheckEmpty } from "@/components/empty-state";

export default function CheckView() {
  const [doc, setDoc] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [phase, setPhase] = useState<string | null>(null);
  const [searches, setSearches] = useState<TraceStep[]>([]);
  const [report, setReport] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Abort any in-flight stream if the component unmounts (panels stay mounted
  // across mode switches, so this is leaving the page).
  useEffect(() => () => abortRef.current?.abort(), []);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setDoc(await file.text());
  }

  // celex_id -> first snippet seen across this run's searches.
  const snippets = useMemo(() => {
    const map = new Map<string, string>();
    for (const step of searches)
      for (const d of step.documents) if (!map.has(d.celex_id)) map.set(d.celex_id, d.snippet);
    return map;
  }, [searches]);

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
        else if (event.type === "tool")
          setSearches((s) => [
            ...s,
            { query: event.data.query, documents: event.data.documents ?? [] },
          ]);
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
    <div className="space-y-5">
      <Composer>
        <div className="space-y-1.5">
          <p className="field-label">Upload a .txt file</p>
          {/* The native control's "Choose File / No file chosen" text can't be
            styled or translated, so the input is visually hidden and the
            label acts as the button. It stays keyboard-focusable. */}
          <div className="flex items-center gap-3">
            <input
              id="check-file"
              type="file"
              accept=".txt"
              onChange={onFile}
              className="peer sr-only"
            />
            <label
              htmlFor="check-file"
              className="inline-flex min-h-11 items-center rounded-md border border-input px-3 font-ui text-sm hover:bg-secondary peer-focus-visible:border-ring peer-focus-visible:ring-3 peer-focus-visible:ring-ring/50"
            >
              Choose a file
            </label>
            <span className="truncate font-ui text-sm text-muted-foreground">
              {fileName ?? "No file chosen"}
            </span>
          </div>
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
      </Composer>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <RetrievalTrace steps={searches} phase={phase} writing={report.length > 0} />
      {report && (
        <div className="prose prose-sm max-w-[66ch] dark:prose-invert">
          <SnippetContext.Provider value={snippets}>
            <Markdown components={{ a: ExternalLink }}>{linkifyCelexCitations(report)}</Markdown>
          </SnippetContext.Provider>
        </div>
      )}
      {!busy && report && <Sources ids={citedCelexIds(report)} snippets={snippets} />}
      {!busy && !error && !report && phase === null && <CheckEmpty />}
    </div>
  );
}
