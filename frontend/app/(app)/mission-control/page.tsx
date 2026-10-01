"use client";

import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Boxes,
  Clock,
  Factory,
  GitBranch,
  PackageCheck,
  Plug,
  Radar,
  ShieldAlert,
  ShoppingCart,
  Siren,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import { useDemoMode } from "@/lib/demo-mode";
import type {
  MissionControlResponse,
  RecommendedAction,
  SituationInsight,
  TimelineEvent,
} from "@/lib/types";
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
  const { data, loading, error, refetch } = useFetch<MissionControlResponse>("/mission-control", [demo]);

  if (loading) return <MissionSkeleton />;
  if (error || !data)
    return (
      <ErrorState
        message={error || "No mission control data"}
        onRetry={() => refetch()}
      />
    );

  const k = data.kpis;
  const situation = data.ai_situation_report || data.situation_report;
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
        description={`Executive command centre · ${now}`}
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
          <Kpi
            label="Data Health"
            value={formatNumber(data.data_health?.score ?? 0)}
            icon={Activity}
            intent={(data.data_health?.score ?? 100) >= 80 ? "success" : "warning"}
            sub={`grade ${data.data_health?.grade ?? "—"}`}
          />
        </div>
      </div>

      {/* SECTION 2 + 3 — Situation report (prominent) + recommended actions */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <SituationReportCard
          className="lg:col-span-7"
          headline={situation.headline}
          insights={situation.insights}
        />
        <RecommendedActions className="lg:col-span-5" actions={data.recommended_actions} />
      </div>

      {/* SECTION 4 — Live operations grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <RiskHeatmapCard className="lg:col-span-3" heatmap={data.risk_heatmap} />
        <OrdersPanel
          className="lg:col-span-3"
          title="Purchase Orders"
          icon={ShoppingCart}
          openCount={data.purchase_orders?.open_count ?? k.open_purchase_orders ?? 0}
          recent={data.purchase_orders?.recent ?? []}
        />
        <OrdersPanel
          className="lg:col-span-3"
          title="Sales Orders"
          icon={PackageCheck}
          openCount={data.sales_orders?.open_count ?? k.open_sales_orders ?? 0}
          recent={(data.sales_orders?.recent ?? []).map((r) => ({
            id: r.id,
            reference: r.reference,
            status: r.status,
            total_amount: r.total_amount,
          }))}
        />
        <UpcomingRisksCard className="lg:col-span-3" risks={data.upcoming_risks ?? []} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <IncidentsPanel className="lg:col-span-4" incidents={data.top_incidents ?? []} />
        <ConnectorStatusPanel className="lg:col-span-4" status={data.connector_status} />
        <GraphStatsPanel className="lg:col-span-4" graph={data.graph} />
      </div>

      <OperationalTimelinePanel events={data.operational_timeline ?? []} />

      {(data.predictions?.length || 0) > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <CardTitle className="text-sm">Predictive Intelligence</CardTitle>
            <Link href="/predictions">
              <Button variant="ghost" size="sm">
                All <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
            {(data.predictions || []).slice(0, 6).map((p) => (
              <div key={p.id} className="rounded-md border border-border/60 p-3">
                <div className="flex justify-between gap-2">
                  <p className="text-xs font-medium leading-snug">{p.title}</p>
                  <span className="text-[10px] tabular-nums text-muted-foreground">
                    {Math.round(p.confidence * 100)}%
                  </span>
                </div>
                <p className="mt-1 text-[10px] uppercase text-muted-foreground">
                  {p.kind.replace(/_/g, " ")}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* SECTION 5 — Critical alerts */}
      <CriticalAlertsFeed alerts={data.critical_alerts} />

      {/* SECTION 6 — Operational trends (supporting, lower) */}
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
            <p className="text-[11px] text-muted-foreground">What is happening · why it&apos;s happening</p>
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
        {actions.map((a, i) => {
          const href =
            a.category === "supplier" || a.entity_type === "supplier"
              ? "/suppliers"
              : a.category === "shipment" || a.entity_type === "shipment"
                ? "/shipments"
                : a.category === "inventory" || a.entity_type === "inventory"
                  ? "/inventory"
                  : a.entity_type === "alert"
                    ? "/alerts"
                    : "/risk";
          return (
          <Link key={i} href={href} className="block rounded-lg border border-border/60 p-3 transition-colors hover:bg-accent/40">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2.5">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
                  {i + 1}
                </span>
                <p className="text-sm font-medium leading-snug">{a.title}</p>
              </div>
              <PriorityBadge priority={a.priority as never} />
            </div>
            <p className="mt-1.5 pl-8 text-xs leading-snug text-muted-foreground">
              {a.reason || a.detail}
            </p>
            <div className="mt-2.5 flex flex-wrap items-center gap-2 pl-8">
              <span className="inline-flex items-center gap-1 rounded-md bg-success/10 px-2 py-0.5 text-[11px] font-medium text-success">
                <TrendingUp className="h-3 w-3" /> {a.estimated_impact || a.expected_impact}
              </span>
              <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                Est. cost: {a.estimated_cost}
              </span>
              {typeof a.confidence === "number" ? (
                <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                  Confidence {(a.confidence * 100).toFixed(0)}%
                </span>
              ) : null}
              {a.estimate_label ? (
                <span className="text-[10px] text-muted-foreground">Modeled estimate</span>
              ) : null}
            </div>
          </Link>
          );
        })}
        <Link href="/risk" className="block">
          <Button variant="outline" size="sm" className="w-full">
            View full risk center <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}

