"use client";

import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  Database,
  Plug,
  Server,
  Users,
} from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import { formatDateTime, relativeTime, titleCase } from "@/lib/format";
import {
  healthBadgeVariant,
  type JobRow,
  type SystemHealth,
  type TenantList,
  type ErrorGroup,
} from "@/lib/admin-console";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
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

function ago(value: string | null | undefined): string {
  if (!value) return "—";
  return relativeTime(value);
}

export default function AdminDashboardPage() {
  const health = useFetch<SystemHealth>("/admin/health");
  const tenants = useFetch<TenantList>("/admin/tenants");
  const jobs = useFetch<{
    failed: number;
    last_failed: JobRow | null;
    last_successful: JobRow | null;
    items: JobRow[];
  }>("/admin/jobs");
  const errors = useFetch<{ items: ErrorGroup[] }>("/admin/errors");

  const refreshAll = () => {
    health.refetch();
    tenants.refetch();
    jobs.refetch();
    errors.refetch();
  };

  if (health.loading && !health.data) return <LoadingState label="Loading operator console…" />;
  if (health.error && !health.data) {
    return <ErrorState message={health.error} onRetry={health.refetch} />;
  }

  const h = health.data;
  const w = h?.workers;
  const tenantItems = tenants.data?.items ?? [];
  const problemTenants = tenantItems.filter((t) => t.health === "warning" || t.health === "critical");
  const lastFail = jobs.data?.last_failed;
  const lastOk = jobs.data?.last_successful;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Admin Console"
        description="Internal operator view of platform and tenant health. Not a customer-facing product surface."
      >
        <Badge variant={healthBadgeVariant(h?.overall || "unknown")}>
          {titleCase(h?.overall || "unknown")}
        </Badge>
        <Button variant="outline" size="sm" onClick={refreshAll}>
          Refresh
        </Button>
      </PageHeader>

      {h?.checked_at && (
        <p className="text-xs text-muted-foreground">Last check {ago(h.checked_at)}</p>
      )}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold">System health</h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-7">
          {(h?.components ?? []).map((c) => (
            <Card key={c.name} className="p-3">
              <p className="section-label">{titleCase(c.name)}</p>
              <Badge variant={healthBadgeVariant(c.state)} className="mt-2">
                {titleCase(c.state)}
              </Badge>
              <p className="mt-2 text-xs text-muted-foreground">{c.detail}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Background workers</h2>
          <Link href="/admin/jobs" className="text-xs font-medium text-primary hover:underline">
            Job monitor
          </Link>
        </div>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <Kpi
            label="Workers"
            value={w ? `${w.active_workers}` : "—"}
            sub={
              w?.state === "critical"
                ? "Critical — worker heartbeat missing"
                : w?.detail
            }
            icon={Server}
            intent={w?.state === "healthy" ? "success" : w?.state === "critical" ? "danger" : "warning"}
          />
          <Kpi
            label="Queue"
            value={
              w?.queue_known === false || (w?.state === "unknown" && !w?.heartbeat_at)
                ? "Unknown"
                : String(w?.queued_jobs ?? "—")
            }
            icon={Activity}
          />
          <Kpi label="Running" value={String(w?.running_jobs ?? "—")} icon={Activity} />
          <Kpi
            label="Failed jobs"
            value={String(jobs.data?.failed ?? w?.failed_jobs_heartbeat ?? "—")}
            icon={AlertTriangle}
            intent={(jobs.data?.failed ?? 0) > 0 ? "danger" : "default"}
          />
          <Kpi
            label="Heartbeat complete"
            value={String(w?.completed_jobs_heartbeat ?? "—")}
            sub={w?.heartbeat_at ? `Seen ${ago(w.heartbeat_at)}` : "No heartbeat"}
            icon={Database}
          />
        </div>
        <Card>
          <CardContent className="grid gap-3 p-4 text-sm sm:grid-cols-2">
            <div>
              <p className="section-label">Last successful job</p>
              <p className="mt-1 font-medium">
                {lastOk ? `${lastOk.job_type} · ${ago(lastOk.started_at)}` : "None in recent history"}
              </p>
              {lastOk?.organization_name && (
                <p className="text-xs text-muted-foreground">{lastOk.organization_name}</p>
              )}
            </div>
            <div>
              <p className="section-label">Last failed job</p>
              <p className="mt-1 font-medium">
                {lastFail ? `${lastFail.job_type} · ${ago(lastFail.started_at)}` : "None in recent history"}
              </p>
              {lastFail?.error_summary && (
                <p className="text-xs text-muted-foreground">{lastFail.error_summary}</p>
              )}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Tenant health</h2>
          <div className="flex gap-3 text-xs text-muted-foreground">
            <span>{tenants.data?.counts.tenants ?? 0} tenants</span>
            <span>{tenants.data?.counts.warning ?? 0} warning</span>
            <span>{tenants.data?.counts.critical ?? 0} critical</span>
          </div>
        </div>
        {tenants.loading && !tenants.data ? (
          <LoadingState label="Loading tenants…" />
        ) : tenants.error ? (
          <ErrorState message={tenants.error} onRetry={tenants.refetch} />
        ) : tenantItems.length === 0 ? (
          <EmptyState title="No tenants" message="No organizations are registered yet." icon={Users} />
        ) : (
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tenant</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Users</TableHead>
                  <TableHead>Connectors</TableHead>
                  <TableHead>Last successful sync</TableHead>
                  <TableHead>Failed jobs</TableHead>
                  <TableHead>Last activity</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenantItems.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell>
                      <Link href={`/admin/tenants/${t.id}`} className="font-medium hover:underline">
                        {t.name}
                      </Link>
                      <p className="text-xs text-muted-foreground">{t.slug}</p>
                    </TableCell>
                    <TableCell>
                      <Badge variant={healthBadgeVariant(t.health)}>{titleCase(t.health)}</Badge>
                    </TableCell>
                    <TableCell className="tabular-nums">{t.user_count}</TableCell>
                    <TableCell className="tabular-nums">{t.connector_count}</TableCell>
                    <TableCell>{ago(t.last_successful_sync_at)}</TableCell>
                    <TableCell className="tabular-nums">{t.failed_jobs}</TableCell>
                    <TableCell>{ago(t.last_activity_at)}</TableCell>
                    <TableCell>{t.created_at ? formatDateTime(t.created_at) : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm">Failing connectors</CardTitle>
            <Link href="/admin/connectors" className="text-xs text-primary hover:underline">
              All connectors
            </Link>
          </CardHeader>
          <CardContent>
            {problemTenants.length === 0 ? (
              <p className="text-sm text-muted-foreground">No tenant-level connector problems in the current snapshot.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {problemTenants.slice(0, 8).map((t) => (
                  <li key={t.id} className="flex items-center justify-between gap-2">
                    <Link href={`/admin/tenants/${t.id}`} className="hover:underline">
                      {t.name}
                    </Link>
                    <Badge variant={healthBadgeVariant(t.health)}>{titleCase(t.health)}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm">Recent errors</CardTitle>
            <Link href="/admin/errors" className="text-xs text-primary hover:underline">
              Grouped errors
            </Link>
          </CardHeader>
          <CardContent>
            {(errors.data?.items ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No grouped errors in the current snapshot.</p>
            ) : (
              <ul className="space-y-3">
                {(errors.data?.items ?? []).slice(0, 6).map((e, i) => (
                  <li key={`${e.sample_id}-${i}`} className="text-sm">
                    <div className="flex items-center gap-2">
                      <Plug className="h-3.5 w-3.5 text-muted-foreground" />
                      <Badge variant={e.severity === "critical" ? "destructive" : "warning"}>
                        {titleCase(e.error_type)}
                      </Badge>
                      <span className="text-xs text-muted-foreground">×{e.count}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{e.message}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
