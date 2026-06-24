"use client";

import { useState } from "react";
import {
  CloudLightning,
  FlaskConical,
  Factory,
  Play,
  Ship,
  TrendingUp,
  Warehouse as WarehouseIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import type {
  Simulation,
  SimulationResult,
  SimulationType,
  Supplier,
  Warehouse,
} from "@/lib/types";
import { formatCurrency, formatPercent, titleCase } from "@/lib/format";
import { CHART_COLORS } from "@/lib/constants";
import { PageHeader } from "@/components/shared/page-header";
import { AreaTrend } from "@/components/charts/charts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const SCENARIOS: { value: SimulationType; label: string; icon: typeof Ship; desc: string }[] = [
  { value: "supplier_shutdown", label: "Supplier Shutdown", icon: Factory, desc: "A key supplier goes offline" },
  { value: "port_closure", label: "Port Closure", icon: Ship, desc: "A major port closes" },
  { value: "warehouse_outage", label: "Warehouse Outage", icon: WarehouseIcon, desc: "A distribution center goes down" },
  { value: "demand_spike", label: "Demand Spike", icon: TrendingUp, desc: "Sudden surge in demand" },
  { value: "weather_disruption", label: "Weather Disruption", icon: CloudLightning, desc: "Severe weather event" },
];

