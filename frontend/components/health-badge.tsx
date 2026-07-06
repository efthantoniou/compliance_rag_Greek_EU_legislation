"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";

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
  const ok = health.surrealdb && health.llamacpp;
  return (
    <Badge variant={ok ? "secondary" : "destructive"}>
      {health.surrealdb ? "DB ✓" : "DB ✗"} · {health.llamacpp ? "LLM ✓" : "LLM ✗"}
    </Badge>
  );
}
