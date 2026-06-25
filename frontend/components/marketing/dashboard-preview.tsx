"use client";

import { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Boxes,
  ShieldAlert,
  Truck,
} from "lucide-react";
import { cn } from "@/lib/utils";

function useCountUp(target: number, duration = 1400, decimals = 0) {
  const [val, setVal] = useState(0);
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setVal(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return decimals
    ? val.toFixed(decimals)
    : Math.round(val).toLocaleString();
}

function Kpi({
  icon: Icon,
  label,
  value,
  delta,
  up,
  tone,
}: {
  icon: typeof Truck;
  label: string;
  value: string;
  delta: string;
  up: boolean;
  tone: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-background p-3">
      <div className="flex items-center justify-between">
        <span
          className={cn(
            "flex h-7 w-7 items-center justify-center rounded-lg",
            tone,
          )}
        >
          <Icon className="h-3.5 w-3.5" />
        </span>
        <span
          className={cn(
            "flex items-center gap-0.5 text-[10px] font-semibold",
            up ? "text-success" : "text-destructive",
          )}
        >
          {up ? (
            <ArrowUpRight className="h-3 w-3" />
          ) : (
            <ArrowDownRight className="h-3 w-3" />
          )}
          {delta}
        </span>
      </div>
      <p className="mt-2 font-mono text-lg font-semibold tabular-nums tracking-tight text-foreground">
        {value}
      </p>
      <p className="text-[10px] text-muted-foreground">{label}</p>
    </div>
  );
}

const BARS = [42, 58, 47, 65, 54, 72, 63, 80, 71, 88, 79, 94];

function MiniChart() {
  return (
    <div className="flex h-full flex-col rounded-xl border border-border bg-background p-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold text-foreground">
          On-time delivery
        </p>
        <span className="flex items-center gap-1 text-[10px] text-success">
          <span className="h-1.5 w-1.5 animate-count-blink rounded-full bg-success" />
          Live
        </span>
      </div>
      <div className="mt-3 flex flex-1 items-end gap-1.5">
        {BARS.map((h, i) => (
          <div
            key={i}
            className="flex-1 origin-bottom rounded-t-[3px] bg-gradient-to-t from-primary/30 to-primary"
            style={{
              height: `${h}%`,
              animation: `bar-rise 0.9s cubic-bezier(0.16,1,0.3,1) ${i * 60}ms both`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

function NetworkMap() {
  return (
    <div className="relative overflow-hidden rounded-xl border border-border bg-[linear-gradient(180deg,hsl(var(--muted)/0.5),hsl(var(--background)))] p-3">
      <p className="text-[11px] font-semibold text-foreground">Network view</p>
      <svg viewBox="0 0 320 120" className="mt-1 w-full">
        <defs>
          <linearGradient id="route" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="hsl(221 83% 53%)" stopOpacity="0.1" />
            <stop offset="50%" stopColor="hsl(221 83% 53%)" stopOpacity="0.9" />
            <stop offset="100%" stopColor="hsl(221 83% 53%)" stopOpacity="0.1" />
          </linearGradient>
        </defs>
        {/* routes */}
        {[
          "M40 80 C 110 20, 180 110, 270 40",
          "M50 40 C 130 90, 200 20, 290 90",
        ].map((d, i) => (
          <g key={i}>
            <path d={d} fill="none" stroke="hsl(var(--border))" strokeWidth="1.5" />
            <path
              d={d}
              fill="none"
              stroke="url(#route)"
              strokeWidth="1.8"
              strokeDasharray="6 8"
              className="animate-dash-flow"
            />
          </g>
        ))}
        {/* nodes */}
        {[
          { x: 40, y: 80, c: "hsl(142 71% 45%)" },
          { x: 270, y: 40, c: "hsl(221 83% 53%)" },
          { x: 50, y: 40, c: "hsl(221 83% 53%)" },
          { x: 290, y: 90, c: "hsl(38 92% 50%)" },
          { x: 165, y: 64, c: "hsl(0 72% 51%)" },
        ].map((n, i) => (
          <g key={i}>
            <circle cx={n.x} cy={n.y} r="9" fill={n.c} opacity="0.18">
              <animate
                attributeName="r"
                values="6;14;6"
                dur="2.6s"
                begin={`${i * 0.4}s`}
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="0.25;0;0.25"
                dur="2.6s"
                begin={`${i * 0.4}s`}
                repeatCount="indefinite"
              />
            </circle>
            <circle cx={n.x} cy={n.y} r="3.2" fill={n.c} />
          </g>
        ))}
        {/* moving shipment */}
        <circle r="3" fill="hsl(221 83% 53%)">
          <animateMotion
            dur="4s"
            repeatCount="indefinite"
            path="M40 80 C 110 20, 180 110, 270 40"
          />
        </circle>
      </svg>
    </div>
  );
}

const ALERTS = [
  {
    icon: AlertTriangle,
    tone: "text-destructive bg-destructive/10",
    title: "Port congestion — Rotterdam",
    meta: "3 shipments · ETA +2d",
  },
  {
    icon: ShieldAlert,
    tone: "text-warning bg-warning/10",
    title: "Supplier risk elevated",
    meta: "Meridian Components · 72→64",
  },
  {
    icon: Boxes,
    tone: "text-primary bg-primary/10",
    title: "Reorder recommended",
    meta: "SKU-4471 · 6 days cover",
  },
];

export function DashboardPreview() {
  const onTime = useCountUp(94.2, 1600, 1);
  const shipments = useCountUp(1284);
  const risk = useCountUp(37);

  return (
    <div className="relative">
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-premium">
        {/* window chrome */}
        <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-4 py-2.5">
          <span className="h-2.5 w-2.5 rounded-full bg-destructive/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-warning/60" />
          <span className="h-2.5 w-2.5 rounded-full bg-success/60" />
          <div className="ml-3 flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
            <Activity className="h-3 w-3 text-primary" />
            ATLASOPS · Mission Control
          </div>
          <span className="ml-auto rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-semibold text-success">
            Operational
          </span>
        </div>

        <div className="grid gap-3 p-4 sm:grid-cols-3">
          <Kpi
            icon={Truck}
            label="Active shipments"
            value={shipments}
            delta="4.1%"
            up
            tone="bg-primary/10 text-primary"
          />
          <Kpi
            icon={Activity}
            label="On-time delivery"
            value={`${onTime}%`}
            delta="1.2%"
            up
            tone="bg-success/10 text-success"
          />
          <Kpi
            icon={ShieldAlert}
            label="Risk index"
            value={risk}
            delta="3pts"
            up={false}
            tone="bg-warning/10 text-warning"
          />

          <div className="sm:col-span-2">
            <div className="h-36">
              <MiniChart />
            </div>
          </div>
          <div className="rounded-xl border border-border bg-background p-3">
            <p className="text-[11px] font-semibold text-foreground">
              Situation report
            </p>
            <p className="mt-2 text-[10.5px] leading-relaxed text-muted-foreground">
              Network stable. Two corridors show elevated transit risk; mitigation
              recommended for the Rotterdam lane.
            </p>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div className="h-full w-[78%] rounded-full bg-gradient-to-r from-primary to-blue-600" />
            </div>
            <p className="mt-1 text-[9.5px] text-muted-foreground">
              Operational health · 78
            </p>
          </div>

          <div className="sm:col-span-2">
            <NetworkMap />
          </div>
          <div className="space-y-2 rounded-xl border border-border bg-background p-3">
            <p className="text-[11px] font-semibold text-foreground">
              Critical alerts
            </p>
            {ALERTS.map((a, i) => (
              <div
                key={a.title}
                className="flex items-start gap-2 rounded-lg p-1.5"
                style={{
                  animation: `fade-up 0.6s ease-out ${600 + i * 180}ms both`,
                }}
              >
                <span
                  className={cn(
                    "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md",
                    a.tone,
                  )}
                >
                  <a.icon className="h-3 w-3" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-[10.5px] font-medium text-foreground">
                    {a.title}
                  </p>
                  <p className="truncate text-[9.5px] text-muted-foreground">
                    {a.meta}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* floating accent cards */}
      <div className="absolute -right-4 -top-5 hidden rounded-xl border border-border bg-background px-3 py-2 shadow-card md:block animate-float">
        <p className="text-[10px] text-muted-foreground">Records synced</p>
        <p className="font-mono text-sm font-semibold text-foreground">
          2.4M / day
        </p>
      </div>
      <div
        className="absolute -bottom-5 -left-4 hidden rounded-xl border border-border bg-background px-3 py-2 shadow-card md:block animate-float"
        style={{ animationDelay: "1.5s" }}
      >
        <p className="text-[10px] text-muted-foreground">Decisions supported</p>
        <p className="font-mono text-sm font-semibold text-success">+318 this wk</p>
      </div>
    </div>
  );
}
