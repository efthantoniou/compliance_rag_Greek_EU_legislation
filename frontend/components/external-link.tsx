"use client";

import { createContext, useContext, useId, type AnchorHTMLAttributes } from "react";
import { describeCelex } from "@/lib/celex";

const EUR_LEX = "https://eur-lex.europa.eu/";

// celex_id -> passage snippet from this answer's searches, for citation previews.
export const SnippetContext = createContext<Map<string, string>>(new Map());

// react-markdown `a` renderer: EUR-Lex citation links should open in a new
// tab rather than navigating away from an in-progress answer. Citations are
// identifiers from a real document, so they get mono + petrol (DESIGN.md);
// any other link stays plain ink. Hovering or focusing a citation previews
// the passage it came from.
export function ExternalLink(props: AnchorHTMLAttributes<HTMLAnchorElement>) {
  const snippets = useContext(SnippetContext);
  const previewId = useId();
  const href = typeof props.href === "string" ? props.href : "";
  const celexId = href.startsWith(EUR_LEX) ? href.split("CELEX:")[1] : undefined;
  const snippet = celexId ? snippets.get(celexId) : undefined;

  if (!celexId) {
    return <a {...props} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2" />;
  }

  return (
    <span className="group/cite relative">
      <a
        {...props}
        target="_blank"
        rel="noopener noreferrer"
        aria-describedby={snippet ? previewId : undefined}
        className="font-mono text-[0.9em] text-source underline decoration-source/40 underline-offset-2 hover:decoration-source"
      />
      {snippet && (
        // display:none until hovered/focused (so it never widens the page), then
        // fades up from @starting-style.
        <span
          id={previewId}
          role="tooltip"
          className="absolute top-full left-0 z-20 mt-1.5 hidden w-[min(20rem,80vw)] rounded-md border border-border bg-popover p-3 font-body text-[13px] leading-[1.55] text-popover-foreground not-italic shadow-sm transition-[opacity,translate,display] transition-discrete duration-(--motion-fast) ease-(--ease-out) group-focus-within/cite:block group-hover/cite:block starting:translate-y-1 starting:opacity-0"
        >
          {describeCelex(celexId) && (
            <span className="mb-1 block font-ui text-xs text-muted-foreground">
              {describeCelex(celexId)}
            </span>
          )}
          <span className="line-clamp-5 block">{snippet}</span>
        </span>
      )}
    </span>
  );
}
