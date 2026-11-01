"use client";

import { useState } from "react";
import { activityMessage, traceSummary } from "@/lib/display";
import type { RetrievedDocument } from "@/lib/sse";
import { cn } from "@/lib/utils";

export type TraceStep = { query: string; documents: RetrievedDocument[] };

// The chain of custody for an answer: every search the agent ran, in order,
// with how many documents it brought back. Steps draw in as they land; once
// the answer is done the trace folds into one line the user can reopen.
export function RetrievalTrace({
  steps,
  phase,
  writing,
}: {
  steps: TraceStep[];
  phase: string | null;
  writing: boolean;
}) {
  const [open, setOpen] = useState(false);
  const running = phase !== null;
  const message = activityMessage(phase, steps.length, writing);
  if (!running && steps.length === 0) return null;

  if (!running) {
    return (
      <div className="space-y-2">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="inline-flex min-h-11 items-center gap-2 rounded-xs font-ui text-sm text-muted-foreground hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
        >
          <span
            aria-hidden
            className={cn(
              "inline-block text-xs transition-transform duration-(--motion-fast) ease-(--ease-out)",
              open && "rotate-90"
            )}
          >
            ▸
          </span>
          {traceSummary(steps)}
        </button>
        {open && <TraceList steps={steps} className="motion-fade" />}
      </div>
    );
  }

  return (
    <TraceList steps={steps} animate>
      {message && (
        <li className="motion-trace-in relative">
          <Node state="current" />
          <p role="status" className="font-ui text-sm text-foreground">
            {message}
          </p>
        </li>
      )}
    </TraceList>
  );
}

function TraceList({
  steps,
  animate = false,
  className,
  children,
}: {
  steps: TraceStep[];
  animate?: boolean;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <ol
      aria-label="Searches run"
      className={cn("ml-1 space-y-2.5 border-l border-border pl-5", className)}
    >
      {steps.map((step, i) => (
        <li key={`${step.query}-${i}`} className={cn("relative", animate && "motion-trace-in")}>
          <Node state="done" />
          <div className="flex flex-wrap items-baseline justify-between gap-x-4">
            <span className="font-body text-[13.5px] leading-[1.55]">{step.query}</span>
            <span
              className={cn(
                "font-mono text-[11px] leading-[1.9]",
                step.documents.length === 0 ? "text-uncertain" : "text-muted-foreground"
              )}
            >
              {step.documents.length === 0
                ? "nothing found"
                : `${step.documents.length} ${step.documents.length === 1 ? "document" : "documents"}`}
            </span>
          </div>
        </li>
      ))}
      {children}
    </ol>
  );
}

function Node({ state }: { state: "done" | "current" }) {
  return (
    <span
      aria-hidden
      className={cn(
        "absolute top-[0.55em] -left-[24.5px] size-2 rounded-full ring-4 ring-background",
        state === "done" ? "bg-muted-foreground" : "motion-pulse bg-foreground"
      )}
    />
  );
}
