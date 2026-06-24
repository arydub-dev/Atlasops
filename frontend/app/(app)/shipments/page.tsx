"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowUpDown, Search } from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import type { Page, Shipment, ShipmentStatus } from "@/lib/types";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { ShipmentStatusBadge } from "@/components/shared/badges";
import { Pagination } from "@/components/shared/pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";

const STATUSES: { value: string; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "in_transit", label: "In Transit" },
  { value: "delayed", label: "Delayed" },
  { value: "delivered", label: "Delivered" },
  { value: "at_warehouse", label: "At Warehouse" },
  { value: "customs_hold", label: "Customs Hold" },
];

function ShipmentsInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [debouncedQ, setDebouncedQ] = useState(q);
  const [status, setStatus] = useState("all");
  const [sortBy, setSortBy] = useState("eta");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => setPage(1), [debouncedQ, status, sortBy, sortDir]);

  const query = new URLSearchParams({
    page: String(page),
    page_size: "20",
    sort_by: sortBy,
    sort_dir: sortDir,
  });
  if (debouncedQ) query.set("q", debouncedQ);
  if (status !== "all") query.set("status", status);

  const { data, loading, error } = useFetch<Page<Shipment>>(`/shipments?${query.toString()}`, [
    page,
    debouncedQ,
    status,
    sortBy,
    sortDir,
  ]);

  function toggleSort(field: string) {
    if (sortBy === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortDir("asc");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Shipment Management"
        description="Track, search and manage every shipment across your network."
      />

      <Card>
        <CardContent className="space-y-4 pt-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search reference, origin, destination, carrier, location…"
                className="pl-9"
              />
            </div>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUSES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={sortBy} onValueChange={(v) => toggleSort(v)}>
              <SelectTrigger className="w-full sm:w-44">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="eta">Sort: ETA</SelectItem>
                <SelectItem value="delay_risk_score">Sort: Risk</SelectItem>
                <SelectItem value="value_usd">Sort: Value</SelectItem>
                <SelectItem value="delay_days">Sort: Delay</SelectItem>
                <SelectItem value="reference">Sort: Reference</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error} />
          ) : !data || data.items.length === 0 ? (
            <EmptyState message="No shipments match your filters." />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>
                      <button className="flex items-center gap-1" onClick={() => toggleSort("reference")}>
                        Reference <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </TableHead>
                    <TableHead>Route</TableHead>
                    <TableHead>Carrier</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-36">
                      <button className="flex items-center gap-1" onClick={() => toggleSort("delay_risk_score")}>
                        Delay Risk <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </TableHead>
                    <TableHead>
                      <button className="flex items-center gap-1" onClick={() => toggleSort("eta")}>
                        ETA <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </TableHead>
                    <TableHead className="text-right">
                      <button className="ml-auto flex items-center gap-1" onClick={() => toggleSort("value_usd")}>
                        Value <ArrowUpDown className="h-3 w-3" />
                      </button>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((s) => (
                    <TableRow
                      key={s.id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/shipments/${s.id}`)}
                    >
                      <TableCell className="font-mono text-xs font-medium">{s.reference}</TableCell>
                      <TableCell className="text-sm">
                        <span className="font-medium">{s.origin}</span>
                        <span className="text-muted-foreground"> → {s.destination}</span>
                        <span className="block text-xs text-muted-foreground">@ {s.current_location}</span>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{s.carrier}</TableCell>
                      <TableCell><ShipmentStatusBadge status={s.status} /></TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress
                            value={s.delay_risk_score}
                            className="h-1.5 w-16"
                            indicatorClassName={
                              s.delay_risk_score >= 60
                                ? "bg-destructive"
                                : s.delay_risk_score >= 35
                                  ? "bg-warning"
                                  : "bg-success"
                            }
                          />
                          <span className="font-mono text-xs tabular-nums">{s.delay_risk_score.toFixed(0)}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">{formatDate(s.eta)}</TableCell>
                      <TableCell className="text-right font-mono text-sm tabular-nums">
                        {formatCurrency(s.value_usd, true)}
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

export default function ShipmentsPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <ShipmentsInner />
    </Suspense>
  );
}
