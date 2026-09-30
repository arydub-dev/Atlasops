"use client";

import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  Link2,
  Server,
  Sparkles,
  Workflow,
} from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import { titleCase } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Kpi } from "@/components/shared/kpi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type SyncRow = {
  id: string;
  connection_id: string;
  status: string;
  latency_ms: number;
  created_at?: string | null;
};

type PlatformOps = {
  workers: { dead_letter_count?: number; failed_import_jobs?: number; note?: string };
  connectors: {
    total?: number;
    avg_health_score?: number;
    avg_sync_latency_ms?: number;
    by_status?: Record<string, number>;
    recent_syncs?: SyncRow[];
  };
  ai_usage: { reports_generated?: number };
  automations: { workflow_runs?: number };
  alerts: { open?: number; deliveries?: number; delivery_failures?: number };
  integrations?: Record<string, boolean | string>;
  data_quality?: { overall_score?: number; grade?: string } | null;
  connection_count?: number;
};

export default function PlatformOpsPage() {
  const { data, loading, error, refetch } = useFetch<PlatformOps>("/platform-ops");

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error || "Unavailable"} onRetry={refetch} />;

  const workers = data.workers || {};
  const connectors = data.connectors || {};
  const ai = data.ai_usage || {};
  const automations = data.automations || {};
  const alerts = data.alerts || {};
  const byStatus = connectors.by_status || {};
  const recent = connectors.recent_syncs || [];
  const integrations = Object.entries(data.integrations || {});

  return (
    <div className="space-y-6">
      <PageHeader
        title="Platform Operations"
        description="Workers, connector latency, AI usage, automations, and alert delivery."
      >
        <Badge variant="secondary" className="gap-1">
          <Server className="h-3 w-3" /> Tenant ops
        </Badge>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          Refresh
        </Button>
      </PageHeader>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi
          label="Dead letters"
          value={String(workers.dead_letter_count ?? 0)}
          icon={AlertTriangle}
          intent={(workers.dead_letter_count ?? 0) > 0 ? "danger" : "success"}
        />
        <Kpi
          label="Failed imports"
          value={String(workers.failed_import_jobs ?? 0)}
          icon={Activity}
          intent={(workers.failed_import_jobs ?? 0) > 0 ? "warning" : "default"}
        />
        <Kpi
          label="AI reports"
          value={String(ai.reports_generated ?? 0)}
          icon={Sparkles}
        />
        <Kpi
          label="Workflow runs"
          value={String(automations.workflow_runs ?? 0)}
          icon={Workflow}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-7">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm">Connector operations</CardTitle>
            <Link href="/connector-studio">
              <Button variant="ghost" size="sm">
                <Link2 className="h-3.5 w-3.5" /> Studio
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <Metric label="Connections" value={String(connectors.total ?? data.connection_count ?? 0)} />
              <Metric
                label="Avg health"
                value={
                  connectors.avg_health_score != null
                    ? String(Math.round(Number(connectors.avg_health_score)))
                    : "—"
                }
              />
              <Metric
                label="Avg latency"
                value={
                  connectors.avg_sync_latency_ms != null
                    ? `${Math.round(Number(connectors.avg_sync_latency_ms))} ms`
                    : "—"
                }
              />
            </div>

            {Object.keys(byStatus).length > 0 && (
              <div className="flex flex-wrap gap-2">
                {Object.entries(byStatus).map(([status, count]) => (
                  <Badge key={status} variant="outline">
                    {titleCase(status)} · {count}
                  </Badge>
                ))}
              </div>
            )}

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Latency</TableHead>
                  <TableHead>When</TableHead>
                  <TableHead>Connection</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recent.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-muted-foreground">
                      No recent syncs for this organization.
                    </TableCell>
                  </TableRow>
                ) : (
                  recent.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell>
                        <Badge
                          variant={
                            row.status === "success" || row.status === "ok"
                              ? "success"
                              : row.status === "error" || row.status === "failed"
                                ? "destructive"
                                : "secondary"
                          }
                        >
                          {row.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="tabular-nums">{row.latency_ms} ms</TableCell>
                      <TableCell className="text-muted-foreground">
                        {row.created_at ? new Date(row.created_at).toLocaleString() : "—"}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {row.connection_id.slice(0, 8)}…
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="lg:col-span-5">
          <CardHeader>
            <CardTitle className="text-sm">Alerts & integrations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="Open alerts" value={String(alerts.open ?? 0)} />
            <Row label="Deliveries" value={String(alerts.deliveries ?? 0)} />
            <Row label="Delivery failures" value={String(alerts.delivery_failures ?? 0)} />
            {data.data_quality && (
              <Row
                label="Data quality"
                value={`${Math.round(Number(data.data_quality.overall_score ?? 0))} (${data.data_quality.grade ?? "—"})`}
              />
            )}
            <div className="pt-2">
              <p className="mb-2 text-xs uppercase text-muted-foreground">Integrations</p>
              <div className="space-y-2">
                {integrations.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No integration status reported.</p>
                ) : (
                  integrations.map(([name, enabled]) => (
                    <div key={name} className="flex items-center justify-between">
                      <span className="capitalize text-muted-foreground">{name}</span>
                      <Badge variant={enabled ? "success" : "outline"}>
                        {enabled ? "Configured" : "Off"}
                      </Badge>
                    </div>
                  ))
                )}
              </div>
            </div>
            {workers.note && (
              <p className="pt-2 text-xs text-muted-foreground">{workers.note}</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/60 px-3 py-2">
      <p className="text-[11px] uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border/40 pb-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}
