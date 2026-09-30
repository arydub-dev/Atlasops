"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  Boxes,
  Factory,
  GitBranch,
  Search,
  ShieldAlert,
  Siren,
  Truck,
  Warehouse,
} from "lucide-react";
import { api } from "@/lib/api";
import type { SearchResultItem } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

const TYPE_ICON: Record<string, typeof Search> = {
  shipment: Truck,
  supplier: Factory,
  warehouse: Warehouse,
  inventory: Boxes,
  alert: AlertTriangle,
  risk: ShieldAlert,
  incident: Siren,
  purchase_order: GitBranch,
  sales_order: GitBranch,
};

function hrefFor(item: SearchResultItem): string {
  if (item.href) return item.href;
  switch (item.entity_type) {
    case "shipment":
      return `/shipments/${item.entity_id}`;
    case "supplier":
      // Detail route not shipped; open list with focus query.
      return `/suppliers?focus=${encodeURIComponent(item.entity_id)}&q=${encodeURIComponent(item.title)}`;
    case "warehouse":
      return `/warehouses?focus=${encodeURIComponent(item.entity_id)}&q=${encodeURIComponent(item.title)}`;
    case "incident":
      return `/incidents?focus=${encodeURIComponent(item.entity_id)}`;
    case "inventory":
      return `/inventory?q=${encodeURIComponent(item.title)}`;
    case "alert":
      return `/alerts?q=${encodeURIComponent(item.title)}`;
    case "risk":
      return `/risk?q=${encodeURIComponent(item.title)}`;
    case "purchase_order":
    case "sales_order":
      return `/mission-control`;
    default:
      return `/graph?type=${encodeURIComponent(item.entity_type)}&id=${encodeURIComponent(item.entity_id)}`;
  }
}

export function GlobalSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
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
    if (q.trim().length < 2) return;
    const t = setTimeout(() => {
      api
        .get<{ items: SearchResultItem[] }>(`/search?q=${encodeURIComponent(q)}&limit=12`)
        .then((d) => {
          setResults(d.items || []);
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
          onChange={(e) => {
            const next = e.target.value;
            setQ(next);
            if (next.trim().length < 2) {
              setResults([]);
              setOpen(false);
            }
          }}
          onFocus={() => results.length && setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && results[0]) {
              router.push(hrefFor(results[0]));
              setOpen(false);
              setQ("");
            }
          }}
          placeholder="Search suppliers, shipments, incidents, risks…"
          className="h-9 w-full rounded-lg border border-input bg-background/60 pl-9 pr-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>
      {open && results.length > 0 && (
        <div className="absolute z-50 mt-2 max-h-80 w-full overflow-auto rounded-lg border border-border bg-popover shadow-lg">
          {results.map((item) => {
            const Icon = TYPE_ICON[item.entity_type] || Search;
            return (
              <button
                key={`${item.entity_type}-${item.entity_id}`}
                onClick={() => {
                  router.push(hrefFor(item));
                  setOpen(false);
                  setQ("");
                }}
                className="flex w-full items-start justify-between gap-3 px-3 py-2.5 text-left text-sm hover:bg-accent"
              >
                <span className="flex min-w-0 items-start gap-2">
                  <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{item.title}</span>
                    <span className="block truncate text-xs text-muted-foreground">{item.summary}</span>
                  </span>
                </span>
                <span className="flex shrink-0 flex-col items-end gap-1">
                  <Badge variant="secondary" className="text-[10px] uppercase">
                    {item.entity_type.replace(/_/g, " ")}
                  </Badge>
                  {item.risk_score != null && (
                    <span className="text-[10px] text-muted-foreground">risk {item.risk_score}</span>
                  )}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
