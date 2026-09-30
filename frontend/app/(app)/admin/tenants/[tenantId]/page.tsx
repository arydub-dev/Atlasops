"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import { formatDateTime, relativeTime, titleCase } from "@/lib/format";
import {
  healthBadgeVariant,
  type ConnectorRow,
  type JobRow,
  type TenantRow,
} from "@/lib/admin-console";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
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

type TenantDetail = {
  overview: TenantRow;
  connectors: ConnectorRow[];
  jobs: JobRow[];
  audit_events: {
    id: string;
    action: string;
    resource: string;
    resource_id: string | null;
    detail: string | null;
    created_at: string | null;
  }[];
  checked_at: string;
};

function ago(value: string | null | undefined): string {
  if (!value) return "—";
  return relativeTime(value);
}

export default function AdminTenantDetailPage() {
  const params = useParams<{ tenantId: string }>();
  const tenantId = params.tenantId;
  const { data, loading, error, refetch } = useFetch<TenantDetail>(
    tenantId ? `/admin/tenants/${tenantId}` : null
  );
  const [retrying, setRetrying] = useState<string | null>(null);
  const [retryMsg, setRetryMsg] = useState<string | null>(null);

  async function retry(connectionId: string) {
    setRetrying(connectionId);
    setRetryMsg(null);
    try {
      await api.post(`/admin/connectors/${connectionId}/retry?organization_id=${tenantId}`);
      setRetryMsg("Incremental sync queued.");
      refetch();
    } catch (e) {
      setRetryMsg(e instanceof Error ? e.message : "Retry failed");
    } finally {
      setRetrying(null);
    }
  }

  if (loading) return <LoadingState label="Loading tenant health…" />;
  if (error || !data) return <ErrorState message={error || "Tenant not found"} onRetry={refetch} />;

  const o = data.overview;

  return (
    <div className="space-y-6">
      <PageHeader title={o.name} description="Operational metadata only — credentials are never shown.">
        <Badge variant={healthBadgeVariant(o.health)}>{titleCase(o.health)}</Badge>
        <Button variant="outline" size="sm" asChild>
          <Link href="/admin">Back</Link>
        </Button>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          Refresh
        </Button>
      </PageHeader>
      {retryMsg && <p className="text-xs text-muted-foreground">{retryMsg}</p>}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4 text-sm">
          <p className="section-label">Tenant ID</p>
          <p className="mt-1 break-all font-mono text-xs">{o.id}</p>
        </Card>
        <Card className="p-4 text-sm">
          <p className="section-label">Created</p>
          <p className="mt-1">{o.created_at ? formatDateTime(o.created_at) : "—"}</p>
        </Card>
        <Card className="p-4 text-sm">
          <p className="section-label">Users / connectors</p>
          <p className="mt-1 tabular-nums">
            {o.user_count} / {o.connector_count}
          </p>
        </Card>
        <Card className="p-4 text-sm">
          <p className="section-label">Last activity</p>
          <p className="mt-1">{ago(o.last_activity_at)}</p>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Connector health</CardTitle>
        </CardHeader>
        <CardContent>
          {data.connectors.length === 0 ? (
            <EmptyState title="No connectors" message="This tenant has not configured connectors." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Connector</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last success</TableHead>
                  <TableHead>Last attempt</TableHead>
                  <TableHead>Last failure</TableHead>
                  <TableHead>Retries</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.connectors.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.name}</TableCell>
                    <TableCell>{c.connector_type}</TableCell>
                    <TableCell>
                      <Badge variant={healthBadgeVariant(c.status)}>{titleCase(c.status)}</Badge>
                    </TableCell>
                    <TableCell>{ago(c.last_successful_sync_at)}</TableCell>
                    <TableCell>{ago(c.last_attempted_sync_at)}</TableCell>
                    <TableCell className="max-w-xs text-xs text-muted-foreground">
                      {c.last_error ? (
                        <>
                          <span>{c.last_error}</span>
                          <p className="mt-0.5">{titleCase(c.failure_class)}</p>
                        </>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="tabular-nums">{c.retry_count}</TableCell>
                    <TableCell>
                      {c.is_active && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={retrying === c.id}
                          onClick={() => retry(c.id)}
                        >
                          Retry
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Job history</CardTitle>
        </CardHeader>
        <CardContent>
          {data.jobs.length === 0 ? (
            <EmptyState title="No jobs" message="No sync or import history for this tenant." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Error</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.jobs.map((j) => (
                  <TableRow key={`${j.kind}-${j.id}`}>
                    <TableCell>
                      <p className="font-medium">{j.job_type}</p>
                      <p className="font-mono text-[11px] text-muted-foreground">{j.id}</p>
                    </TableCell>
                    <TableCell>{ago(j.started_at)}</TableCell>
                    <TableCell>
                      <Badge variant={healthBadgeVariant(j.status)}>{j.status}</Badge>
                    </TableCell>
                    <TableCell className="tabular-nums">{j.duration_ms} ms</TableCell>
                    <TableCell className="max-w-sm text-xs text-muted-foreground">
                      {j.error_summary || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Recent audit events</CardTitle>
        </CardHeader>
        <CardContent>
          {data.audit_events.length === 0 ? (
            <EmptyState title="No audit events" message="No tenant audit rows in the current window." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Detail</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.audit_events.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>{ago(a.created_at)}</TableCell>
                    <TableCell className="font-medium">{a.action}</TableCell>
                    <TableCell>
                      {a.resource}
                      {a.resource_id ? `:${a.resource_id.slice(0, 8)}` : ""}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{a.detail || "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
