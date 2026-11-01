import { describeCelex, eurLexUrl } from "@/lib/celex";

// The documents an answer actually cites, in the order it first cites them.
// Appears once, when the answer is complete.
export function Sources({ ids, snippets }: { ids: string[]; snippets: Map<string, string> }) {
  if (ids.length === 0) return null;
  return (
    <section aria-labelledby="sources-heading" className="motion-settle space-y-3 border-t border-border pt-4">
      <h2 id="sources-heading" className="field-label">
        Sources
      </h2>
      <ul className="max-w-[66ch] space-y-3">
        {ids.map((id) => {
          const description = describeCelex(id);
          const snippet = snippets.get(id);
          return (
            <li key={id} className="space-y-0.5">
              <div className="flex flex-wrap items-baseline gap-x-3">
                <a
                  href={eurLexUrl(id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-sm text-source underline decoration-source/40 underline-offset-4 hover:decoration-source focus-visible:rounded-xs focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
                >
                  {id}
                </a>
                {description && (
                  <span className="font-ui text-[13px] text-muted-foreground">{description}</span>
                )}
              </div>
              {snippet && (
                <p className="line-clamp-2 text-[13.5px] leading-[1.55] text-muted-foreground">
                  {snippet}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
