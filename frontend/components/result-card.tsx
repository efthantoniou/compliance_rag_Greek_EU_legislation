import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { eurLexUrl } from "@/lib/celex";

export type Concept = { id: string; el: string; en: string };

export type SearchResult = {
  celex_id: string;
  labels: Concept[]; // EUROVOC level_1 (broad domains)
  subtopics: Concept[]; // level_2 (microthesauri)
  topics: Concept[]; // level_3 (specific concepts)
  text: string;
};

function conceptLabel(c: Concept) {
  return c.en && c.en !== c.el ? `${c.el} (${c.en})` : c.el;
}

export function ResultCard({ result }: { result: SearchResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-mono">
          <a
            href={eurLexUrl(result.celex_id)}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:underline"
          >
            {result.celex_id}
          </a>
        </CardTitle>
        {result.labels.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {result.labels.map((c) => (
              <Badge key={c.id} variant="secondary">
                {conceptLabel(c)}
              </Badge>
            ))}
          </div>
        )}
        {result.topics.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {result.topics.map((c) => (
              <Badge key={c.id} variant="outline">
                {conceptLabel(c)}
              </Badge>
            ))}
          </div>
        )}
      </CardHeader>
      <CardContent className="text-sm leading-relaxed whitespace-pre-wrap">
        {result.text}
      </CardContent>
    </Card>
  );
}
