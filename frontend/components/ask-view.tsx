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
import { AskEmpty } from "@/components/empty-state";

export default function AskView() {
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<string | null>(null);
  const [searches, setSearches] = useState<TraceStep[]>([]);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Abort any in-flight stream if the component unmounts (panels stay mounted
  // across mode switches, so this is leaving the page).
  useEffect(() => () => abortRef.current?.abort(), []);

  // celex_id -> first snippet seen across this run's searches.
  const snippets = useMemo(() => {
    const map = new Map<string, string>();
    for (const step of searches)
      for (const d of step.documents) if (!map.has(d.celex_id)) map.set(d.celex_id, d.snippet);
    return map;
  }, [searches]);

  const canAsk = question.trim().length > 0 && !busy;

  async function ask() {
    if (!canAsk) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    setError(null);
    setSearches([]);
    setAnswer("");
    setPhase("thinking");
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question }),
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
        else if (event.type === "token") setAnswer((a) => a + event.data.text);
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
          <label htmlFor="ask-question" className="field-label">
            Your question
          </label>
          <Textarea
            id="ask-question"
            value={question}
            onChange={(e) => {
              setQuestion(e.target.value);
              // A stale failure must not outlive the request it described.
              if (error) setError(null);
            }}
            placeholder="Ask a question about Greek / EU legislation…"
            rows={3}
          />
        </div>
        <Button onClick={ask} disabled={!canAsk} className="min-h-11">
          {busy ? "Asking…" : "Ask"}
        </Button>
      </Composer>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <RetrievalTrace steps={searches} phase={phase} writing={answer.length > 0} />
      {answer && (
        <div className="prose prose-sm max-w-[66ch] dark:prose-invert">
          <SnippetContext.Provider value={snippets}>
            <Markdown components={{ a: ExternalLink }}>{linkifyCelexCitations(answer)}</Markdown>
          </SnippetContext.Provider>
        </div>
      )}
      {!busy && answer && <Sources ids={citedCelexIds(answer)} snippets={snippets} />}
      {!busy && !error && !answer && phase === null && <AskEmpty />}
    </div>
  );
}
