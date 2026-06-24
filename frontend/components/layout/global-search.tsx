"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Truck } from "lucide-react";
import { api } from "@/lib/api";
import type { Page, Shipment } from "@/lib/types";
import { ShipmentStatusBadge } from "@/components/shared/badges";

export function GlobalSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Shipment[]>([]);
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  useEffect(() => {
    if (q.trim().length < 2) {
      setResults([]);
      return;
    }
    const t = setTimeout(() => {
      api
        .get<Page<Shipment>>(`/shipments?q=${encodeURIComponent(q)}&page_size=6`)
        .then((d) => {
          setResults(d.items);
          setOpen(true);
        })
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div ref={boxRef} className="relative w-full max-w-md">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && q.trim()) {
              router.push(`/shipments?q=${encodeURIComponent(q)}`);
              setOpen(false);
            }
          }}
          placeholder="Search shipments, references, locations…"
          className="h-9 w-full rounded-lg border border-input bg-background/60 pl-9 pr-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>
      {open && results.length > 0 && (
        <div className="absolute z-50 mt-2 w-full overflow-hidden rounded-lg border border-border bg-popover shadow-lg">
          {results.map((s) => (
            <button
              key={s.id}
              onClick={() => {
                router.push(`/shipments/${s.id}`);
                setOpen(false);
                setQ("");
              }}
              className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-accent"
            >
              <span className="flex items-center gap-2">
                <Truck className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{s.reference}</span>
                <span className="text-xs text-muted-foreground">
                  {s.origin} → {s.destination}
                </span>
              </span>
              <ShipmentStatusBadge status={s.status} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
