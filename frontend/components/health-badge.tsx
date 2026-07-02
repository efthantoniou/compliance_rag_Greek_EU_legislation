"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";

export type Health = { surrealdb: boolean; llamacpp: boolean };

const POLL_INTERVAL_MS = 10_000;

export function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    let active = true;
    async function check() {
      try {
        const res = await fetch("/api/health", { cache: "no-store" });
        const data = (await res.json()) as Health;
        if (active) {
          setHealth(data);
        }
      } catch {
        if (active) setHealth({ surrealdb: false, llamacpp: false });
      }
    }
    check();
    const id = setInterval(check, POLL_INTERVAL_MS);
    return () => {
      active = false;
      clearInterval(id);
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