/* --------------------------- Phase B panels ----------------------------- */
function RiskHeatmapCard({
  heatmap,
  className,
}: {
  heatmap?: Record<string, number>;
  className?: string;
}) {
  const entries = Object.entries(heatmap || {}).sort((a, b) => b[1] - a[1]);
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Risk Heatmap</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {entries.length === 0 && (
          <p className="py-6 text-center text-xs text-muted-foreground">No scored categories</p>
        )}
        {entries.map(([cat, score]) => (
          <div key={cat}>
            <div className="mb-1 flex justify-between text-xs">
              <span className="capitalize text-muted-foreground">{cat.replace(/_/g, " ")}</span>
              <span className="tabular-nums font-medium">{score.toFixed(0)}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className={cn(
                  "h-full rounded-full",
                  score >= 70 ? "bg-destructive" : score >= 45 ? "bg-warning" : "bg-success"
                )}
                style={{ width: `${Math.min(100, score)}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function OrdersPanel({
  title,
  icon: Icon,
  openCount,
  recent,
  className,
}: {
  title: string;
  icon: typeof ShoppingCart;
  openCount: number;
  recent: { id: string; reference: string; status: string; total_amount: number }[];
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {title}
        </CardTitle>
        <Badge variant="secondary">{openCount} open</Badge>
      </CardHeader>
      <CardContent className="space-y-2">
        {recent.length === 0 && (
          <p className="py-4 text-center text-xs text-muted-foreground">No recent orders</p>
        )}
        {recent.map((o) => (
          <div key={o.id} className="flex items-center justify-between gap-2 text-xs">
            <span className="truncate font-medium">{o.reference}</span>
            <span className="shrink-0 text-muted-foreground">{o.status}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function UpcomingRisksCard({
  risks,
  className,
}: {
  risks: { title: string; score: number; level: string }[];
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Upcoming Risks</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2.5">
        {risks.length === 0 && (
          <p className="py-4 text-center text-xs text-muted-foreground">No elevated risks</p>
        )}
        {risks.map((r, i) => (
          <div key={i} className="rounded-md border border-border/60 p-2">
            <div className="flex items-start justify-between gap-2">
              <p className="text-xs font-medium leading-snug">{r.title}</p>
              <span className="tabular-nums text-xs text-muted-foreground">{r.score}</span>
            </div>
            <p className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">{r.level}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function IncidentsPanel({
  incidents,
  className,
}: {
  incidents: { id: string; title: string; severity: string; status: string }[];
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Siren className="h-4 w-4 text-destructive" />
          Top Incidents
        </CardTitle>
        <Link href="/incidents">
          <Button variant="ghost" size="sm">
            All <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent className="space-y-2">
        {incidents.length === 0 && (
          <p className="py-4 text-center text-xs text-muted-foreground">No open incidents</p>
        )}
        {incidents.map((inc) => (
          <Link
            key={inc.id}
            href={`/incidents/${inc.id}`}
            className="block rounded-md border border-border/60 p-2 transition-colors hover:bg-accent/40"
          >
            <p className="text-xs font-medium leading-snug">{inc.title}</p>
            <div className="mt-1 flex gap-2 text-[10px] uppercase text-muted-foreground">
              <span>{inc.severity}</span>
              <span>·</span>
              <span>{inc.status}</span>
            </div>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}

function ConnectorStatusPanel({
  status,
  className,
}: {
  status: MissionControlResponse["connector_status"];
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Plug className="h-4 w-4 text-muted-foreground" />
          Connector Status
        </CardTitle>
        <Link href="/data-sources/connectors">
          <Button variant="ghost" size="sm">
            Manage <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-md bg-muted/40 p-2">
            <p className="text-lg font-semibold tabular-nums">{status?.total ?? 0}</p>
            <p className="text-[10px] text-muted-foreground">Total</p>
          </div>
          <div className="rounded-md bg-success/10 p-2">
            <p className="text-lg font-semibold tabular-nums text-success">{status?.healthy ?? 0}</p>
            <p className="text-[10px] text-muted-foreground">Healthy</p>
          </div>
          <div className="rounded-md bg-destructive/10 p-2">
            <p className="text-lg font-semibold tabular-nums text-destructive">{status?.error ?? 0}</p>
            <p className="text-[10px] text-muted-foreground">Error</p>
          </div>
        </div>
        {(status?.items ?? []).slice(0, 4).map((c) => (
          <div key={c.id} className="flex items-center justify-between text-xs">
            <span className="truncate font-medium">{c.name}</span>
            <Badge variant={c.status === "error" ? "destructive" : "secondary"} className="text-[10px]">
              {c.status}
            </Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function GraphStatsPanel({
  graph,
  className,
}: {
  graph: MissionControlResponse["graph"];
  className?: string;
}) {
  const counts = Object.entries(graph?.node_counts || {}).slice(0, 6);
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <GitBranch className="h-4 w-4 text-muted-foreground" />
          Knowledge Graph
        </CardTitle>
        <Link href="/graph">
          <Button variant="ghost" size="sm">
            Explore <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        <div className="mb-3 flex gap-4 text-xs">
          <span>
            <span className="font-semibold tabular-nums">{graph?.total_nodes ?? 0}</span> nodes
          </span>
          <span>
            <span className="font-semibold tabular-nums">{graph?.total_edges ?? 0}</span> edges
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {counts.map(([type, n]) => (
            <div key={type} className="rounded-md border border-border/60 px-2 py-1.5 text-xs">
              <span className="capitalize text-muted-foreground">{type.replace(/_/g, " ")}</span>
              <span className="ml-2 font-medium tabular-nums">{n}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function OperationalTimelinePanel({ events }: { events: TimelineEvent[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Clock className="h-4 w-4 text-muted-foreground" />
          Operational Timeline
        </CardTitle>
        <Link href="/graph">
          <Button variant="ghost" size="sm">
            Full timeline <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">No recent operational events</p>
        ) : (
          <ol className="relative space-y-0 border-l border-border/70 pl-4">
            {events.slice(0, 10).map((e) => (
              <li key={e.id} className="relative pb-4 last:pb-0">
                <span className="absolute -left-[1.3rem] top-1.5 h-2 w-2 rounded-full bg-primary" />
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-sm font-medium leading-snug">{e.title}</p>
                  {e.occurred_at && (
                    <span className="text-[11px] text-muted-foreground">{relativeTime(e.occurred_at)}</span>
                  )}
                </div>
                {e.summary && <p className="mt-0.5 text-xs text-muted-foreground">{e.summary}</p>}
                <div className="mt-1 flex flex-wrap gap-2 text-[10px] uppercase tracking-wide text-muted-foreground">
                  {e.entity_type && <span>{e.entity_type}</span>}
                  {e.severity && <span>{e.severity}</span>}
                  {e.source && <span>{e.source}</span>}
                </div>
              </li>
            ))}
          </ol>
        )}
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
