"use client";

import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Activity } from "@/components/activity";
import { linkifyCelexCitations } from "@/lib/celex";
import { parseSse } from "@/lib/sse";
import { ExternalLink } from "@/components/external-link";

export default function AskView() {
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<string | null>(null);
  const [searches, setSearches] = useState<string[]>([]);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Abort any in-flight stream if the component unmounts (e.g. tab switch).
  useEffect(() => () => abortRef.current?.abort(), []);

  async function ask() {
    if (!question.trim()) return;
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
        else if (event.type === "tool") setSearches((s) => [...s, event.data.query]);
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
    <div className="space-y-4">
      <Textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask a question about Greek / EU legislation…"
        rows={3}
      />
      <Button onClick={ask} disabled={busy}>
        {busy ? "Asking…" : "Ask"}
      </Button>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Activity phase={phase} searches={searches} />
      {answer && (
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <Markdown components={{ a: ExternalLink }}>{linkifyCelexCitations(answer)}</Markdown>
        </div>
      )}
    </div>
  );
}
