"use client";

import type { Concept } from "@/components/result-card";
import { eurLexUrl } from "@/lib/celex";

/**
 * Empty and no-result states.
 *
 * DESIGN.md treats these as first-class rather than as absence: the corpus is
 * bounded, so the interface has to "say what the corpus does cover, so the
 * limit is informative rather than a dead end." Typography and hairlines do all
 * the work — no illustration, no icon-in-circle, no colour used for emphasis.
 * Amber ◆ appears only on the no-results state, where it means uncertainty.
 */

/** Verified against the live corpus — each returns results. */
export const EXAMPLE_QUERIES = [
  "προστασία δεδομένων προσωπικού χαρακτήρα",
  "ασφάλεια τροφίμων",
  "εκπομπές αερίων θερμοκηπίου",
  "δημόσιες συμβάσεις",
] as const;

function Shell({
  label,
  headline,
  children,
}: {
  label: string;
  headline: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="border-t border-border pt-5">
      <p className="field-label">{label}</p>
      <p className="mt-2 max-w-[66ch] text-[19px] leading-[1.55]">{headline}</p>
      {children}
    </div>
  );
}

export function ExampleQueries({
  onPick,
}: {
  onPick: (query: string) => void;
}) {
  return (
    <div className="mt-5">
      <p className="field-label">Try one of these</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {EXAMPLE_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="min-h-11 rounded-sm border border-border px-3 py-1.5 text-left font-body text-sm transition-colors hover:border-foreground/40 hover:bg-secondary focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * The coverage statement. These are the 21 EUROVOC level-1 domains already
 * fetched for the filter dropdown, so this is live corpus metadata rather than
 * a hardcoded claim that goes stale on the next ingest.
 */
export function Coverage({ domains }: { domains: Concept[] }) {
  if (domains.length === 0) return null;
  return (
    <div className="mt-5 border-t border-border pt-4">
      <p className="field-label">
        Corpus coverage — {domains.length} EUROVOC domains
      </p>
      <p className="mt-2 max-w-[66ch] font-ui text-[13px] leading-[1.65] text-muted-foreground">
        {domains.map((d, i) => (
          <span key={d.id}>
            {i > 0 && <span aria-hidden="true"> · </span>}
            {d.el.toLowerCase()}
          </span>
        ))}
      </p>
    </div>
  );
}

export function SearchEmpty({
  domains,
  onPick,
}: {
  domains: Concept[];
  onPick: (query: string) => void;
}) {
  return (
    <Shell
      label="No search yet"
      headline="Search Greek translations of EU legislation. Results are passages from the corpus itself, each carrying its CELEX identifier so you can open the source on EUR-Lex."
    >
      <ExampleQueries onPick={onPick} />
      <Coverage domains={domains} />
    </Shell>
  );
}

export function SearchNoResults({
  query,
  domains,
  filtered,
  topScore,
  threshold,
}: {
  query: string;
  domains: Concept[];
  filtered: boolean;
  topScore?: number | null;
  threshold?: number;
}) {
  return (
    <div className="border-t border-border pt-5">
      {/* Amber, never red. Retrieval finding nothing is correct behaviour, not
          a system fault — DESIGN.md reserves red for backend/stream failures. */}
      <p className="field-label text-uncertain">◆ Nothing retrieved</p>
      <p className="mt-2 max-w-[66ch] text-[19px] leading-[1.55]">
        No passage in the corpus matched{" "}
        <span className="font-mono text-[0.9em]">{query}</span>
        {filtered ? " within the selected domain." : "."}
      </p>
      <p className="mt-3 max-w-[66ch] text-sm text-muted-foreground">
        {filtered
          ? "Widen the filter to all domains, or try broader wording."
          : "The corpus is bounded — it covers the domains below and nothing outside them. Try broader wording, or a term closer to the legislative vocabulary."}
      </p>
      {/* The trace that justifies the refusal. DESIGN.md: refusing is correct
          behaviour, so show the working rather than hiding it. */}
      {typeof topScore === "number" && typeof threshold === "number" && (
        <p className="mt-4 font-mono text-[11px] leading-[1.9] text-muted-foreground">
          best match {topScore.toFixed(4)} · threshold {threshold.toFixed(2)} ·
          declined
        </p>
      )}
      <Coverage domains={domains} />
    </div>
  );
}

/**
 * Search is Greek-only. Ask is not — the planner translates before it
 * retrieves — so this points there rather than being a dead end.
 */
export function NotGreekNotice({ onGoToAsk }: { onGoToAsk?: () => void }) {
  return (
    <div className="border-t border-border pt-5">
      <p className="field-label text-uncertain">◆ Greek only</p>
      <p className="mt-2 max-w-[66ch] text-[19px] leading-[1.55]">
        Search matches Greek text against a Greek corpus, so a Latin-script
        query retrieves nothing regardless of how well it is phrased.
      </p>
      <p className="mt-3 max-w-[66ch] text-sm text-muted-foreground">
        Rewrite the query in Greek — mixed terms are fine, so{" "}
        <span className="font-mono text-[0.9em]">GDPR προστασία δεδομένων</span>{" "}
        works. Transliteration does not:{" "}
        <span className="font-mono text-[0.9em]">prostasia dedomenon</span> finds
        nothing.
      </p>
      {onGoToAsk && (
        <p className="mt-3 max-w-[66ch] text-sm text-muted-foreground">
          Or use{" "}
          <button
            type="button"
            onClick={onGoToAsk}
            className="text-source underline underline-offset-2 hover:no-underline focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
          >
            Ask
          </button>
          , which accepts any language and searches in Greek for you.
        </p>
      )}
    </div>
  );
}

/**
 * A bare CELEX id is an exact-identifier lookup, which semantic retrieval
 * handles badly. Hand over the source directly instead.
 */
export function CelexShortcut({ id }: { id: string }) {
  return (
    <div className="border-t border-border pt-5">
      <p className="field-label">Document identifier</p>
      <p className="mt-2 max-w-[66ch] text-[19px] leading-[1.55]">
        <span className="font-mono text-[0.85em]">{id}</span> is a CELEX
        identifier, not a search term.
      </p>
      <p className="mt-3 max-w-[66ch] text-sm text-muted-foreground">
        Open it directly on EUR-Lex, or search for the subject matter instead.
      </p>
      <p className="mt-4">
        <a
          href={eurLexUrl(id)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-11 items-center rounded-sm border border-border px-3 font-ui text-sm text-source transition-colors hover:border-source focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
        >
          Open {id} on EUR-Lex →
        </a>
      </p>
    </div>
  );
}

/** Retrieval succeeded but the best match was mediocre. Caveat, never hidden. */
export function WeakRetrievalNotice({
  topScore,
  threshold,
}: {
  topScore: number;
  threshold: number;
}) {
  return (
    <div className="rounded-sm border border-uncertain/40 bg-uncertain-quiet px-4 py-3">
      <p className="field-label text-uncertain">◆ Weak match</p>
      <p className="mt-1.5 max-w-[66ch] text-sm">
        Nothing in the corpus matched this query strongly. The passages below
        are the closest available and may not answer it.
      </p>
      <p className="mt-2 font-mono text-[11px] text-muted-foreground">
        best match {topScore.toFixed(4)} · confident above {threshold.toFixed(2)}
      </p>
    </div>
  );
}

export function AskEmpty() {
  return (
    <Shell
      label="No question yet"
      headline="Ask in Greek or English. Answers are built only from retrieved passages and cite the CELEX identifier of every source."
    >
      <p className="mt-3 max-w-[66ch] text-sm text-muted-foreground">
        When nothing relevant is retrieved, the answer says so rather than
        filling the gap. That refusal is the intended behaviour.
      </p>
    </Shell>
  );
}

export function CheckEmpty() {
  return (
    <Shell
      label="No document yet"
      headline="Paste a policy document, or upload a .txt file. Each topic found in the document is matched against the regulations that govern it."
    >
      <p className="mt-3 max-w-[66ch] text-sm text-muted-foreground">
        Longer documents take longer — every extracted topic runs its own
        retrieval pass.
      </p>
    </Shell>
  );
}
