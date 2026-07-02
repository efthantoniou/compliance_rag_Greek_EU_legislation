import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type SearchResult = {
  celex_id: string;
  labels: string[];
  text: string;
};

export function ResultCard({ result }: { result: SearchResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-mono">{result.celex_id}</CardTitle>
        <div className="flex flex-wrap gap-1">
          {result.labels.map((label) => (
            <Badge key={label} variant="secondary">
              {label}
            </Badge>
          ))}
        </div>
      </CardHeader>
      <CardContent className="text-sm leading-relaxed whitespace-pre-wrap">
        {result.text}
      </CardContent>
    </Card>
  );
}
