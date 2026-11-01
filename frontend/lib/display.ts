// Pure display helpers for the views, kept here so they can be unit-tested.

import type { RetrievedDocument } from "./sse";

// Cross-encoder relevance in [0, 1]. Search only returns results above the
// backend threshold, so this is just the number to show.
export function relevance(score: number | null | undefined): string | null {
  return score === null || score === undefined ? null : score.toFixed(2);
}

// Search shows each document once; this says how many of its passages matched.
export function matchesLabel(matches: number | undefined): string | null {
  return matches && matches > 1 ? `${matches} matching passages` : null;
}

// "Results 11–20 of 37" for one page of search results, plus the page count.
export function pageInfo(
  page: number,
  pageSize: number,
  total: number
): { summary: string; pages: number } {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages === 1) return { summary: `${total} ${total === 1 ? "result" : "results"}`, pages };
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  return { summary: `Results ${first}–${last} of ${total}`, pages };
}

// What an ask/check run is doing right now, in the user's terms. The backend
// only reports a single "thinking" phase, so progress is read from what has
// already streamed in: searches so far, and whether answer text has started.
export function activityMessage(
  phase: string | null,
  searches: number,
  writing: boolean
): string | null {
  if (!phase) return null;
  if (writing) return "Writing the answer…";
  if (searches === 0) return "Planning the first search…";
  return `Searching the corpus, ${searches} ${searches === 1 ? "search" : "searches"} so far…`;
}

export function healthSummary(health: { surrealdb: boolean; llamacpp: boolean }): {
  ok: boolean;
  text: string;
} {
  if (health.surrealdb && health.llamacpp) return { ok: true, text: "Ready" };
  if (!health.surrealdb && !health.llamacpp) return { ok: false, text: "Database and model offline" };
  return { ok: false, text: health.surrealdb ? "Model offline" : "Database offline" };
}

// One line for a finished retrieval trace, e.g. "Searched 5 times, found 9 documents".
export function traceSummary(steps: { query: string; documents: RetrievedDocument[] }[]): string {
  const docs = new Set(steps.flatMap((s) => s.documents.map((d) => d.celex_id))).size;
  const searched = steps.length === 1 ? "Searched once" : `Searched ${steps.length} times`;
  const found = docs === 0 ? "found nothing" : `found ${docs} ${docs === 1 ? "document" : "documents"}`;
  return `${searched}, ${found}`;
}
