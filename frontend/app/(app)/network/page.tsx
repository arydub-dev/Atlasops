"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Activity,
  Factory,
  Minus,
  Plus,
  Maximize2,
  ShieldAlert,
  Warehouse,
  X,
} from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import { useDemoMode } from "@/lib/demo-mode";
import { WORLD_FEATURES, type LandGeometry } from "@/lib/world-map";
import type { NetworkData, NetworkNode } from "@/lib/types";
import { formatNumber, formatPercent } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/states";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const W = 1000;
const H = 480;

function project(lat: number, lon: number): [number, number] {
  const x = ((lon + 180) / 360) * W;
  const y = ((90 - lat) / 180) * H;
  return [x, y];
}

// Build an SVG path from a GeoJSON ring, breaking the line where a polygon
// crosses the antimeridian so it doesn't draw a seam across the whole map.
function ringToPath(ring: [number, number][]): string {
  let d = "";
  let prevLon: number | null = null;
  for (let i = 0; i < ring.length; i++) {
    const [lon, lat] = ring[i];
    const [x, y] = project(lat, lon);
    const cmd =
      i === 0 || (prevLon !== null && Math.abs(lon - prevLon) > 180) ? "M" : "L";
    d += `${cmd}${x.toFixed(1)} ${y.toFixed(1)}`;
    prevLon = lon;
  }
  return d;
}

function geometryToPath(geom: LandGeometry | null): string {
  if (!geom) return "";
  if (geom.type === "Polygon") return geom.coordinates.map(ringToPath).join("");
  if (geom.type === "MultiPolygon")
    return geom.coordinates.map((poly) => poly.map(ringToPath).join("")).join("");
  return "";
}

// Precompute landmass paths once — these never change.
const WORLD_PATHS: string[] = WORLD_FEATURES.map((f) =>
  geometryToPath(f.geometry),
).filter(Boolean);

function routeColor(rate: number): string {
  if (rate >= 40) return "#ef4444";
  if (rate >= 20) return "#f59e0b";
  return "#22c55e";
}

function riskColor(score: number): string {
  if (score >= 70) return "#ef4444";
  if (score >= 45) return "#f59e0b";
  return "#22c55e";
}

