"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Database,
  Plug,
  RefreshCw,
  TriangleAlert,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import type { DataSource, DataSummary, IntegrationTemplate } from "@/lib/types";
import { formatNumber, relativeTime } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { Kpi } from "@/components/shared/kpi";
import { CardGridSkeleton, EmptyState, ErrorState } from "@/components/shared/states";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ConnectorIcon, HealthDot, StatusBadge } from "@/components/data/data-bits";

export default function DataSourcesPage() {
  const { user } = useAuth();
  const canWrite = user && user.role !== "executive";
  const { data: summary, loading, error, refetch } = useFetch<DataSummary>("/data/summary");
  const { data: sources, refetch: refetchSources } = useFetch<DataSource[]>("/data/sources");
  const { data: integrations } = useFetch<IntegrationTemplate[]>("/data/integrations");
  const [syncing, setSyncing] = useState<number | null>(null);

  async function sync(id: number) {
    setSyncing(id);
    try {
      await api.post(`/data/sources/${id}/sync`);
      refetch();
      refetchSources();
    } finally {
      setSyncing(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Data Sources" description="Connect and monitor enterprise systems feeding the control tower." />
        <CardGridSkeleton count={4} />
      </div>
    );
  }
  if (error || !summary) return <ErrorState message={error || "Failed to load data sources"} />;

  const available = (integrations ?? []).filter((i) => !i.configured);

  return (
    <div className="space-y-6">
      <PageHeader title="Data Sources" description="Connect and monitor enterprise systems feeding the control tower.">
        {summary.mode === "demo" ? (
          <Badge variant="warning" className="gap-1.5">
            <Database className="h-3 w-3" /> Demo Dataset Active
          </Badge>
        ) : (
          <Badge variant="success" className="gap-1.5">
            <Plug className="h-3 w-3" /> Connected Mode
          </Badge>
        )}
      </PageHeader>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Connected Systems" value={formatNumber(summary.connected_systems)} icon={Plug} intent="success" sub={`${summary.total_sources} total sources`} />
        <Kpi label="Available Integrations" value={formatNumber(summary.available_integrations)} icon={Database} sub="ready to connect" />
        <Kpi label="Records Imported" value={formatNumber(summary.records_imported_total)} icon={CheckCircle2} sub={`${formatNumber(summary.records_imported_today)} today`} />
        <Kpi
          label="Last Sync"
          value={summary.last_sync_at ? relativeTime(summary.last_sync_at) : "—"}
          icon={Clock}
          intent={summary.failures.length ? "warning" : "default"}
          sub={summary.failures.length ? `${summary.failures.length} failing` : "all healthy"}
        />
      </div>

      {summary.failures.length > 0 && (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="flex items-start gap-3 py-4">
            <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <div className="text-sm">
              <p className="font-medium">Ingestion attention required</p>
              <p className="text-muted-foreground">
                {summary.failures.map((f) => f.source).join(", ")} {summary.failures.length === 1 ? "has" : "have"} an
                active failure. Review the{" "}
                <Link href="/data-sources/pipeline" className="text-primary underline-offset-2 hover:underline">
                  pipeline monitor
                </Link>
                .
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Connected systems */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-sm">Connected Systems</CardTitle>
          <Link href="/data-sources/connectors">
            <Button variant="ghost" size="sm">
              Manage connectors <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {!sources || sources.length === 0 ? (
            <EmptyState title="No connectors yet" message="Add an integration to start ingesting external data." icon={Plug} />
          ) : (
            <div className="overflow-hidden rounded-lg border border-border/60">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/60 bg-muted/40 text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2 font-medium">System</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium">Health</th>
                    <th className="hidden px-3 py-2 font-medium sm:table-cell">Records</th>
                    <th className="hidden px-3 py-2 font-medium md:table-cell">Last Sync</th>
                    <th className="px-3 py-2 text-right font-medium">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {sources.map((s) => (
                    <tr key={s.id} className="transition-colors hover:bg-accent/30">
                      <td className="px-3 py-2.5">
                        <Link href={`/data-sources/connectors/${s.id}`} className="flex items-center gap-2.5 hover:text-primary">
                          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                            <ConnectorIcon type={s.connector_type} className="h-4 w-4" />
                          </span>
                          <span className="font-medium">{s.name}</span>
                        </Link>
                      </td>
                      <td className="px-3 py-2.5"><StatusBadge status={s.status} /></td>
                      <td className="px-3 py-2.5"><HealthDot health={s.health} withLabel /></td>
                      <td className="hidden px-3 py-2.5 font-mono tabular-nums sm:table-cell">{formatNumber(s.record_count)}</td>
                      <td className="hidden px-3 py-2.5 text-muted-foreground md:table-cell">
                        {s.last_sync_at ? relativeTime(s.last_sync_at) : "never"}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {canWrite && (
                          <Button variant="outline" size="sm" onClick={() => sync(s.id)} disabled={syncing === s.id}>
                            <RefreshCw className={`h-3.5 w-3.5 ${syncing === s.id ? "animate-spin" : ""}`} />
                            Sync
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Available integrations */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-sm">Available Integrations</CardTitle>
          <Link href="/data-sources/connectors">
            <Button variant="ghost" size="sm">
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {available.map((i) => (
            <Link
              key={i.type}
              href="/data-sources/connectors"
              className="flex items-start gap-3 rounded-lg border border-border/60 p-3 transition-colors hover:bg-accent/40"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <ConnectorIcon type={i.type} className="h-4 w-4" />
              </span>
              <div>
                <p className="text-sm font-medium leading-tight">{i.name}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{i.category}</p>
              </div>
            </Link>
          ))}
          {available.length === 0 && (
            <p className="col-span-full py-4 text-center text-sm text-muted-foreground">
              All available integrations are configured.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
