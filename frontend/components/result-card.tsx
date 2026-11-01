"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { describeCelex, eurLexUrl } from "@/lib/celex";
import { matchesLabel, relevance } from "@/lib/display";
import { cn } from "@/lib/utils";

export type Concept = { id: string; el: string; en: string };

export type SearchResult = {
  celex_id: string;
  labels: Concept[]; // EUROVOC level_1 (broad domains)
  subtopics: Concept[]; // level_2 (microthesauri)
  topics: Concept[]; // level_3 (specific concepts)
  text: string;
  score?: number | null; // cross-encoder relevance in [0, 1] of the best passage
  matches?: number; // how many of the document's passages matched (each document shows once)
};

// A full chunk is ~1,500 characters. Collapsed, a passage shows ~8 lines (about
// 600 characters at 66ch) — enough to judge relevance; the rest is one click away.
const COLLAPSE_OVER_CHARS = 600;
const VISIBLE_TOPICS = 4;

function conceptLabel(c: Concept) {
  return c.en && c.en !== c.el ? `${c.el} (${c.en})` : c.el;
}

export function ResultCard({ result }: { result: SearchResult }) {
  const [expanded, setExpanded] = useState(false);
  const [allTopics, setAllTopics] = useState(false);
  const collapsible = result.text.length > COLLAPSE_OVER_CHARS;
  const description = describeCelex(result.celex_id);
  const score = relevance(result.score);
  const more = matchesLabel(result.matches);
  const hiddenTopics = result.topics.length - VISIBLE_TOPICS;
  const topics = allTopics ? result.topics : result.topics.slice(0, VISIBLE_TOPICS);

  return (
    <Card>
      <CardHeader className="gap-2">
        <div className="flex items-baseline justify-between gap-3">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <CardTitle className="font-mono text-sm">
              {/* Petrol means "this came from a real document" (DESIGN.md). */}
              <a
                href={eurLexUrl(result.celex_id)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-source underline decoration-source/40 underline-offset-4 hover:decoration-source focus-visible:rounded-xs focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                {result.celex_id}
              </a>
            </CardTitle>
            {description && (
              <span className="font-ui text-[13px] text-muted-foreground">{description}</span>
            )}
          </div>
          {score && (
            <span className="flex shrink-0 flex-col items-end text-muted-foreground">
              <span
                className="font-mono text-[11px] leading-[1.9]"
                title="How closely this passage matches the query, from 0 to 1"
              >
                relevance {score}
              </span>
              {more && (
                <span
                  className="font-ui text-xs"
                  title="The passage shown is this document's best match"
                >
                  {more}
                </span>
              )}
            </span>
          )}
        </div>
        {result.labels.length > 0 && (
          <p className="font-ui text-[13px] leading-normal text-muted-foreground">
            {result.labels.map(conceptLabel).join(", ")}
          </p>
        )}
        {result.topics.length > 0 && (
          <div className="flex flex-wrap items-center gap-1">
            {topics.map((c) => (
              <Badge
                key={c.id}
                variant="outline"
                className={
                  allTopics && topics.indexOf(c) >= VISIBLE_TOPICS ? "motion-fade" : undefined
                }
              >
                {conceptLabel(c)}
              </Badge>
            ))}
            {hiddenTopics > 0 && (
              <button
                type="button"
                onClick={() => setAllTopics((v) => !v)}
                aria-expanded={allTopics}
                className="rounded-xs px-1 font-ui text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                {allTopics ? "Fewer topics" : `+${hiddenTopics} more`}
              </button>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent>
        {/* DESIGN.md `body-sm`, capped at 66ch: never let a Greek statutory
            passage run wider. */}
        {/* Height animates between 8 lines and auto (interpolate-size in
            globals.css); the mask fades the cut-off edge while collapsed. */}
        <div
          className={cn(
            "overflow-hidden transition-[height] duration-(--motion-base) ease-(--ease-out)",
            collapsible && !expanded
              ? "h-[8lh] text-[13.5px] leading-[1.55] [mask-image:linear-gradient(to_bottom,black_65%,transparent)]"
              : "h-auto text-[13.5px] leading-[1.55]"
          )}
        >
          <p className="max-w-[66ch] whitespace-pre-wrap">{result.text}</p>
        </div>
        {collapsible && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            className="mt-2 rounded-xs font-ui text-[13px] text-muted-foreground underline underline-offset-2 hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
          >
            {expanded ? "Show less" : "Show full passage"}
          </button>
        )}
      </CardContent>
    </Card>
  );
}