export default function NetworkPage() {
  const { enabled: demo } = useDemoMode();
  const { data, loading, error } = useFetch<NetworkData>("/network", [demo]);

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [selected, setSelected] = useState<NetworkNode | null>(null);
  const [showSuppliers, setShowSuppliers] = useState(true);
  const [showRoutes, setShowRoutes] = useState(true);
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);

  const nodes = data?.nodes ?? [];
  const edges = data?.edges ?? [];

  const visibleNodes = useMemo(
    () => (showSuppliers ? nodes : nodes.filter((n) => n.type === "warehouse")),
    [nodes, showSuppliers]
  );

  function onWheel(e: React.WheelEvent) {
    e.preventDefault();
    setZoom((z) => Math.min(6, Math.max(0.8, z - e.deltaY * 0.0015)));
  }
  function onDown(e: React.MouseEvent) {
    drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
  }
  function onMove(e: React.MouseEvent) {
    if (!drag.current) return;
    setPan({
      x: drag.current.px + (e.clientX - drag.current.x),
      y: drag.current.py + (e.clientY - drag.current.y),
    });
  }
  function onUp() {
    drag.current = null;
  }
  function reset() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Network View" description="Global supply chain topology — warehouses, suppliers and active routes." />
        <Skeleton className="shimmer h-[540px] w-full rounded-xl" />
      </div>
    );
  }
  if (error || !data) return <ErrorState message={error || "Failed to load network"} />;

  return (
    <div className="space-y-6">
      <PageHeader title="Network View" description="Global supply chain topology — warehouses, suppliers and active routes.">
        <Badge variant="secondary">{data.summary.warehouses} warehouses</Badge>
        <Badge variant="secondary">{data.summary.suppliers} suppliers</Badge>
        <Badge variant="secondary">{data.summary.active_routes} routes</Badge>
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Map */}
        <Card className="relative overflow-hidden lg:col-span-9">
          {/* Controls */}
          <div className="absolute right-3 top-3 z-20 flex flex-col gap-1.5">
            <ControlBtn onClick={() => setZoom((z) => Math.min(6, z + 0.4))}><Plus className="h-4 w-4" /></ControlBtn>
            <ControlBtn onClick={() => setZoom((z) => Math.max(0.8, z - 0.4))}><Minus className="h-4 w-4" /></ControlBtn>
            <ControlBtn onClick={reset}><Maximize2 className="h-4 w-4" /></ControlBtn>
          </div>

          {/* Toggles + legend */}
          <div className="absolute left-3 top-3 z-20 flex flex-wrap gap-1.5">
            <Toggle active={showRoutes} onClick={() => setShowRoutes((v) => !v)}>Routes</Toggle>
            <Toggle active={showSuppliers} onClick={() => setShowSuppliers((v) => !v)}>Suppliers</Toggle>
          </div>
          <div className="absolute bottom-3 left-3 z-20 flex flex-wrap items-center gap-3 rounded-lg border border-border/60 bg-background/80 px-3 py-1.5 text-[11px] backdrop-blur">
            <LegendDot color="#22c55e" label="Low risk" />
            <LegendDot color="#f59e0b" label="Elevated" />
            <LegendDot color="#ef4444" label="High risk" />
            <span className="text-muted-foreground">· scroll to zoom · drag to pan</span>
          </div>

          <div
            className="grid-bg h-[540px] w-full cursor-grab active:cursor-grabbing"
            onWheel={onWheel}
            onMouseDown={onDown}
            onMouseMove={onMove}
            onMouseUp={onUp}
            onMouseLeave={onUp}
          >
            <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" preserveAspectRatio="xMidYMid meet">
              <defs>
                <radialGradient id="hot" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity="0.5" />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
                </radialGradient>
              </defs>
              <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
                {/* graticule */}
                {[...Array(11)].map((_, i) => (
                  <line key={`v${i}`} x1={(i * W) / 10} y1={0} x2={(i * W) / 10} y2={H} stroke="hsl(var(--border))" strokeWidth={0.4} opacity={0.4} />
                ))}
                {[...Array(7)].map((_, i) => (
                  <line key={`h${i}`} x1={0} y1={(i * H) / 6} x2={W} y2={(i * H) / 6} stroke="hsl(var(--border))" strokeWidth={0.4} opacity={0.4} />
                ))}

                {/* world landmasses */}
                <g>
                  {WORLD_PATHS.map((d, i) => (
                    <path
                      key={`land${i}`}
                      d={d}
                      fill="hsl(var(--foreground))"
                      fillOpacity={0.06}
                      stroke="hsl(var(--foreground))"
                      strokeOpacity={0.14}
                      strokeWidth={0.5 / zoom}
                      strokeLinejoin="round"
                    />
                  ))}
                </g>

                {/* delay hotspots */}
                {data.hotspots.map((h, i) => {
                  if (!h.coords) return null;
                  const [x, y] = project(h.coords[0], h.coords[1]);
                  const r = 14 + Math.min(26, h.delayed);
                  return <circle key={`hs${i}`} cx={x} cy={y} r={r} fill="url(#hot)" className="animate-pulse" />;
                })}

                {/* routes */}
                {showRoutes &&
                  edges.map((e, i) => {
                    const [x1, y1] = project(e.from.lat, e.from.lon);
                    const [x2, y2] = project(e.to.lat, e.to.lon);
                    const mx = (x1 + x2) / 2;
                    const my = (y1 + y2) / 2 - Math.abs(x2 - x1) * 0.12 - 8;
                    return (
                      <path
                        key={`e${i}`}
                        d={`M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`}
                        fill="none"
                        stroke={routeColor(e.delay_rate)}
                        strokeWidth={Math.max(0.4, Math.min(2.2, e.volume / 12)) / zoom}
                        strokeOpacity={0.4}
                      />
                    );
                  })}

                {/* nodes */}
                {visibleNodes.map((n) => {
                  const [x, y] = project(n.lat, n.lon);
                  const isWh = n.type === "warehouse";
                  const c = riskColor(n.risk_score);
                  const sel = selected?.id === n.id;
                  const size = (isWh ? 5 : 3.5) / Math.sqrt(zoom);
                  return (
                    <g
                      key={n.id}
                      transform={`translate(${x} ${y})`}
                      className="cursor-pointer"
                      onClick={(ev) => {
                        ev.stopPropagation();
                        setSelected(n);
                      }}
                    >
                      {sel && <circle r={size + 5} fill="none" stroke={c} strokeWidth={1 / zoom} opacity={0.8} />}
                      {isWh ? (
                        <rect x={-size} y={-size} width={size * 2} height={size * 2} rx={1.2} fill={c} stroke="hsl(var(--background))" strokeWidth={0.8 / zoom} />
                      ) : (
                        <circle r={size} fill="hsl(var(--background))" stroke={c} strokeWidth={1.4 / zoom} />
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>
        </Card>

        {/* Detail panel */}
        <div className="lg:col-span-3">
          {selected ? (
            <NodeDetail node={selected} onClose={() => setSelected(null)} />
          ) : (
            <Card className="flex h-full min-h-[280px] flex-col items-center justify-center p-6 text-center">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                <Activity className="h-5 w-5" />
              </div>
              <p className="mt-3 text-sm font-medium">Select a node</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Click any warehouse (square) or supplier (circle) to inspect its risk, capacity,
                active shipments and related alerts.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function NodeDetail({ node, onClose }: { node: NetworkNode; onClose: () => void }) {
  const isWh = node.type === "warehouse";
  return (
    <Card className="surface-raised">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
        <div className="flex items-start gap-2.5">
          <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", isWh ? "bg-primary/15 text-primary" : "bg-violet-500/15 text-violet-500")}>
            {isWh ? <Warehouse className="h-5 w-5" /> : <Factory className="h-5 w-5" />}
          </span>
          <div>
            <CardTitle className="text-sm leading-tight">{node.name}</CardTitle>
            <p className="text-xs text-muted-foreground">{node.location} · {node.region}</p>
          </div>
        </div>
        <button onClick={onClose} className="rounded p-1 text-muted-foreground hover:bg-accent">
          <X className="h-4 w-4" />
        </button>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <Metric label="Risk Score" value={node.risk_score.toFixed(0)} accent={riskColor(node.risk_score)} />
        {isWh ? (
          <>
            <Metric label="Capacity" value={formatNumber(node.capacity ?? 0)} />
            <Metric label="Utilization" value={formatPercent(node.utilization ?? 0, 0)} />
            <Metric label="On Hand" value={formatNumber(node.current_inventory ?? 0)} />
            <Metric label="Active Shipments" value={formatNumber(node.active_shipments)} />
            <Metric label="Related Alerts" value={formatNumber(node.open_alerts ?? 0)} />
          </>
        ) : (
          <>
            <Metric label="Supplier Score" value={(node.supplier_score ?? 0).toFixed(0)} />
            <Metric label="Active Shipments" value={formatNumber(node.active_shipments)} />
          </>
        )}
        <div className="flex gap-2 pt-1">
          <Link href={isWh ? "/warehouses" : "/suppliers"} className="flex-1">
            <Button variant="outline" size="sm" className="w-full">
              {isWh ? "Warehouses" : "Suppliers"}
            </Button>
          </Link>
          <Link href="/alerts" className="flex-1">
            <Button variant="outline" size="sm" className="w-full">
              <ShieldAlert className="h-3.5 w-3.5" /> Alerts
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border/40 pb-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono font-semibold tabular-nums" style={accent ? { color: accent } : undefined}>
        {value}
      </span>
    </div>
  );
}

function ControlBtn({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex h-8 w-8 items-center justify-center rounded-lg border border-border/60 bg-background/80 text-muted-foreground backdrop-blur transition-colors hover:bg-accent hover:text-foreground"
    >
      {children}
    </button>
  );
}

function Toggle({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-lg border px-2.5 py-1 text-[11px] font-medium backdrop-blur transition-colors",
        active ? "border-primary/40 bg-primary/10 text-primary" : "border-border/60 bg-background/80 text-muted-foreground hover:bg-accent"
      )}
    >
      {children}
    </button>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
      <span className="text-muted-foreground">{label}</span>
    </span>
  );
}