export default function SimulatorPage() {
  const { data: suppliers } = useFetch<Supplier[]>("/suppliers?sort_by=supplier_score&sort_dir=asc");
  const { data: warehouses } = useFetch<Warehouse[]>("/inventory/warehouses");
  const { data: recent, refetch } = useFetch<Simulation[]>("/simulations?limit=8");

  const [type, setType] = useState<SimulationType>("supplier_shutdown");
  const [supplierId, setSupplierId] = useState<string>("auto");
  const [warehouseId, setWarehouseId] = useState<string>("auto");
  const [region, setRegion] = useState("APAC");
  const [severity, setSeverity] = useState(0.7);
  const [duration, setDuration] = useState(21);
  const [demandMult, setDemandMult] = useState(1.8);

  const [result, setResult] = useState<SimulationResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setRunning(true);
    setError("");
    try {
      const body: Record<string, unknown> = {
        simulation_type: type,
        severity,
        duration_days: duration,
        demand_multiplier: demandMult,
      };
      if (type === "supplier_shutdown" && supplierId !== "auto") body.supplier_id = Number(supplierId);
      if (type === "warehouse_outage" && warehouseId !== "auto") body.warehouse_id = Number(warehouseId);
      if (type === "port_closure" || type === "weather_disruption") body.region = region;
      const sim = await api.post<Simulation>("/simulations/run", body);
      setResult(sim.results);
      refetch();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Simulation Center"
        description="Stress-test the network against disruptions and quantify inventory, shipment and revenue impact with mitigation playbooks."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Configuration */}
        <Card className="lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <FlaskConical className="h-4 w-4" /> Configure Scenario
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-2">
              {SCENARIOS.map((s) => {
                const Icon = s.icon;
                const active = type === s.value;
                return (
                  <button
                    key={s.value}
                    onClick={() => setType(s.value)}
                    className={`rounded-lg border p-3 text-left transition-colors ${
                      active ? "border-primary bg-primary/10" : "border-border hover:bg-accent"
                    }`}
                  >
                    <Icon className={`h-5 w-5 ${active ? "text-primary" : "text-muted-foreground"}`} />
                    <p className="mt-2 text-xs font-medium leading-tight">{s.label}</p>
                  </button>
                );
              })}
            </div>

            {type === "supplier_shutdown" && (
              <div className="space-y-1.5">
                <Label>Supplier</Label>
                <Select value={supplierId} onValueChange={setSupplierId}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto (weakest supplier)</SelectItem>
                    {suppliers?.slice(0, 30).map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>
                        {s.name} ({s.supplier_score.toFixed(0)})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {type === "warehouse_outage" && (
              <div className="space-y-1.5">
                <Label>Warehouse</Label>
                <Select value={warehouseId} onValueChange={setWarehouseId}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto (busiest warehouse)</SelectItem>
                    {warehouses?.slice(0, 30).map((w) => (
                      <SelectItem key={w.id} value={String(w.id)}>
                        {w.name} ({w.utilization.toFixed(0)}%)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {(type === "port_closure" || type === "weather_disruption") && (
              <div className="space-y-1.5">
                <Label>Region</Label>
                <Select value={region} onValueChange={setRegion}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {["APAC", "Europe", "North America", "LATAM", "Middle East", "Africa"].map((r) => (
                      <SelectItem key={r} value={r}>
                        {r}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {type === "demand_spike" && (
              <div className="space-y-1.5">
                <Label>Demand Multiplier: {demandMult.toFixed(1)}x</Label>
                <input
                  type="range"
                  min={1}
                  max={4}
                  step={0.1}
                  value={demandMult}
                  onChange={(e) => setDemandMult(Number(e.target.value))}
                  className="w-full accent-[hsl(var(--primary))]"
                />
              </div>
            )}

            <div className="space-y-1.5">
              <Label>Severity: {formatPercent(severity * 100, 0)}</Label>
              <input
                type="range"
                min={0.1}
                max={1}
                step={0.05}
                value={severity}
                onChange={(e) => setSeverity(Number(e.target.value))}
                className="w-full accent-[hsl(var(--primary))]"
              />
            </div>

            <div className="space-y-1.5">
              <Label>Duration: {duration} days</Label>
              <input
                type="range"
                min={1}
                max={90}
                step={1}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="w-full accent-[hsl(var(--primary))]"
              />
            </div>

            <Button onClick={run} disabled={running} className="w-full">
              <Play className="h-4 w-4" />
              {running ? "Running simulation…" : "Run simulation"}
            </Button>
            {error && <p className="text-xs text-destructive">{error}</p>}
          </CardContent>
        </Card>

        {/* Results */}
        <div className="space-y-4 lg:col-span-2">
          {!result ? (
            <Card className="flex h-full min-h-[300px] flex-col items-center justify-center p-8 text-center">
              <FlaskConical className="h-10 w-10 text-muted-foreground/40" />
              <p className="mt-3 text-sm font-medium">Configure and run a scenario</p>
              <p className="mt-1 max-w-sm text-xs text-muted-foreground">
                Results show projected inventory, shipment and revenue impact plus a recommended
                mitigation playbook.
              </p>
            </Card>
          ) : (
            <>
              <Card className="surface-raised radial-fade">
                <CardContent className="pt-5">
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 text-primary">
                      <FlaskConical className="h-4 w-4" />
                    </span>
                    <p className="section-label">Executive Impact Summary · {result.scenario}</p>
                  </div>
                  <p className="mt-2 text-base font-medium leading-snug tracking-tight">{result.summary}</p>
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <ImpactCard label="Inventory Impact" value={formatPercent(result.impacts.inventory_impact_pct, 0)} intent="warning" />
                <ImpactCard label="Shipment Impact" value={formatPercent(result.impacts.shipment_impact_pct, 0)} intent="danger" />
                <ImpactCard label="Revenue at Risk" value={formatCurrency(result.impacts.revenue_impact_usd, true)} intent="danger" />
              </div>

              {result.timeline.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Projected Impact Over Time</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <AreaTrend
                      data={result.timeline}
                      xKey="day"
                      height={200}
                      showLegend={false}
                      series={[{ key: "impact", name: "Impact %", color: CHART_COLORS.red }]}
                    />
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Recommended Mitigations</CardTitle>
                </CardHeader>
                <CardContent>
                  <ol className="space-y-2">
                    {result.mitigations.map((m, i) => (
                      <li key={i} className="flex gap-3 text-sm">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success/15 text-xs font-semibold text-success">
                          {i + 1}
                        </span>
                        {m}
                      </li>
                    ))}
                  </ol>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>

      {recent && recent.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Recent Simulations</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {recent.map((s) => (
              <button
                key={s.id}
                onClick={() => setResult(s.results)}
                className="rounded-lg border border-border/60 p-3 text-left transition-colors hover:bg-accent"
              >
                <p className="text-xs font-medium">{titleCase(s.simulation_type)}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Revenue at risk: {formatCurrency(s.revenue_impact_usd, true)}
                </p>
              </button>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ImpactCard({
  label,
  value,
  intent,
}: {
  label: string;
  value: string;
  intent: "warning" | "danger";
}) {
  const color = intent === "danger" ? "text-destructive" : "text-warning";
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${color}`}>{value}</p>
    </Card>
  );
}
