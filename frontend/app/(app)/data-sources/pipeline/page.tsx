"use client";

import { useMemo } from "react";
import { Activity, CheckCircle2, Clock, XCircle } from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import type { ImportJob } from "@/lib/types";
import { formatNumber, relativeTime } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { CardGridSkeleton, EmptyState, ErrorState } from "@/components/shared/states";
import { Kpi } from "@/components/shared/kpi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ImportStatusBadge } from "@/components/data/data-bits";

function fmtDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} s`;
  return `${(ms / 60000).toFixed(1)} m`;
}

export default function PipelineMonitorPage() {
  const { data, loading, error, refetch } = useFetch<ImportJob[]>("/data/pipeline");

  const stats = useMemo(() => {
    const runs = data ?? [];
    const total = runs.length;
    const failedRecords = runs.reduce((s, r) => s + r.rows_rejected, 0);
    const processed = runs.reduce((s, r) => s + r.rows_processed, 0);
    const successful = runs.filter((r) => r.status === "success").length;
    const avgDuration = total ? runs.reduce((s, r) => s + r.duration_ms, 0) / total : 0;
    return { total, failedRecords, processed, successRate: total ? (successful / total) * 100 : 0, avgDuration };
  }, [data]);

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Pipeline Monitor" description="Live ETL ingestion runs across every connected system." />
        <CardGridSkeleton count={4} />
      </div>
    );
  }
  if (error || !data) return <ErrorState message={error || "Failed to load pipeline"} />;

  return (
    <div className="space-y-6">
      <PageHeader title="Pipeline Monitor" description="Live ETL ingestion runs across every connected system." />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Pipeline Runs" value={formatNumber(stats.total)} icon={Activity} sub="last 60 runs" />
        <Kpi label="Success Rate" value={`${stats.successRate.toFixed(0)}%`} icon={CheckCircle2} intent={stats.successRate >= 80 ? "success" : "warning"} />
        <Kpi label="Records Processed" value={formatNumber(stats.processed)} icon={CheckCircle2} />
        <Kpi label="Failed Records" value={formatNumber(stats.failedRecords)} icon={XCircle} intent={stats.failedRecords ? "danger" : "success"} sub={`avg ${fmtDuration(stats.avgDuration)}/run`} />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-sm">Ingestion Runs</CardTitle>
          <button onClick={refetch} className="text-xs text-muted-foreground hover:text-foreground">Refresh</button>
        </CardHeader>
        <CardContent>
          {data.length === 0 ? (
            <EmptyState title="No pipeline runs" message="Trigger a connector sync or import a file to populate the pipeline." icon={Activity} />
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border/60">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/60 bg-muted/40 text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                    <th className="px-3 py-2 font-medium">Source System</th>
                    <th className="px-3 py-2 font-medium">Type</th>
                    <th className="px-3 py-2 font-medium">Entity</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="hidden px-3 py-2 text-right font-medium sm:table-cell">Processed</th>
                    <th className="px-3 py-2 text-right font-medium">Failed</th>
                    <th className="hidden px-3 py-2 text-right font-medium md:table-cell">Duration</th>
                    <th className="hidden px-3 py-2 text-right font-medium md:table-cell">Last Run</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {data.map((j) => (
                    <tr key={j.id} className="transition-colors hover:bg-accent/30">
                      <td className="px-3 py-2.5 font-medium">{j.source_name}</td>
                      <td className="px-3 py-2.5">
                        <span className="rounded bg-muted px-1.5 py-0.5 text-[11px] capitalize text-muted-foreground">
                          {j.source_type}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 capitalize text-muted-foreground">{j.entity_type}</td>
                      <td className="px-3 py-2.5"><ImportStatusBadge status={j.status} /></td>
                      <td className="hidden px-3 py-2.5 text-right font-mono tabular-nums sm:table-cell">{formatNumber(j.rows_processed)}</td>
                      <td className={`px-3 py-2.5 text-right font-mono tabular-nums ${j.rows_rejected ? "text-destructive" : "text-muted-foreground"}`}>
                        {formatNumber(j.rows_rejected)}
                      </td>
                      <td className="hidden px-3 py-2.5 text-right text-muted-foreground md:table-cell">{fmtDuration(j.duration_ms)}</td>
                      <td className="hidden px-3 py-2.5 text-right text-muted-foreground md:table-cell">{relativeTime(j.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
