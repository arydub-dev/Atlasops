"use client";

import { useEffect, useState } from "react";
import { Boxes, PackageX, ShoppingCart, TriangleAlert } from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import type { InventoryItem, Page, Warehouse } from "@/lib/types";
import { formatNumber, formatPercent, titleCase } from "@/lib/format";
import { CHART_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/shared/pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { ChartCard } from "@/components/charts/chart-card";
import { Donut } from "@/components/charts/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "muted"> = {
  ok: "success",
  low_stock: "warning",
  overstock: "muted",
  stockout: "destructive",
};

const RISK_DOT: Record<string, string> = {
  low: "bg-success",
  medium: "bg-warning",
  high: "bg-destructive",
};

export default function InventoryPage() {
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [status, setStatus] = useState("all");
  const [warehouse, setWarehouse] = useState("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(t);
  }, [q]);
  useEffect(() => setPage(1), [debouncedQ, status, warehouse]);

  const { data: warehouses } = useFetch<Warehouse[]>("/inventory/warehouses");
  const { data: health } = useFetch<Record<string, number>>("/inventory/health");

  const query = new URLSearchParams({ page: String(page), page_size: "15" });
  if (debouncedQ) query.set("q", debouncedQ);
  if (status !== "all") query.set("status", status);
  if (warehouse !== "all") query.set("warehouse_id", warehouse);

  const { data, loading, error } = useFetch<Page<InventoryItem>>(
    `/inventory/items?${query.toString()}`,
    [page, debouncedQ, status, warehouse]
  );

  const healthData = health
    ? [
        { name: "Healthy", value: health.ok ?? 0, color: CHART_COLORS.green },
        { name: "Low Stock", value: health.low_stock ?? 0, color: CHART_COLORS.amber },
        { name: "Overstock", value: health.overstock ?? 0, color: CHART_COLORS.slate },
        { name: "Stockout", value: health.stockout ?? 0, color: CHART_COLORS.red },
      ]
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Inventory Intelligence"
        description="Monitor stock health, detect stockouts and overstock, and act on reorder signals."
      />

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <SummaryCard icon={Boxes} label="Healthy Lines" value={formatNumber(health?.ok ?? 0)} intent="success" />
        <SummaryCard icon={TriangleAlert} label="Low Stock" value={formatNumber(health?.low_stock ?? 0)} intent="warning" />
        <SummaryCard icon={PackageX} label="Stockouts" value={formatNumber(health?.stockout ?? 0)} intent="danger" />
        <SummaryCard icon={ShoppingCart} label="Overstock" value={formatNumber(health?.overstock ?? 0)} intent="muted" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard title="Inventory Health" description="Distribution of all stock lines" className="lg:col-span-1">
          {healthData.length ? <Donut data={healthData} /> : <LoadingState />}
        </ChartCard>

        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Warehouse Network</CardTitle>
          </CardHeader>
          <CardContent>
            {!warehouses ? (
              <LoadingState />
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {warehouses.slice(0, 8).map((w) => (
                  <div key={w.id} className="rounded-lg border border-border/60 p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={cn("h-2.5 w-2.5 rounded-full", RISK_DOT[w.risk_level])} />
                        <p className="text-sm font-medium">{w.name}</p>
                      </div>
                      <Badge variant="outline">{titleCase(w.risk_level)}</Badge>
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">{w.location} · {w.region}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <Progress
                        value={w.utilization}
                        className="h-1.5"
                        indicatorClassName={
                          w.utilization >= 90
                            ? "bg-destructive"
                            : w.utilization >= 80
                              ? "bg-warning"
                              : "bg-success"
                        }
                      />
                      <span className="font-mono text-xs tabular-nums">{formatPercent(w.utilization, 0)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Inventory table */}
      <Card>
        <CardContent className="space-y-4 pt-5">
          <div className="flex flex-col gap-3 sm:flex-row">
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search product name or SKU…"
              className="flex-1"
            />
            <Select value={warehouse} onValueChange={setWarehouse}>
              <SelectTrigger className="w-full sm:w-52">
                <SelectValue placeholder="Warehouse" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All warehouses</SelectItem>
                {warehouses?.map((w) => (
                  <SelectItem key={w.id} value={String(w.id)}>
                    {w.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-full sm:w-44">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="ok">Healthy</SelectItem>
                <SelectItem value="low_stock">Low Stock</SelectItem>
                <SelectItem value="stockout">Stockout</SelectItem>
                <SelectItem value="overstock">Overstock</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error} />
          ) : !data || data.items.length === 0 ? (
            <EmptyState message="No inventory lines match your filters." />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Product</TableHead>
                    <TableHead>Warehouse</TableHead>
                    <TableHead className="text-right">On Hand</TableHead>
                    <TableHead className="text-right">Reorder Pt</TableHead>
                    <TableHead className="text-right">Days Supply</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Reorder Qty</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((it) => (
                    <TableRow key={it.id}>
                      <TableCell>
                        <p className="text-sm font-medium">{it.product_name}</p>
                        <p className="font-mono text-xs text-muted-foreground">{it.product_sku}</p>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{it.warehouse_name}</TableCell>
                      <TableCell className="text-right font-mono text-sm tabular-nums">{formatNumber(it.quantity)}</TableCell>
                      <TableCell className="text-right font-mono text-sm tabular-nums text-muted-foreground">{formatNumber(it.reorder_point)}</TableCell>
                      <TableCell className="text-right font-mono text-sm tabular-nums">{it.days_of_supply > 900 ? "∞" : it.days_of_supply}</TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANT[it.status]}>{titleCase(it.status)}</Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm tabular-nums">
                        {it.reorder_recommendation > 0 ? (
                          <span className="font-semibold text-primary">+{formatNumber(it.reorder_recommendation)}</span>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Pagination page={data.page} pages={data.pages} total={data.total} onPage={setPage} />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function SummaryCard({
  icon: Icon,
  label,
  value,
  intent,
}: {
  icon: typeof Boxes;
  label: string;
  value: string;
  intent: "success" | "warning" | "danger" | "muted";
}) {
  const colors = {
    success: "text-success bg-success/10",
    warning: "text-warning bg-warning/10",
    danger: "text-destructive bg-destructive/10",
    muted: "text-muted-foreground bg-muted",
  };
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", colors[intent])}>
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
