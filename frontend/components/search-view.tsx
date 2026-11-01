"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Composer } from "@/components/composer";
import { ResultCard, type Concept, type SearchResult } from "@/components/result-card";
import {
  CelexShortcut,
  NotGreekNotice,
  SearchEmpty,
  SearchNoResults,
} from "@/components/empty-state";
import { Pagination } from "@/components/pagination";
import { gateQuery, type QueryGate } from "@/lib/query-language";

// Mirrors Config.retrieval_min_score on the backend; used only to explain a
// refusal the API already decided on, never to re-filter here.
const MIN_SCORE = 0.55;
const PAGE_SIZE = 10;

// What the results on screen were searched with. Paging re-asks the same
// question, even if the input has been edited since.
type Searched = { query: string; label: string };

export default function SearchView() {
  const [query, setQuery] = useState("");
  const [label, setLabel] = useState(""); // selected level_1 domain id ("" = all)
  const [domains, setDomains] = useState<Concept[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The search a result set belongs to. null means nothing has been run yet,
  // which is a different state from "ran and found nothing".
  const [searched, setSearched] = useState<Searched | null>(null);
  const [topScore, setTopScore] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const summaryRef = useRef<HTMLParagraphElement>(null);
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

  async function runSearch(
    override?: string,
    target: { page: number; label: string } = { page: 1, label }
  ) {
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
        body: JSON.stringify({
          query: q,
          page: target.page,
          page_size: PAGE_SIZE,
          label: target.label || null,
        }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Search failed (${res.status})`);
      const data = await res.json();
      setResults(data.results);
      setTopScore(data.top_score ?? null);
      setTotal(data.total ?? data.results.length);
      setPage(target.page);
      setSearched({ query: q, label: target.label });
      if (target.page > 1 || page > 1) {
        // A new page replaced the list: move focus (and the view) to its top
        // so keyboard and screen-reader users land on the new results.
        requestAnimationFrame(() => {
          summaryRef.current?.focus({ preventScroll: true });
          summaryRef.current?.scrollIntoView({ block: "start" });
        });
      }
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
    <div className="space-y-5">
      <Composer>
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
            <Button onClick={() => runSearch()} disabled={!canSearch} className="min-h-11">
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
      </Composer>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {gate.kind === "celex" && <CelexShortcut id={gate.id} />}
      {gate.kind === "not-greek" && <NotGreekNotice />}
      {gate.kind === "ok" && (
        <>
          {results.length > 0 && searched && (
            <div className="space-y-3">
              <Pagination.Summary ref={summaryRef} page={page} pageSize={PAGE_SIZE} total={total} />
              {results.map((result, i) => (
                <ResultCard key={`${result.celex_id}-${page}-${i}`} result={result} />
              ))}
              <Pagination.Controls
                page={page}
                pageSize={PAGE_SIZE}
                total={total}
                disabled={loading}
                onPage={(p) => runSearch(searched.query, { page: p, label: searched.label })}
              />
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
              query={searched.query}
              domains={domains}
              filtered={searched.label !== ""}
              topScore={topScore}
              threshold={MIN_SCORE}
            />
          )}
        </>
      )}
    </div>
  );
}
