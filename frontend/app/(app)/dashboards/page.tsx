"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  LayoutDashboard,
  Link2,
  Package,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
  Truck,
} from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import { formatCurrency, titleCase } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Kpi } from "@/components/shared/kpi";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type DashboardPayload = {
  name: string;
  widgets: string[];
  data: Record<string, unknown>;
  health: { operational: number; data: number; data_grade: string };
};

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
}

function asList(v: unknown): Record<string, unknown>[] {
  return Array.isArray(v) ? (v as Record<string, unknown>[]) : [];
}

function num(v: unknown, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function WidgetCard({ widgetKey, value }: { widgetKey: string; value: unknown }) {
  const title = titleCase(widgetKey.replace(/_/g, " "));
  const obj = asRecord(value);
  const list = asList(value);

  if (widgetKey === "health") {
    return (
      <Kpi
        label={title}
        value={`${num(obj.score).toFixed(0)}`}
        icon={Activity}
        intent={num(obj.score) >= 80 ? "success" : num(obj.score) >= 60 ? "warning" : "danger"}
        sub="Operational health score"
      />
    );
  }

  if (widgetKey === "data_health") {
    return (
      <Kpi
        label={title}
        value={`${num(obj.overall_score).toFixed(0)}`}
        icon={Package}
        intent={num(obj.overall_score) >= 80 ? "success" : "warning"}
        sub={`Grade ${String(obj.grade ?? "—")}`}
      />
    );
  }

  if (widgetKey === "shipments") {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{title}</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-3 text-center">
          <MetricCell label="Active" value={num(obj.active)} />
          <MetricCell label="Delayed" value={num(obj.delayed)} intent="danger" />
          <MetricCell label="On-time %" value={num(obj.on_time)} />
        </CardContent>
      </Card>
    );
  }

  if (widgetKey === "revenue_at_risk" || widgetKey === "shipment_value") {
    return (
      <Kpi
        label={title}
        value={formatCurrency(num(obj.value_usd))}
        icon={TrendingUp}
        intent="warning"
        sub="In-transit + delayed value"
      />
    );
  }

  if (widgetKey === "purchase_orders" || widgetKey === "open_pos" || widgetKey === "open_sos") {
    return (
      <Kpi
        label={title}
        value={String(num(obj.open_count))}
        icon={Package}
        sub="Open / in-progress orders"
      />
    );
  }

  if (widgetKey === "connectors") {
    return (
      <Kpi
        label={title}
        value={String(num(obj.total))}
        icon={Link2}
        intent={num(obj.error) > 0 ? "danger" : "success"}
        sub={`${num(obj.error)} in error`}
      />
    );
  }

  if (widgetKey === "supplier_reliability") {
    return (
      <Kpi
        label={title}
        value={`${num(obj.score).toFixed(0)}`}
        icon={ShieldAlert}
        sub="Reliability index"
      />
    );
  }

  if (typeof value === "number") {
    return <Kpi label={title} value={String(value)} icon={Activity} />;
  }

  if (obj.href && typeof obj.href === "string") {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Link href={obj.href} className="text-sm text-primary hover:underline">
            Open related view
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (list.length > 0) {
    const cols = Object.keys(list[0]).slice(0, 4);
    return (
      <Card className="col-span-1 md:col-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                {cols.map((c) => (
                  <TableHead key={c}>{titleCase(c.replace(/_/g, " "))}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.slice(0, 8).map((row, i) => (
                <TableRow key={i}>
                  {cols.map((c) => (
                    <TableCell key={c} className="max-w-[180px] truncate text-sm">
                      {formatCell(row[c])}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    );
  }

  if (widgetKey === "risk_heatmap" || Object.keys(obj).length > 0) {
    const entries = Object.entries(obj).filter(([, v]) => typeof v === "number" || typeof v === "string");
    if (entries.length > 0) {
      return (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {entries.slice(0, 8).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{titleCase(k.replace(/_/g, " "))}</span>
                <span className="font-medium tabular-nums">{formatCell(v)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      );
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">No data for this widget yet.</CardContent>
    </Card>
  );
}

function MetricCell({
  label,
  value,
  intent,
}: {
  label: string;
  value: number;
  intent?: "danger";
}) {
  return (
    <div>
      <p className="text-[11px] uppercase text-muted-foreground">{label}</p>
      <p
        className={`mt-1 text-xl font-semibold tabular-nums ${
          intent === "danger" && value > 0 ? "text-destructive" : ""
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function formatCell(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(1);
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export default function DashboardsPage() {
  const { data: roles } = useFetch<{ roles: { role_key: string; name: string }[] }>(
    "/dashboards/roles"
  );
  const [role, setRole] = useState("ceo");
  const [saving, setSaving] = useState(false);
  const { data, loading, error, refetch } = useFetch<DashboardPayload>(
    `/dashboards/${role}`,
    [role]
  );

  const roleOptions = useMemo(() => roles?.roles || [], [roles]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Executive Dashboards"
        description="Role-specific command views backed by live operational metrics."
      >
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger className="w-56">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {roleOptions.map((r) => (
              <SelectItem key={r.role_key} value={r.role_key}>
                {r.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </Button>
      </PageHeader>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {data && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="gap-1">
              <LayoutDashboard className="h-3 w-3" /> {data.name}
            </Badge>
            <Badge variant="success">Ops {Math.round(data.health.operational)}</Badge>
            <Badge variant="outline">
              Data {Math.round(num(data.health.data))} ({data.health.data_grade})
            </Badge>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.widgets.map((w) => (
              <WidgetCard key={w} widgetKey={w} value={data.data[w]} />
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={saving}
              onClick={async () => {
                setSaving(true);
                try {
                  await api.put(`/dashboards/${role}/layout`, {
                    name: data.name,
                    widgets: data.widgets,
                    is_default: true,
                  });
                } finally {
                  setSaving(false);
                }
              }}
            >
              Save layout
            </Button>
            <Link href="/mission-control">
              <Button variant="ghost" size="sm">
                <Truck className="h-3.5 w-3.5" /> Mission Control
              </Button>
            </Link>
            <Link href="/risk">
              <Button variant="ghost" size="sm">
                <AlertTriangle className="h-3.5 w-3.5" /> Risk center
              </Button>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
