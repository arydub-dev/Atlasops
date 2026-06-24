"use client";

import { useState } from "react";
import { RefreshCw, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import type { RiskAssessment, RiskSummary } from "@/lib/types";
import { titleCase } from "@/lib/format";
import { CHART_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/page-header";
import { RiskLevelBadge, RiskScore } from "@/components/shared/badges";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { ChartCard } from "@/components/charts/chart-card";
import { HorizontalBars } from "@/components/charts/charts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const LEVEL_COLOR: Record<string, string> = {
  low: CHART_COLORS.green,
  medium: CHART_COLORS.amber,
  high: CHART_COLORS.red,
  critical: "#b91c1c",
};

export default function RiskPage() {
  const { user } = useAuth();
  const [category, setCategory] = useState("all");
  const [level, setLevel] = useState("all");
  const [recomputing, setRecomputing] = useState(false);

  const { data: summary, loading: ls, refetch: refetchSummary } = useFetch<RiskSummary>("/risks/summary");

  const q = new URLSearchParams({ limit: "100" });
  if (category !== "all") q.set("category", category);
  if (level !== "all") q.set("level", level);
  const { data: risks, loading: lr, error, refetch } = useFetch<RiskAssessment[]>(
    `/risks?${q.toString()}`,
    [category, level]
  );

  const canRecompute =
    user?.role === "admin" || user?.role === "operations_manager" || user?.role === "analyst";

  async function recompute() {
    setRecomputing(true);
    try {
      await api.post("/risks/recompute");
      refetchSummary();
      refetch();
    } finally {
      setRecomputing(false);
    }
  }

  if (ls || !summary) return <LoadingState />;

  const categoryBars = Object.entries(summary.by_category).map(([name, value]) => ({
    name: titleCase(name),
    value: Math.round(value),
  }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operational Risk Center"
        description="Continuous risk scoring across suppliers, shipments, inventory and geography."
      >
        {canRecompute && (
          <Button onClick={recompute} disabled={recomputing} variant="outline" size="sm">
            <RefreshCw className={cn("h-4 w-4", recomputing && "animate-spin")} />
            Recompute
          </Button>
        )}
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Overall gauge */}
        <Card className="flex flex-col items-center justify-center p-6 text-center">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Overall Risk Score</p>
          <div className="relative my-3 flex h-32 w-32 items-center justify-center">
            <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" fill="none" stroke="hsl(var(--muted))" strokeWidth="10" />
              <circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                stroke={LEVEL_COLOR[summary.overall_level]}
                strokeWidth="10"
                strokeLinecap="round"
                strokeDasharray={`${(summary.overall_score / 100) * 326.7} 326.7`}
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="font-mono text-3xl font-semibold tabular-nums">
                {summary.overall_score.toFixed(0)}
              </span>
              <span className="text-xs text-muted-foreground">/ 100</span>
            </div>
          </div>
          <RiskLevelBadge level={summary.overall_level} />
        </Card>

        <ChartCard title="Risk by Category" description="Average score per category" className="lg:col-span-2">
          <HorizontalBars data={categoryBars} color={CHART_COLORS.red} height={220} />
        </ChartCard>
      </div>

      {/* Level counts */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {(["critical", "high", "medium", "low"] as const).map((lvl) => (
          <Card key={lvl} className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">{titleCase(lvl)}</p>
                <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
                  {summary.counts[lvl] ?? 0}
                </p>
              </div>
              <span className="h-10 w-1.5 rounded-full" style={{ backgroundColor: LEVEL_COLOR[lvl] }} />
            </div>
          </Card>
        ))}
      </div>

      {/* Risk register */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="flex items-center gap-2 text-sm">
            <ShieldAlert className="h-4 w-4" /> Risk Register
          </CardTitle>
          <div className="flex gap-2">
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                <SelectItem value="supplier">Supplier</SelectItem>
                <SelectItem value="shipment">Shipment</SelectItem>
                <SelectItem value="inventory">Inventory</SelectItem>
                <SelectItem value="geographic">Geographic</SelectItem>
              </SelectContent>
            </Select>
            <Select value={level} onValueChange={setLevel}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All levels</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {lr ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error} />
          ) : !risks || risks.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No risks for these filters.</p>
          ) : (
            risks.map((r) => (
              <div key={r.id} className="rounded-lg border border-border/60 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <RiskLevelBadge level={r.level} />
                      <span className="text-xs uppercase tracking-wide text-muted-foreground">
                        {titleCase(r.category)}
                      </span>
                    </div>
                    <p className="mt-1.5 text-sm font-medium">{r.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{r.description}</p>
                    <p className="mt-2 text-xs">
                      <span className="font-medium text-primary">Recommendation: </span>
                      <span className="text-muted-foreground">{r.recommendation}</span>
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <RiskScore score={r.score} />
                    <p className="text-[10px] text-muted-foreground">risk score</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
