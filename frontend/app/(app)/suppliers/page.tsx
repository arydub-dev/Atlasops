"use client";

import { useState } from "react";
import { Award, Factory, Star } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import type { SupplierScorecard } from "@/lib/types";
import { formatPercent, titleCase } from "@/lib/format";
import { CHART_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { LineTrend } from "@/components/charts/charts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function scoreColor(score: number) {
  if (score >= 85) return "text-success";
  if (score >= 65) return "text-warning";
  return "text-destructive";
}

export default function SuppliersPage() {
  const { data, loading, error } = useFetch<SupplierScorecard[]>("/suppliers/ranking?limit=50");
  const [selected, setSelected] = useState<SupplierScorecard | null>(null);
  const [loadingCard, setLoadingCard] = useState(false);

  async function openScorecard(id: number) {
    setLoadingCard(true);
    try {
      const card = await api.get<SupplierScorecard>(`/suppliers/${id}/scorecard`);
      setSelected(card);
    } finally {
      setLoadingCard(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error || "Failed to load suppliers"} />;

  const top3 = data.slice(0, 3);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Supplier Intelligence"
        description="Rank, score and compare supplier performance across reliability, delays and quality."
      />

      {/* Top performers */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {top3.map((s, i) => (
          <Card key={s.id} className="cursor-pointer transition-shadow hover:shadow-md" onClick={() => openScorecard(s.id)}>
            <CardContent className="pt-5">
              <div className="flex items-center justify-between">
                <Badge variant={i === 0 ? "success" : "secondary"} className="gap-1">
                  <Award className="h-3 w-3" /> Rank #{s.rank}
                </Badge>
                <span className={cn("font-mono text-2xl font-semibold", scoreColor(s.supplier_score))}>
                  {s.supplier_score.toFixed(0)}
                </span>
              </div>
              <p className="mt-3 font-medium">{s.name}</p>
              <p className="text-xs text-muted-foreground">{s.country} · {s.category}</p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <Metric label="Reliability" value={formatPercent(s.delivery_reliability, 0)} />
                <Metric label="On-time" value={formatPercent(s.on_time_rate, 0)} />
                <Metric label="Avg delay" value={`${s.average_delay_days.toFixed(1)}d`} />
                <Metric label="Defects" value={formatPercent(s.defect_rate, 1)} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Factory className="h-4 w-4" /> Supplier Ranking
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-14">Rank</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Region</TableHead>
                <TableHead className="w-40">Score</TableHead>
                <TableHead className="text-right">Reliability</TableHead>
                <TableHead className="text-right">On-time</TableHead>
                <TableHead className="text-right">Avg Delay</TableHead>
                <TableHead className="text-right">Defects</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((s) => (
                <TableRow key={s.id} className="cursor-pointer" onClick={() => openScorecard(s.id)}>
                  <TableCell className="font-mono font-semibold">#{s.rank}</TableCell>
                  <TableCell>
                    <p className="text-sm font-medium">{s.name}</p>
                    <p className="text-xs text-muted-foreground">{s.category}</p>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{s.region}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress
                        value={s.supplier_score}
                        className="h-1.5 w-20"
                        indicatorClassName={
                          s.supplier_score >= 85 ? "bg-success" : s.supplier_score >= 65 ? "bg-warning" : "bg-destructive"
                        }
                      />
                      <span className={cn("font-mono text-sm tabular-nums", scoreColor(s.supplier_score))}>
                        {s.supplier_score.toFixed(0)}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums">{formatPercent(s.delivery_reliability, 0)}</TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums">{formatPercent(s.on_time_rate, 0)}</TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums">{s.average_delay_days.toFixed(1)}d</TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums">{formatPercent(s.defect_rate, 1)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-2xl">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Star className="h-5 w-5 text-warning" /> {selected.name}
                </DialogTitle>
                <DialogDescription>
                  Rank #{selected.rank} · {selected.country} · {titleCase(selected.category)} · {selected.total_shipments} shipments
                </DialogDescription>
              </DialogHeader>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <ScoreTile label="Score" value={selected.supplier_score.toFixed(0)} color={scoreColor(selected.supplier_score)} />
                <ScoreTile label="Reliability" value={formatPercent(selected.delivery_reliability, 0)} />
                <ScoreTile label="On-time" value={formatPercent(selected.on_time_rate, 0)} />
                <ScoreTile label="Fulfillment" value={formatPercent(selected.order_fulfillment_rate, 0)} />
                <ScoreTile label="Avg Delay" value={`${selected.average_delay_days.toFixed(1)}d`} />
                <ScoreTile label="Defect Rate" value={formatPercent(selected.defect_rate, 1)} />
                <ScoreTile label="Shipments" value={String(selected.total_shipments)} />
                <ScoreTile label="Delayed" value={String(selected.delayed_shipments)} />
              </div>
              <div className="mt-2">
                <p className="mb-1 text-sm font-medium">6-Month Performance Trend</p>
                <LineTrend
                  data={selected.monthly_trend}
                  xKey="label"
                  height={200}
                  series={[
                    { key: "score", name: "Score", color: CHART_COLORS.violet },
                    { key: "reliability", name: "Reliability", color: CHART_COLORS.green },
                  ]}
                />
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {loadingCard && !selected && <LoadingState label="Loading scorecard…" />}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted/50 px-2 py-1.5">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="font-mono text-sm font-medium tabular-nums">{value}</p>
    </div>
  );
}

function ScoreTile({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border border-border/60 p-3 text-center">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={cn("mt-1 font-mono text-lg font-semibold tabular-nums", color)}>{value}</p>
    </div>
  );
}
