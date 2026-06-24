"use client";

import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Boxes,
  Clock,
  Factory,
  PackageCheck,
  Radar,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import { useDemoMode } from "@/lib/demo-mode";
import type { MissionControlResponse, RecommendedAction, SituationInsight } from "@/lib/types";
import { formatNumber, formatPercent, relativeTime } from "@/lib/format";
import { CHART_COLORS } from "@/lib/constants";
import { PageHeader } from "@/components/shared/page-header";
import { Kpi } from "@/components/shared/kpi";
import { MissionSkeleton } from "@/components/shared/states";
import { ErrorState } from "@/components/shared/states";
import { ChartCard } from "@/components/charts/chart-card";
import { AreaTrend, BarTrend, LineTrend } from "@/components/charts/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PriorityBadge } from "@/components/shared/badges";
import { cn } from "@/lib/utils";

export default function MissionControlPage() {
  const { enabled: demo } = useDemoMode();
  const { data, loading, error } = useFetch<MissionControlResponse>("/mission-control", [demo]);

  if (loading) return <MissionSkeleton />;
  if (error || !data) return <ErrorState message={error || "No mission control data"} />;

  const k = data.kpis;
  const now = new Date().toLocaleString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mission Control"
        description={`Operational command surface · ${now}`}
      >
        <Badge variant="success" className="gap-1.5">
          <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-success" />
          Live
        </Badge>
        {demo && (
          <Badge variant="default" className="gap-1.5">
            <Sparkles className="h-3 w-3" /> Demo Mode
          </Badge>
        )}
      </PageHeader>

      {/* SECTION 1 — Global health overview */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <HealthCard
          className="lg:col-span-3"
          score={data.health.score}
          grade={data.health.grade}
          label={data.health.label}
        />
        <div className="grid grid-cols-2 gap-4 lg:col-span-9 lg:grid-cols-3">
          <Kpi label="Active Shipments" value={formatNumber(k.active_shipments)} icon={PackageCheck} intent="default" sub="in motion" />
          <Kpi
            label="Delayed Shipments"
            value={formatNumber(k.delayed_shipments)}
            icon={Clock}
            intent={k.delayed_shipments > 0 ? "danger" : "success"}
            sub={`${formatPercent(k.on_time_delivery_rate)} on-time`}
          />
          <Kpi
            label="Critical Risks"
            value={formatNumber(k.critical_risks)}
            icon={ShieldAlert}
            intent={k.critical_risks > 0 ? "danger" : "success"}
            sub={`risk index ${k.overall_risk_score}`}
          />
          <Kpi
            label="Inventory Risk"
            value={formatNumber(k.inventory_risk_count)}
            icon={Boxes}
            intent={k.inventory_risk_count > 0 ? "warning" : "success"}
            sub="low / out-of-stock lines"
          />
          <Kpi
            label="Supplier Reliability"
            value={`${formatNumber(k.supplier_reliability_score)}`}
            icon={Factory}
            intent={k.supplier_reliability_score >= 80 ? "success" : "warning"}
            sub="avg score / 100"
          />
          <Kpi label="Open Alerts" value={formatNumber(k.open_alerts)} icon={AlertTriangle} intent={k.open_alerts > 0 ? "warning" : "success"} sub="awaiting triage" />
        </div>
      </div>

      {/* SECTION 2 + 3 — Situation report (prominent) + recommended actions */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SituationReportCard
          className="lg:col-span-7"
          headline={data.situation_report.headline}
          insights={data.situation_report.insights}
        />
        <RecommendedActions className="lg:col-span-5" actions={data.recommended_actions} />
      </div>

      {/* SECTION 4 — Critical alerts */}
      <CriticalAlertsFeed alerts={data.critical_alerts} />

      {/* SECTION 5 — Operational trends (supporting, lower) */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Operational Trends</h2>
          <span className="text-xs text-muted-foreground">Context for the decisions above</span>
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <ChartCard title="Shipment Throughput" description="Weekly shipped vs delivered vs delayed">
            <BarTrend
              data={data.shipment_trend}
              xKey="label"
              height={220}
              series={[
                { key: "shipped", name: "Shipped", color: CHART_COLORS.blue },
                { key: "delivered", name: "Delivered", color: CHART_COLORS.green },
                { key: "delayed", name: "Delayed", color: CHART_COLORS.red },
              ]}
            />
          </ChartCard>
          <ChartCard title="Delay Pressure" description="Average delay days & delayed %">
            <LineTrend
              data={data.delay_trend}
              xKey="label"
              height={220}
              series={[
                { key: "avg_delay_days", name: "Avg Delay (days)", color: CHART_COLORS.amber },
                { key: "delayed_pct", name: "Delayed %", color: CHART_COLORS.red },
              ]}
            />
          </ChartCard>
          <ChartCard title="Network Utilization" description="Inventory capacity used over time">
            <AreaTrend
              data={data.inventory_trend}
              xKey="label"
              height={220}
              showLegend={false}
              series={[{ key: "utilization", name: "Utilization %", color: CHART_COLORS.cyan }]}
            />
          </ChartCard>
          <ChartCard title="Supplier Performance" description="Score & delivery reliability">
            <LineTrend
              data={data.supplier_performance_trend}
              xKey="label"
              height={220}
              series={[
                { key: "supplier_score", name: "Supplier Score", color: CHART_COLORS.violet },
                { key: "delivery_reliability", name: "Reliability", color: CHART_COLORS.green },
              ]}
            />
          </ChartCard>
        </div>
      </div>
    </div>
  );
}

/* ----------------------------- Health score ----------------------------- */
function HealthCard({
  score,
  grade,
  label,
  className,
}: {
  score: number;
  grade: string;
  label: string;
  className?: string;
}) {
  const tone =
    score >= 85
      ? { ring: CHART_COLORS.green, text: "text-success" }
      : score >= 70
        ? { ring: CHART_COLORS.blue, text: "text-primary" }
        : score >= 55
          ? { ring: CHART_COLORS.amber, text: "text-warning" }
          : { ring: CHART_COLORS.red, text: "text-destructive" };
  const r = 52;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  return (
    <Card className={cn("surface-raised radial-fade flex flex-col items-center justify-center p-5", className)}>
      <p className="section-label self-start">Supply Chain Health</p>
      <div className="relative mt-2 flex h-36 w-36 items-center justify-center">
        <svg className="h-36 w-36 -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r={r} fill="none" stroke="hsl(var(--border))" strokeWidth="10" />
          <circle
            cx="60"
            cy="60"
            r={r}
            fill="none"
            stroke={tone.ring}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circ}`}
            style={{ transition: "stroke-dasharray 0.8s ease" }}
          />
        </svg>
        <div className="absolute flex flex-col items-center">
          <span className={cn("text-4xl font-semibold tabular-nums tracking-tight", tone.text)}>
            {score.toFixed(0)}
          </span>
          <span className="text-xs text-muted-foreground">/ 100</span>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <span className={cn("flex h-6 w-6 items-center justify-center rounded-md text-xs font-bold", tone.text, "bg-muted")}>
          {grade}
        </span>
        <span className="text-sm font-medium">{label}</span>
      </div>
    </Card>
  );
}

/* -------------------------- Situation report ---------------------------- */
const INSIGHT_TONE: Record<string, string> = {
  high: "text-destructive bg-destructive/10",
  medium: "text-warning bg-warning/10",
  low: "text-success bg-success/10",
};

function SituationReportCard({
  headline,
  insights,
  className,
}: {
  headline: string;
  insights: SituationInsight[];
  className?: string;
}) {
  return (
    <Card className={cn("surface-raised radial-fade overflow-hidden", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <Radar className="h-4 w-4" />
          </span>
          <div>
            <CardTitle className="text-sm">AI Situation Report</CardTitle>
            <p className="text-[11px] text-muted-foreground">What is happening · why it's happening</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-lg font-medium leading-snug tracking-tight">{headline}</p>
        <div className="space-y-2.5">
          {insights.map((ins, i) => (
            <div key={i} className="flex items-start gap-3 rounded-lg border border-border/60 bg-muted/30 p-3">
              <span className={cn("mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md", INSIGHT_TONE[ins.severity])}>
                <Activity className="h-3.5 w-3.5" />
              </span>
              <p className="text-sm leading-snug">{ins.text}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/* ------------------------ Recommended actions --------------------------- */
function RecommendedActions({
  actions,
  className,
}: {
  actions: RecommendedAction[];
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-sm">Recommended Actions</CardTitle>
        <span className="text-[11px] text-muted-foreground">What to do next</span>
      </CardHeader>
      <CardContent className="space-y-2.5">
        {actions.length === 0 && (
          <p className="py-6 text-center text-sm text-muted-foreground">No actions required.</p>
        )}
        {actions.map((a, i) => (
          <div key={i} className="rounded-lg border border-border/60 p-3 transition-colors hover:bg-accent/40">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2.5">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
                  {i + 1}
                </span>
                <p className="text-sm font-medium leading-snug">{a.title}</p>
              </div>
              <PriorityBadge priority={a.priority as never} />
            </div>
            <p className="mt-1.5 pl-8 text-xs leading-snug text-muted-foreground">{a.detail}</p>
            <div className="mt-2.5 flex flex-wrap items-center gap-2 pl-8">
              <span className="inline-flex items-center gap-1 rounded-md bg-success/10 px-2 py-0.5 text-[11px] font-medium text-success">
                <TrendingUp className="h-3 w-3" /> {a.expected_impact}
              </span>
              <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                Est. cost: {a.estimated_cost}
              </span>
            </div>
          </div>
        ))}
        <Link href="/risk" className="block">
          <Button variant="outline" size="sm" className="w-full">
            View full risk center <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}

/* --------------------------- Critical alerts ---------------------------- */
function CriticalAlertsFeed({
  alerts,
}: {
  alerts: MissionControlResponse["critical_alerts"];
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          Critical Alerts
        </CardTitle>
        <Link href="/alerts">
          <Button variant="ghost" size="sm">
            View all <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No critical alerts. The network is operating within normal parameters.
          </p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border/60">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/60 bg-muted/40 text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                  <th className="px-3 py-2 font-medium">Severity</th>
                  <th className="px-3 py-2 font-medium">Alert</th>
                  <th className="hidden px-3 py-2 font-medium md:table-cell">Recommended Response</th>
                  <th className="px-3 py-2 text-right font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {alerts.map((a) => (
                  <tr key={a.id} className="transition-colors hover:bg-accent/30">
                    <td className="px-3 py-2.5 align-top">
                      <PriorityBadge priority={a.priority} />
                    </td>
                    <td className="px-3 py-2.5 align-top">
                      <p className="font-medium leading-snug">{a.title}</p>
                      <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{a.message}</p>
                    </td>
                    <td className="hidden max-w-xs px-3 py-2.5 align-top text-xs text-muted-foreground md:table-cell">
                      {a.recommended_response}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-right align-top text-xs text-muted-foreground">
                      {relativeTime(a.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
