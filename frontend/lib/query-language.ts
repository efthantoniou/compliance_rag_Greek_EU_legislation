import { isCelexId } from "./celex";

// Greek and Greek Extended. A query with any Greek character counts as Greek,
// which deliberately lets mixed queries through: "GDPR προστασία δεδομένων" and
// "de minimis κρατικές ενισχύσεις" both retrieve well (measured 0.47 and 0.94),
// so gating on "purely Greek" would reject working queries.
const GREEK_CHARACTER = /[Ͱ-Ͽἀ-῿]/;

export function hasGreekCharacters(query: string): boolean {
  return GREEK_CHARACTER.test(query);
}

export type QueryGate =
  | { kind: "ok" }
  | { kind: "celex"; id: string }
  | { kind: "not-greek" };

/**
 * Decides whether a query is worth sending to retrieval.
 *
 * The corpus is Greek and the cross-encoder cannot match across languages —
 * measured on this corpus, English queries score a median 0.10 at top-1 against
 * 0.90 for Greek, and Greeklish scores below 0.01. Rather than spend a search
 * to return nothing, say so up front and point somewhere useful.
 *
 * This is a better error message, not a safety mechanism: a perfectly Greek
 * query can still retrieve nothing ("acquis communautaire και εθνικό δίκαιο"
 * scores 0.0047). The server-side score threshold is what catches that.
 */
export function gateQuery(raw: string): QueryGate {
  const query = raw.trim();
  // A bare CELEX id is an exact-identifier lookup, not a semantic search, and
  // retrieval handles it badly (0.05). Send them straight to the source.
  if (isCelexId(query.toUpperCase())) {
    return { kind: "celex", id: query.toUpperCase() };
  }
  if (!hasGreekCharacters(query)) return { kind: "not-greek" };
  return { kind: "ok" };
}
