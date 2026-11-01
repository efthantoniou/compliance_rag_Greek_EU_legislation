// The input surface for each mode: a raised sheet on the paper background so
// what you type is visibly separate from what the corpus returns.
export function Composer({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-3 rounded-lg border border-border bg-card p-3 sm:p-4">{children}</div>
  );
}
