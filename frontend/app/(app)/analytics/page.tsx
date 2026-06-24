"use client";

import { useFetch } from "@/lib/use-fetch";
import { formatNumber, formatPercent } from "@/lib/format";
import { CHART_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/page-header";
import { LoadingState } from "@/components/shared/states";
import { ChartCard } from "@/components/charts/chart-card";
import { AreaTrend, BarTrend, Donut, HorizontalBars, LineTrend } from "@/components/charts/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics Hub"
        description="Deep-dive analytics across delivery, suppliers, inventory and demand forecasting."
      />
      <Tabs defaultValue="delivery">
        <TabsList className="flex-wrap">
          <TabsTrigger value="delivery">Delivery Performance</TabsTrigger>
          <TabsTrigger value="suppliers">Supplier Analytics</TabsTrigger>
          <TabsTrigger value="inventory">Inventory Analytics</TabsTrigger>
          <TabsTrigger value="forecast">Forecast Analytics</TabsTrigger>
        </TabsList>
        <TabsContent value="delivery"><DeliveryTab /></TabsContent>
        <TabsContent value="suppliers"><SupplierTab /></TabsContent>
        <TabsContent value="inventory"><InventoryTab /></TabsContent>
        <TabsContent value="forecast"><ForecastTab /></TabsContent>
      </Tabs>
    </div>
  );
}

function DeliveryTab() {
  const { data } = useFetch<{
    status_breakdown: Record<string, number>;
    shipment_trend: Record<string, unknown>[];
    delay_trend: Record<string, unknown>[];
    carrier_performance: { carrier: string; shipments: number; avg_delay_days: number }[];
  }>("/analytics/delivery");
  if (!data) return <LoadingState />;

  const statusDonut = Object.entries(data.status_breakdown).map(([k, v], i) => ({
    name: k.replace(/_/g, " "),
    value: v,
    color: Object.values(CHART_COLORS)[i + 1] ?? CHART_COLORS.slate,
  }));
  const carriers = data.carrier_performance
    .slice(0, 8)
    .map((c) => ({ name: c.carrier, value: Math.round(c.avg_delay_days * 10) / 10 }));

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard title="Shipment Volume Trend" description="Weekly shipped / delivered / delayed">
        <BarTrend
          data={data.shipment_trend}
          xKey="label"
          series={[
            { key: "shipped", name: "Shipped", color: CHART_COLORS.blue },
            { key: "delivered", name: "Delivered", color: CHART_COLORS.green },
            { key: "delayed", name: "Delayed", color: CHART_COLORS.red },
          ]}
        />
      </ChartCard>
      <ChartCard title="Status Breakdown" description="Current shipment mix">
        <Donut data={statusDonut} />
      </ChartCard>
      <ChartCard title="Delay Trend" description="Average delay days over time">
        <AreaTrend
          data={data.delay_trend}
          xKey="label"
          showLegend={false}
          series={[{ key: "avg_delay_days", name: "Avg Delay", color: CHART_COLORS.amber }]}
        />
      </ChartCard>
      <ChartCard title="Carrier Performance" description="Average delay days by carrier">
        <HorizontalBars data={carriers} color={CHART_COLORS.violet} />
      </ChartCard>
    </div>
  );
}

