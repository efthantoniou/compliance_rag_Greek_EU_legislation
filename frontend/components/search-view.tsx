"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ResultCard,
  type Concept,
  type SearchResult,
} from "@/components/result-card";
import {
  CelexShortcut,
  NotGreekNotice,
  SearchEmpty,
  SearchNoResults,
  WeakRetrievalNotice,
} from "@/components/empty-state";
import { gateQuery, type QueryGate } from "@/lib/query-language";

// Mirrors Config.retrieval_weak_score on the backend; used only to explain the
// number the API already decided on, never to re-classify here.
const WEAK_SCORE = 0.5;
const MIN_SCORE = 0.1;

export default function SearchView() {
  const [query, setQuery] = useState("");
  const [label, setLabel] = useState(""); // selected level_1 domain id ("" = all)
  const [domains, setDomains] = useState<Concept[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The query a result set belongs to. null means nothing has been run yet,
  // which is a different state from "ran and found nothing".
  const [searched, setSearched] = useState<string | null>(null);
  const [status, setStatus] = useState<"grounded" | "weak" | "refused">("grounded");
  const [topScore, setTopScore] = useState<number | null>(null);
  // Set when the query never reached the server: wrong script, or a CELEX id.
  const [gate, setGate] = useState<QueryGate>({ kind: "ok" });
  const abortRef = useRef<AbortController | null>(null);

  // Load the EUROVOC level_1 domains once to populate the filter dropdown.
  useEffect(() => {
    let active = true;
    fetch("/api/labels")
      .then((r) => r.json())
      .then((d) => active && setDomains(d.labels ?? []))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const canSearch = query.trim().length > 0 && !loading;

  async function runSearch(override?: string) {
    const q = (override ?? query).trim();
    if (!q || loading) return;

    // Don't spend a retrieval pass on a query the corpus cannot match.
    const verdict = gateQuery(q);
    setGate(verdict);
    if (verdict.kind !== "ok") {
      setResults([]);
      setSearched(null);
      setError(null);
      return;
    }
    // Cancel any in-flight request so a slower earlier search can't overwrite
    // the results of a newer one.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ query: q, top_k: 5, label: label || null }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Search failed (${res.status})`);
      const data = await res.json();
      setResults(data.results);
      setStatus(data.status ?? "grounded");
      setTopScore(data.top_score ?? null);
      setSearched(q);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label htmlFor="search-query" className="field-label">
          Search query
        </label>
        <div className="flex gap-2">
          <Input
            id="search-query"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              // A stale failure must not outlive the request it described.
              if (error) setError(null);
              if (gate.kind !== "ok") setGate({ kind: "ok" });
            }}
            onKeyDown={(e) => e.key === "Enter" && runSearch()}
            placeholder="Search Greek EU legislation…"
            className="min-h-11"
          />
          <Button
            onClick={() => runSearch()}
            disabled={!canSearch}
            className="min-h-11"
          >
            {loading ? "Searching…" : "Search"}
          </Button>
        </div>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="domain-filter" className="field-label">
          Filter by EUROVOC domain
        </label>
        <select
          id="domain-filter"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="min-h-11 w-full rounded-md border border-input bg-transparent px-3 font-ui text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <option value="">All domains</option>
          {domains.map((c) => (
            <option key={c.id} value={c.id}>
              {c.el}
              {c.en && c.en !== c.el ? ` (${c.en})` : ""}
            </option>
          ))}
        </select>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {gate.kind === "celex" && <CelexShortcut id={gate.id} />}
      {gate.kind === "not-greek" && <NotGreekNotice />}
      {gate.kind === "ok" && (
        <>
          {status === "weak" && results.length > 0 && topScore !== null && (
            <WeakRetrievalNotice topScore={topScore} threshold={WEAK_SCORE} />
          )}
          {results.length > 0 && (
            <div className="space-y-3">
              {results.map((result, i) => (
                <ResultCard key={`${result.celex_id}-${i}`} result={result} />
              ))}
            </div>
          )}
          {!loading && !error && results.length === 0 && searched === null && (
            <SearchEmpty
              domains={domains}
              onPick={(q) => {
                setQuery(q);
                setError(null);
                runSearch(q);
              }}
            />
          )}
          {!loading && !error && results.length === 0 && searched !== null && (
            <SearchNoResults
              query={searched}
              domains={domains}
              filtered={label !== ""}
              topScore={topScore}
              threshold={MIN_SCORE}
            />
          )}
        </>
      )}
    </div>
  );
}
