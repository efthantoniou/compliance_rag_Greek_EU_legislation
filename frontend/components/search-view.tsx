"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ResultCard,
  type Concept,
  type SearchResult,
} from "@/components/result-card";

export default function SearchView() {
  const [query, setQuery] = useState("");
  const [label, setLabel] = useState(""); // selected level_1 domain id ("" = all)
  const [domains, setDomains] = useState<Concept[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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

  async function runSearch() {
    if (!query.trim()) return;
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
        body: JSON.stringify({ query, top_k: 5, label: label || null }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Search failed (${res.status})`);
      const data = await res.json();
      setResults(data.results);
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
      <div className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && runSearch()}
          placeholder="Search Greek EU legislation…"
        />
        <Button onClick={runSearch} disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </Button>
      </div>
      <select
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs"
        aria-label="Filter by EUROVOC domain"
      >
        <option value="">All domains</option>
        {domains.map((c) => (
          <option key={c.id} value={c.id}>
            {c.el}
            {c.en && c.en !== c.el ? ` (${c.en})` : ""}
          </option>
        ))}
      </select>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="space-y-3">
        {results.map((result, i) => (
          <ResultCard key={`${result.celex_id}-${i}`} result={result} />
        ))}
      </div>
    </div>
  );
}
