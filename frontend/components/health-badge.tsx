"use client";

import { useEffect, useState } from "react";
import { healthSummary } from "@/lib/display";
import { cn } from "@/lib/utils";

export type Health = { surrealdb: boolean; llamacpp: boolean };

const POLL_INTERVAL_MS = 10_000;

export function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    let active = true;
    let intervalId: ReturnType<typeof setInterval> | undefined;

    async function check() {
      try {
        const res = await fetch("/api/health", { cache: "no-store" });
        const data = (await res.json()) as Health;
        if (active) setHealth(data);
      } catch {
        if (active) setHealth({ surrealdb: false, llamacpp: false });
      }
    }

    function startPolling() {
      if (intervalId !== undefined) return;
      check(); // immediate check whenever polling (re)starts
      intervalId = setInterval(check, POLL_INTERVAL_MS);
    }

    function stopPolling() {
      if (intervalId !== undefined) {
        clearInterval(intervalId);
        intervalId = undefined;
      }
    }

    // Only poll while the tab is visible: pause when it's hidden and re-check
    // immediately when the user returns, so we never waste background requests.
    function handleVisibility() {
      if (document.visibilityState === "visible") startPolling();
      else stopPolling();
    }

    if (document.visibilityState === "visible") startPolling();
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      active = false;
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, []);

  if (!health) return null;
  const { ok, text } = healthSummary(health);
  return (
    <span
      role="status"
      title={`Database ${health.surrealdb ? "connected" : "unreachable"}, model ${health.llamacpp ? "loaded" : "unreachable"}`}
      className={cn(
        "inline-flex items-center gap-1.5 font-ui text-[13px]",
        ok ? "text-muted-foreground" : "text-destructive"
      )}
    >
      {/* While healthy, a soft ring breathes out from the dot; it stops (and the
          dot turns red) the moment a service goes down, so the change reads. */}
      <span aria-hidden className="relative inline-flex size-1.5">
        {ok && <span className="motion-halo absolute inset-0 rounded-full bg-ok" />}
        <span className={cn("relative size-1.5 rounded-full", ok ? "bg-ok" : "bg-destructive")} />
      </span>
      {text}
    </span>
  );
}
