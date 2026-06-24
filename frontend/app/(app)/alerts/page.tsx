"use client";

import { useEffect, useState } from "react";
import { Bell, BellRing, CheckCheck, CircleCheck } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import type { Alert, AlertStatus, Page } from "@/lib/types";
import { formatNumber, relativeTime, titleCase } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { PriorityBadge } from "@/components/shared/badges";
import { Pagination } from "@/components/shared/pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface AlertStats {
  open: number;
  acknowledged: number;
  resolved: number;
  by_priority: Record<string, number>;
  by_type: Record<string, number>;
}

const STATUS_VARIANT: Record<AlertStatus, "warning" | "default" | "success"> = {
  open: "warning",
  acknowledged: "default",
  resolved: "success",
};

export default function AlertsPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState("open");
  const [priority, setPriority] = useState("all");
  const [type, setType] = useState("all");
  const [page, setPage] = useState(1);

  useEffect(() => setPage(1), [status, priority, type]);

  const { data: stats, refetch: refetchStats } = useFetch<AlertStats>("/alerts/stats");

  const q = new URLSearchParams({ page: String(page), page_size: "12" });
  if (status !== "all") q.set("status", status);
  if (priority !== "all") q.set("priority", priority);
  if (type !== "all") q.set("alert_type", type);

  const { data, loading, error, refetch } = useFetch<Page<Alert>>(`/alerts?${q.toString()}`, [
    page,
    status,
    priority,
    type,
  ]);

  const canManage =
    user?.role === "admin" || user?.role === "operations_manager" || user?.role === "analyst";

  async function update(id: number, newStatus: AlertStatus) {
    await api.patch(`/alerts/${id}`, {
      status: newStatus,
      resolution_note: newStatus === "resolved" ? "Resolved from Alert Center" : undefined,
    });
    refetch();
    refetchStats();
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Alert Center"
        description="Prioritized operational alerts with resolution tracking and history."
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile icon={BellRing} label="Open" value={formatNumber(stats?.open ?? 0)} intent="warning" />
        <StatTile icon={Bell} label="Acknowledged" value={formatNumber(stats?.acknowledged ?? 0)} intent="default" />
        <StatTile icon={CircleCheck} label="Resolved" value={formatNumber(stats?.resolved ?? 0)} intent="success" />
        <StatTile
          icon={BellRing}
          label="Critical Open"
          value={formatNumber(stats?.by_priority?.critical ?? 0)}
          intent="danger"
        />
      </div>

      <Card>
        <CardContent className="space-y-4 pt-5">
          <div className="flex flex-wrap gap-2">
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="acknowledged">Acknowledged</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
              </SelectContent>
            </Select>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger className="w-36"><SelectValue placeholder="Priority" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All priorities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger className="w-52"><SelectValue placeholder="Type" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                <SelectItem value="delayed_shipment">Delayed Shipment</SelectItem>
                <SelectItem value="inventory_stockout_risk">Stockout Risk</SelectItem>
                <SelectItem value="supplier_failure_risk">Supplier Failure</SelectItem>
                <SelectItem value="forecasted_demand_spike">Demand Spike</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error} />
          ) : !data || data.items.length === 0 ? (
            <EmptyState message="No alerts match your filters." />
          ) : (
            <>
              <div className="space-y-3">
                {data.items.map((a) => (
                  <div key={a.id} className="rounded-lg border border-border/60 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <PriorityBadge priority={a.priority} />
                          <Badge variant={STATUS_VARIANT[a.status]}>{titleCase(a.status)}</Badge>
                          <span className="text-xs uppercase tracking-wide text-muted-foreground">
                            {titleCase(a.alert_type)}
                          </span>
                        </div>
                        <p className="mt-1.5 text-sm font-medium">{a.title}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">{a.message}</p>
                        <p className="mt-1.5 text-[11px] text-muted-foreground">{relativeTime(a.created_at)}</p>
                      </div>
                      {canManage && a.status !== "resolved" && (
                        <div className="flex shrink-0 gap-2">
                          {a.status === "open" && (
                            <Button variant="outline" size="sm" onClick={() => update(a.id, "acknowledged")}>
                              <CheckCheck className="h-4 w-4" /> Ack
                            </Button>
                          )}
                          <Button size="sm" onClick={() => update(a.id, "resolved")}>
                            <CircleCheck className="h-4 w-4" /> Resolve
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatTile({
  icon: Icon,
  label,
  value,
  intent,
}: {
  icon: typeof Bell;
  label: string;
  value: string;
  intent: "warning" | "default" | "success" | "danger";
}) {
  const colors = {
    warning: "text-warning bg-warning/10",
    default: "text-primary bg-primary/10",
    success: "text-success bg-success/10",
    danger: "text-destructive bg-destructive/10",
  };
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${colors[intent]}`}>
          <Icon className="h-4 w-4" />
        </span>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
          <p className="text-xl font-semibold tabular-nums">{value}</p>
        </div>
      </div>
    </Card>
  );
}
