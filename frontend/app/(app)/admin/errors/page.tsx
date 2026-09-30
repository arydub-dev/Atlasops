"use client";

import Link from "next/link";
import { useFetch } from "@/lib/use-fetch";
import { relativeTime, titleCase } from "@/lib/format";
import { type ErrorGroup } from "@/lib/admin-console";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function AdminErrorsPage() {
  const { data, loading, error, refetch } = useFetch<{ items: ErrorGroup[]; checked_at: string }>(
    "/admin/errors"
  );

  if (loading) return <LoadingState label="Loading errors…" />;
  if (error) return <ErrorState message={error} onRetry={refetch} />;
  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Error monitor"
        description="Grouped operational errors. Messages are redacted; Sentry remains the tracing backend when configured."
      >
        <Button variant="outline" size="sm" asChild>
          <Link href="/admin">Dashboard</Link>
        </Button>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          Refresh
        </Button>
      </PageHeader>
      {data?.checked_at && (
        <p className="text-xs text-muted-foreground">Snapshot {relativeTime(data.checked_at)}</p>
      )}
      {items.length === 0 ? (
        <EmptyState title="No errors" message="No connector or import failures in the current snapshot." />
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>When</TableHead>
                <TableHead>Subsystem</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Tenants</TableHead>
                <TableHead>Count</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((e, i) => (
                <TableRow key={`${e.sample_id}-${i}`}>
                  <TableCell>{e.last_seen_at ? relativeTime(e.last_seen_at) : "—"}</TableCell>
                  <TableCell>{e.subsystem}</TableCell>
                  <TableCell>
                    <Badge variant={e.severity === "critical" ? "destructive" : "warning"}>
                      {e.severity}
                    </Badge>
                  </TableCell>
                  <TableCell>{titleCase(e.error_type)}</TableCell>
                  <TableCell className="max-w-md text-xs text-muted-foreground">{e.message}</TableCell>
                  <TableCell className="text-xs">{e.tenants.join(", ") || e.tenant_count}</TableCell>
                  <TableCell className="tabular-nums">{e.count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
