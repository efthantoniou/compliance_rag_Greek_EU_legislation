import { Badge } from "@/components/ui/badge";

export function Activity({
  phase,
  searches,
}: {
  phase: string | null;
  searches: string[];
}) {
  if (!phase && searches.length === 0) return null;
  return (
    <div className="space-y-2">
      {phase && (
        <p className="text-sm text-muted-foreground">
          {phase === "thinking" ? "Thinking…" : "Working…"}
        </p>
      )}
      <div className="flex flex-wrap gap-1">
        {searches.map((q, i) => (
          <Badge key={`${q}-${i}`} variant="outline">
            🔍 {q}
          </Badge>
        ))}
      </div>
    </div>
  );
}
