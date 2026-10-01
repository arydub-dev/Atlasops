"use client";

import { Activity, AlertTriangle, Gauge, GitBranch, Plug } from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import { relativeTime } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type PlatformObs = {
  connectors: {
    total: number;
    by_status: Record<string, number>;
    syncing: number;
    error: number;
    items: {
      id: string;
      name: string;
      type: string;
      status: string;
      health: string;
      last_sync_at?: string | null;
      next_sync_at?: string | null;
      record_count?: number;
      last_error?: string | null;
    }[];
  };
  workers: {
    failed_import_jobs: number;
    dead_letter_count: number;
    note?: string;
  };
  operations: {
    open_alerts: number;
    incidents: number;
    simulations_run: number;
  };
  graph: {
    total_nodes?: number;
    total_edges?: number;
    node_counts?: Record<string, number>;
  };
};

export default function ObservabilityPage() {
  const { data, loading, error } = useFetch<PlatformObs>("/observability/platform");

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error || "Unable to load observability"} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Platform Observability"
        description="Connector health, worker failures, graph statistics, and operational load."
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Metric
          icon={Plug}
          label="Connectors"
          value={data.connectors.total}
          sub={`${data.connectors.error} error · ${data.connectors.syncing} syncing`}
        />
        <Metric
          icon={AlertTriangle}
          label="Dead letters"
          value={data.workers.dead_letter_count}
          sub={`${data.workers.failed_import_jobs} failed imports`}
        />
        <Metric
          icon={Activity}
          label="Open alerts"
          value={data.operations.open_alerts}
          sub={`${data.operations.incidents} incidents`}
        />
        <Metric
          icon={GitBranch}
          label="Graph nodes"
          value={data.graph.total_nodes ?? 0}
          sub={`${data.graph.total_edges ?? 0} edges`}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-8">
          <CardHeader>
            <CardTitle className="text-sm">Connector health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-hidden rounded-lg border border-border/60">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/60 bg-muted/40 text-left text-[11px] uppercase text-muted-foreground">
                    <th className="px-3 py-2">Name</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Health</th>
                    <th className="px-3 py-2">Records</th>
                    <th className="px-3 py-2">Last sync</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {data.connectors.items.map((c) => (
                    <tr key={c.id}>
                      <td className="px-3 py-2.5">
                        <p className="font-medium">{c.name}</p>
                        <p className="text-xs text-muted-foreground">{c.type}</p>
                      </td>
                      <td className="px-3 py-2.5">
                        <Badge variant={c.status === "error" ? "destructive" : "secondary"}>
                          {c.status}
                        </Badge>
                      </td>
                      <td className="px-3 py-2.5 text-xs">{c.health}</td>
                      <td className="px-3 py-2.5 tabular-nums text-xs">{c.record_count ?? 0}</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">
                        {c.last_sync_at ? relativeTime(c.last_sync_at) : "—"}
                      </td>
                    </tr>
                  ))}
                  {data.connectors.items.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-3 py-8 text-center text-sm text-muted-foreground">
                        No connectors configured
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {data.workers.note && (
              <p className="mt-3 text-xs text-muted-foreground">{data.workers.note}</p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Gauge className="h-4 w-4" /> Graph composition
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(data.graph.node_counts || {}).map(([k, v]) => (
              <div key={k} className="flex justify-between text-xs">
                <span className="capitalize text-muted-foreground">{k.replace(/_/g, " ")}</span>
                <span className="font-medium tabular-nums">{v}</span>
              </div>
            ))}
            <div className="mt-4 rounded-md border border-border/60 p-3 text-xs">
              <p className="font-medium">Simulations run</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">
                {data.operations.simulations_run}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: typeof Plug;
  label: string;
  value: number;
  sub: string;
}) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Icon className="h-4 w-4" />
          <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
        </div>
        <p className="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
        <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
      </CardContent>
    </Card>
  );
}
