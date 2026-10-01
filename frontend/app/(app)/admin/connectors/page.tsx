"use client";

import Link from "next/link";
import { useFetch } from "@/lib/use-fetch";
import { relativeTime, titleCase } from "@/lib/format";
import { healthBadgeVariant, type ConnectorRow } from "@/lib/admin-console";
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

export default function AdminConnectorsPage() {
  const { data, loading, error, refetch } = useFetch<{ items: ConnectorRow[] }>("/admin/connectors");

  if (loading) return <LoadingState label="Loading connectors…" />;
  if (error) return <ErrorState message={error} onRetry={refetch} />;
  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader title="Connector health" description="Cross-tenant connector status. Secrets are never returned.">
        <Button variant="outline" size="sm" asChild>
          <Link href="/admin">Dashboard</Link>
        </Button>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          Refresh
        </Button>
      </PageHeader>
      {items.length === 0 ? (
        <EmptyState title="No connectors" message="No tenant connectors are registered." />
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Connector</TableHead>
                <TableHead>Tenant</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last sync</TableHead>
                <TableHead>Next sync</TableHead>
                <TableHead>Last error</TableHead>
                <TableHead>Retries</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>
                    <p className="font-medium">{c.name}</p>
                    <p className="text-xs text-muted-foreground">{c.connector_type}</p>
                  </TableCell>
                  <TableCell>
                    <Link href={`/admin/tenants/${c.organization_id}`} className="hover:underline">
                      {c.organization_name || c.organization_id.slice(0, 8)}
                    </Link>
                  </TableCell>
                  <TableCell>
                  <Badge variant={healthBadgeVariant(c.status)}>
                    {c.status === "failed" ? "Critical" : titleCase(c.status)}
                  </Badge>
                  </TableCell>
                  <TableCell>{c.last_successful_sync_at ? relativeTime(c.last_successful_sync_at) : "—"}</TableCell>
                  <TableCell>{c.next_sync_at ? relativeTime(c.next_sync_at) : "—"}</TableCell>
                  <TableCell className="max-w-sm text-xs text-muted-foreground">
                    {c.last_error ? (
                      <>
                        {c.last_error}
                        <p>{titleCase(c.failure_class)}</p>
                      </>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell className="tabular-nums">{c.retry_count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