function SupplierTab() {
  const { data } = useFetch<{
    performance_trend: Record<string, unknown>[];
    by_region: { region: string; avg_score: number; avg_reliability: number; suppliers: number }[];
    top_performers: { name: string; score: number }[];
    bottom_performers: { name: string; score: number }[];
  }>("/analytics/suppliers");
  if (!data) return <LoadingState />;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard title="Supplier Performance Trend" description="Score & reliability over time" className="lg:col-span-2">
        <LineTrend
          data={data.performance_trend}
          xKey="label"
          series={[
            { key: "supplier_score", name: "Score", color: CHART_COLORS.violet },
            { key: "delivery_reliability", name: "Reliability", color: CHART_COLORS.green },
          ]}
        />
      </ChartCard>
      <ChartCard title="Performance by Region" description="Average supplier score">
        <HorizontalBars
          data={data.by_region.map((r) => ({ name: r.region, value: Math.round(r.avg_score) }))}
          color={CHART_COLORS.blue}
        />
      </ChartCard>
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Top & Bottom Performers</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-2 gap-4">
          <div>
            <p className="mb-2 text-xs font-medium text-success">Top 10</p>
            <ul className="space-y-1.5 text-sm">
              {data.top_performers.map((s) => (
                <li key={s.name} className="flex justify-between gap-2">
                  <span className="truncate text-muted-foreground">{s.name}</span>
                  <span className="font-mono tabular-nums text-success">{s.score.toFixed(0)}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium text-destructive">Bottom 10</p>
            <ul className="space-y-1.5 text-sm">
              {data.bottom_performers.map((s) => (
                <li key={s.name} className="flex justify-between gap-2">
                  <span className="truncate text-muted-foreground">{s.name}</span>
                  <span className="font-mono tabular-nums text-destructive">{s.score.toFixed(0)}</span>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function InventoryTab() {
  const { data } = useFetch<{
    health_breakdown: Record<string, number>;
    utilization_trend: Record<string, unknown>[];
    utilization_heatmap: { region: string; avg_utilization: number; warehouses: number }[];
    inventory_by_category: { category: string; units: number }[];
  }>("/analytics/inventory");
  if (!data) return <LoadingState />;

  const donut = [
    { name: "Healthy", value: data.health_breakdown.ok ?? 0, color: CHART_COLORS.green },
    { name: "Low Stock", value: data.health_breakdown.low_stock ?? 0, color: CHART_COLORS.amber },
    { name: "Overstock", value: data.health_breakdown.overstock ?? 0, color: CHART_COLORS.slate },
    { name: "Stockout", value: data.health_breakdown.stockout ?? 0, color: CHART_COLORS.red },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard title="Utilization Trend" description="Network utilization over time">
        <AreaTrend
          data={data.utilization_trend}
          xKey="label"
          showLegend={false}
          series={[{ key: "utilization", name: "Utilization %", color: CHART_COLORS.cyan }]}
        />
      </ChartCard>
      <ChartCard title="Inventory Health" description="Distribution of all stock lines">
        <Donut data={donut} />
      </ChartCard>
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Regional Utilization Heatmap</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {data.utilization_heatmap.map((h) => {
              const u = h.avg_utilization;
              const intensity =
                u >= 90 ? "bg-destructive/80 text-white"
                : u >= 80 ? "bg-warning/80 text-black"
                : u >= 50 ? "bg-success/70 text-white"
                : "bg-success/30";
              return (
                <div key={h.region} className={cn("rounded-lg p-3", intensity)}>
                  <p className="text-xs font-medium">{h.region}</p>
                  <p className="font-mono text-lg font-semibold tabular-nums">{formatPercent(u, 0)}</p>
                  <p className="text-[10px] opacity-80">{h.warehouses} warehouses</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
      <ChartCard title="Inventory by Category" description="Total units on hand">
        <HorizontalBars
          data={data.inventory_by_category.slice(0, 8).map((c) => ({ name: c.category, value: c.units }))}
          color={CHART_COLORS.blue}
        />
      </ChartCard>
    </div>
  );
}

function ForecastTab() {
  const { data } = useFetch<{
    history: Record<string, unknown>[];
    forecast: { label: string; projected_demand: number; lower: number; upper: number }[];
    avg_weekly_volume: number;
  }>("/analytics/forecast");
  if (!data) return <LoadingState />;

  const merged = [
    ...data.history.map((h) => ({ label: h.label, actual: h.shipped })),
    ...data.forecast.map((f) => ({
      label: f.label,
      projected: f.projected_demand,
      upper: f.upper,
      lower: f.lower,
    })),
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Avg Weekly Volume</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{formatNumber(data.avg_weekly_volume)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Forecast Horizon</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{data.forecast.length} wks</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Next Week Projection</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
            {formatNumber(data.forecast[0]?.projected_demand ?? 0)}
          </p>
        </Card>
      </div>
      <ChartCard title="Demand Forecast" description="Historical volume with projected demand & confidence band">
        <LineTrend
          data={merged}
          xKey="label"
          height={320}
          series={[
            { key: "actual", name: "Actual", color: CHART_COLORS.blue },
            { key: "projected", name: "Projected", color: CHART_COLORS.violet },
            { key: "upper", name: "Upper", color: CHART_COLORS.slate },
            { key: "lower", name: "Lower", color: CHART_COLORS.slate },
          ]}
        />
      </ChartCard>
    </div>
  );
}
