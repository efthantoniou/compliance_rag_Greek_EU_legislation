import { forwardRef } from "react";
import { Button } from "@/components/ui/button";
import { pageInfo } from "@/lib/display";

type PageProps = { page: number; pageSize: number; total: number };

// "Results 11–20 of 37" above the list. Focusable (tabIndex -1) so a page
// change can move focus here.
const Summary = forwardRef<HTMLParagraphElement, PageProps>(function Summary(
  { page, pageSize, total },
  ref
) {
  return (
    <p
      ref={ref}
      tabIndex={-1}
      aria-live="polite"
      className="scroll-mt-4 rounded-xs font-ui text-[13px] text-muted-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      {pageInfo(page, pageSize, total).summary}
    </p>
  );
});

function Controls({
  page,
  pageSize,
  total,
  disabled,
  onPage,
}: PageProps & { disabled: boolean; onPage: (page: number) => void }) {
  const { pages } = pageInfo(page, pageSize, total);
  if (pages <= 1) return null;
  return (
    <nav aria-label="Search result pages" className="flex items-center justify-between gap-3 pt-2">
      <Button
        variant="outline"
        className="min-h-11 font-ui"
        disabled={disabled || page <= 1}
        onClick={() => onPage(page - 1)}
      >
        Previous
      </Button>
      <span className="font-ui text-[13px] text-muted-foreground">
        Page {page} of {pages}
      </span>
      <Button
        variant="outline"
        className="min-h-11 font-ui"
        disabled={disabled || page >= pages}
        onClick={() => onPage(page + 1)}
      >
        Next
      </Button>
    </nav>
  );
}

export const Pagination = { Summary, Controls };
