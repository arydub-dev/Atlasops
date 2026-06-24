"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

interface DemoModeState {
  enabled: boolean;
  seeding: boolean;
  toggle: () => void;
  lastSeededAt: string | null;
}

const DemoModeContext = createContext<DemoModeState | undefined>(undefined);
const KEY = "scc_demo_mode";

export function DemoModeProvider({ children }: { children: React.ReactNode }) {
  const [enabled, setEnabled] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [lastSeededAt, setLastSeededAt] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setEnabled(window.localStorage.getItem(KEY) === "1");
    }
  }, []);

  const seedDisruptions = useCallback(async () => {
    setSeeding(true);
    // best-effort: regenerate alerts + recompute risk so demos always look alive.
    // Silently ignores 403s for read-only roles.
    try {
      await Promise.allSettled([
        api.post("/risks/recompute"),
        api.post("/alerts/generate"),
      ]);
      setLastSeededAt(new Date().toISOString());
    } finally {
      setSeeding(false);
    }
  }, []);

  const toggle = useCallback(() => {
    setEnabled((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(KEY, next ? "1" : "0");
      }
      if (next) void seedDisruptions();
      return next;
    });
  }, [seedDisruptions]);

  return (
    <DemoModeContext.Provider value={{ enabled, seeding, toggle, lastSeededAt }}>
      {children}
    </DemoModeContext.Provider>
  );
}

export function useDemoMode(): DemoModeState {
  const ctx = useContext(DemoModeContext);
  if (!ctx) throw new Error("useDemoMode must be used within DemoModeProvider");
  return ctx;
}
