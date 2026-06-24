"use client";

import { useMemo, useState } from "react";
import { Building2, MapPin, Boxes, AlertTriangle } from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import type { Warehouse } from "@/lib/types";
import { formatNumber, formatPercent } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { CardGridSkeleton, EmptyState, ErrorState } from "@/components/shared/states";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RiskLevelBadge } from "@/components/shared/badges";
import { Kpi } from "@/components/shared/kpi";

export default function WarehousesPage() {
  const { data, loading, error } = useFetch<Warehouse[]>("/inventory/warehouses");
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("all");
  const [sort, setSort] = useState("utilization");

  const regions = useMemo(
    () => Array.from(new Set((data ?? []).map((w) => w.region))).sort(),
    [data]
  );

  const filtered = useMemo(() => {
    let rows = data ?? [];
    if (q.trim()) {
      const t = q.toLowerCase();
      rows = rows.filter(
        (w) => w.name.toLowerCase().includes(t) || w.location.toLowerCase().includes(t)
      );
    }
    if (region !== "all") rows = rows.filter((w) => w.region === region);
    rows = [...rows].sort((a, b) => {
      if (sort === "utilization") return b.utilization - a.utilization;
      if (sort === "capacity") return b.capacity - a.capacity;
      if (sort === "name") return a.name.localeCompare(b.name);
      return 0;
    });
    return rows;
  }, [data, q, region, sort]);

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Warehouses" description="Distribution network capacity & risk posture." />
        <CardGridSkeleton count={6} />
      </div>
    );
  }
  if (error || !data) return <ErrorState message={error || "Failed to load warehouses"} />;

  const totalCap = data.reduce((s, w) => s + w.capacity, 0);
  const totalInv = data.reduce((s, w) => s + w.current_inventory, 0);
  const highRisk = data.filter((w) => w.risk_level === "high").length;
  const avgUtil = data.length ? data.reduce((s, w) => s + w.utilization, 0) / data.length : 0;

  return (
    <div className="space-y-6">
      <PageHeader title="Warehouses" description="Distribution network capacity & risk posture." />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Facilities" value={formatNumber(data.length)} icon={Building2} />
        <Kpi label="Network Capacity" value={formatNumber(totalCap)} icon={Boxes} sub={`${formatNumber(totalInv)} units on hand`} />
        <Kpi label="Avg Utilization" value={formatPercent(avgUtil, 0)} icon={MapPin} intent={avgUtil > 85 ? "warning" : "default"} />
        <Kpi label="High-Risk Sites" value={formatNumber(highRisk)} icon={AlertTriangle} intent={highRisk > 0 ? "danger" : "success"} />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name or location…"
          className="sm:max-w-xs"
        />
        <Select value={region} onValueChange={setRegion}>
          <SelectTrigger className="sm:w-44"><SelectValue placeholder="Region" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All regions</SelectItem>
            {regions.map((r) => (
              <SelectItem key={r} value={r}>{r}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={setSort}>
          <SelectTrigger className="sm:w-48"><SelectValue placeholder="Sort" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="utilization">Sort: Utilization</SelectItem>
            <SelectItem value="capacity">Sort: Capacity</SelectItem>
            <SelectItem value="name">Sort: Name</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="No warehouses match" message="Adjust the search or region filter." icon={Building2} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((w) => {
            const util = w.utilization;
            const bar =
              util > 90 ? "bg-destructive" : util > 75 ? "bg-warning" : "bg-success";
            return (
              <Card key={w.id} className="p-5 transition-shadow hover:shadow-md">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold leading-tight">{w.name}</p>
                    <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3" /> {w.location} · {w.region}
                    </p>
                  </div>
                  <RiskLevelBadge level={w.risk_level} />
                </div>

                <div className="mt-4 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Capacity utilization</span>
                    <span className="font-mono font-medium tabular-nums">{formatPercent(util, 0)}</span>
                  </div>
                  <Progress value={util} indicatorClassName={bar} />
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="section-label">On Hand</p>
                    <p className="mt-0.5 font-medium tabular-nums">{formatNumber(w.current_inventory)}</p>
                  </div>
                  <div>
                    <p className="section-label">Capacity</p>
                    <p className="mt-0.5 font-medium tabular-nums">{formatNumber(w.capacity)}</p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
