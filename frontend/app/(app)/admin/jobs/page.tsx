"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import { relativeTime, titleCase } from "@/lib/format";
import { healthBadgeVariant, type JobRow } from "@/lib/admin-console";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type JobsPayload = {
  queued: number;
  running: number;
  failed: number;
  successful: number;
  completed_24h: number;
  last_successful: JobRow | null;
  last_failed: JobRow | null;
  items: JobRow[];
};

export default function AdminJobsPage() {
  const { data, loading, error, refetch } = useFetch<JobsPayload>("/admin/jobs");
  const [inspect, setInspect] = useState<JobRow | null>(null);
  const [retryMsg, setRetryMsg] = useState<string | null>(null);

  async function retry(job: JobRow) {
    if (!job.connection_id) return;
    setRetryMsg(null);
    try {
      await api.post(
        `/admin/connectors/${job.connection_id}/retry?organization_id=${job.organization_id}`
      );
      setRetryMsg("Incremental sync queued.");
      refetch();
    } catch (e) {
      setRetryMsg(e instanceof Error ? e.message : "Retry failed");
    }
  }

  if (loading) return <LoadingState label="Loading jobs…" />;
  if (error) return <ErrorState message={error} onRetry={refetch} />;
  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader title="Background jobs" description="Recent connector syncs and imports across tenants.">
        <Button variant="outline" size="sm" asChild>
          <Link href="/admin">Dashboard</Link>
        </Button>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          Refresh
        </Button>
      </PageHeader>
      {retryMsg && <p className="text-xs text-muted-foreground">{retryMsg}</p>}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5 text-sm">
        <Card className="p-3"><p className="section-label">Queued / running</p><p className="mt-1 tabular-nums">{data?.queued ?? 0} / {data?.running ?? 0}</p></Card>
        <Card className="p-3"><p className="section-label">Successful</p><p className="mt-1 tabular-nums">{data?.successful ?? 0}</p></Card>
        <Card className="p-3"><p className="section-label">Failed</p><p className="mt-1 tabular-nums">{data?.failed ?? 0}</p></Card>
        <Card className="p-3"><p className="section-label">Completed (recent window)</p><p className="mt-1 tabular-nums">{data?.completed_24h ?? 0}</p></Card>
        <Card className="p-3"><p className="section-label">Last failure</p><p className="mt-1">{data?.last_failed ? relativeTime(data.last_failed.started_at || "") : "—"}</p></Card>
      </div>

      {items.length === 0 ? (
        <EmptyState title="No jobs" message="No recent sync or import jobs." />
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job</TableHead>
                <TableHead>Tenant</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((j) => (
                <TableRow key={`${j.kind}-${j.id}`}>
                  <TableCell>
                    <p className="font-medium">{j.job_type}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">{j.id}</p>
                  </TableCell>
                  <TableCell>
                    <Link href={`/admin/tenants/${j.organization_id}`} className="hover:underline">
                      {j.organization_name || j.organization_id.slice(0, 8)}
                    </Link>
                  </TableCell>
                  <TableCell>{j.started_at ? relativeTime(j.started_at) : "—"}</TableCell>
                  <TableCell>
                    <Badge variant={healthBadgeVariant(j.status)}>{j.status}</Badge>
                  </TableCell>
                  <TableCell className="tabular-nums">{j.duration_ms} ms</TableCell>
                  <TableCell className="space-x-2">
                    <Button size="sm" variant="ghost" onClick={() => setInspect(j)}>
                      Inspect
                    </Button>
                    {j.can_retry && j.connection_id && (
                      <Button size="sm" variant="outline" onClick={() => retry(j)}>
                        Retry
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {inspect && (
        <Card>
          <CardContent className="space-y-2 p-4 text-sm">
            <div className="flex items-center justify-between">
              <p className="font-medium">Job {inspect.id}</p>
              <Button size="sm" variant="ghost" onClick={() => setInspect(null)}>
                Close
              </Button>
            </div>
            <p>Type: {inspect.job_type}</p>
            <p>Tenant: {inspect.organization_name}</p>
            <p>Status: {inspect.status}</p>
            <p>Failure class: {titleCase(inspect.failure_class)}</p>
            <p>Duration: {inspect.duration_ms} ms</p>
            <p className="text-muted-foreground">Error: {inspect.error_summary || "—"}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
