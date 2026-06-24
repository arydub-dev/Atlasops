"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, MapPin, PackageCheck, Save } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import type { ShipmentDetail, ShipmentStatus } from "@/lib/types";
import { formatCurrency, formatDate, formatDateTime, formatNumber, titleCase } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { ShipmentStatusBadge } from "@/components/shared/badges";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const STATUS_OPTIONS: ShipmentStatus[] = [
  "in_transit",
  "delayed",
  "at_warehouse",
  "customs_hold",
  "delivered",
];

export default function ShipmentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user } = useAuth();
  const { data, loading, error, refetch } = useFetch<ShipmentDetail>(`/shipments/${id}`);
  const [newStatus, setNewStatus] = useState<ShipmentStatus | "">("");
  const [location, setLocation] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const canUpdate = user?.role === "admin" || user?.role === "operations_manager";

  async function save() {
    if (!newStatus) return;
    setSaving(true);
    setMsg("");
    try {
      await api.patch(`/shipments/${id}/status`, {
        status: newStatus,
        current_location: location || undefined,
        note: note || undefined,
      });
      setMsg("Status updated.");
      setNote("");
      setNewStatus("");
      setLocation("");
      refetch();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Update failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error || "Shipment not found"} />;

  const facts = [
    { label: "Origin", value: data.origin },
    { label: "Destination", value: data.destination },
    { label: "Current Location", value: data.current_location },
    { label: "Carrier", value: data.carrier },
    { label: "Supplier", value: data.supplier_name ?? "—" },
    { label: "Warehouse", value: data.warehouse_name ?? "—" },
    { label: "Units", value: formatNumber(data.units) },
    { label: "Value", value: formatCurrency(data.value_usd) },
    { label: "Shipped", value: formatDate(data.shipped_at) },
    { label: "ETA", value: formatDate(data.eta) },
    { label: "Delivered", value: data.delivered_at ? formatDate(data.delivered_at) : "—" },
    { label: "Delay", value: `${data.delay_days.toFixed(1)} days` },
  ];

  return (
    <div className="space-y-6">
      <Link href="/shipments">
        <Button variant="ghost" size="sm" className="-ml-2">
          <ArrowLeft className="h-4 w-4" /> Back to shipments
        </Button>
      </Link>

      <PageHeader title={data.reference} description={`${data.origin} → ${data.destination}`}>
        <ShipmentStatusBadge status={data.status} />
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Shipment Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
                {facts.map((f) => (
                  <div key={f.label}>
                    <dt className="text-xs uppercase tracking-wide text-muted-foreground">{f.label}</dt>
                    <dd className="mt-0.5 text-sm font-medium">{f.value}</dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Tracking Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              {data.events.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">No tracking events recorded.</p>
              ) : (
                <ol className="relative space-y-5 border-l border-border pl-6">
                  {data.events.map((e) => (
                    <li key={e.id} className="relative">
                      <span className="absolute -left-[27px] flex h-3 w-3 items-center justify-center rounded-full bg-primary ring-4 ring-background" />
                      <div className="flex flex-wrap items-center gap-2">
                        <ShipmentStatusBadge status={e.status} />
                        <span className="flex items-center gap-1 text-sm text-muted-foreground">
                          <MapPin className="h-3 w-3" /> {e.location}
                        </span>
                        <span className="text-xs text-muted-foreground">{formatDateTime(e.occurred_at)}</span>
                      </div>
                      {e.note && <p className="mt-1 text-sm">{e.note}</p>}
                    </li>
                  ))}
                </ol>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <PackageCheck className="h-4 w-4" /> Update Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!canUpdate && (
                <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
                  Your role ({user ? titleCase(user.role) : ""}) has read-only access. Operations
                  Managers can update shipment status.
                </p>
              )}
              <div className="space-y-1.5">
                <Label>New Status</Label>
                <Select value={newStatus} onValueChange={(v) => setNewStatus(v as ShipmentStatus)} disabled={!canUpdate}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_OPTIONS.map((s) => (
                      <SelectItem key={s} value={s}>
                        {titleCase(s)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Current Location</Label>
                <Input
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder={data.current_location}
                  disabled={!canUpdate}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Note</Label>
                <Input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Optional note"
                  disabled={!canUpdate}
                />
              </div>
              <Button onClick={save} disabled={!canUpdate || !newStatus || saving} className="w-full">
                <Save className="h-4 w-4" />
                {saving ? "Saving…" : "Save update"}
              </Button>
              {msg && <p className="text-xs text-muted-foreground">{msg}</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Delay Risk Score</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-2">
                <span className="font-mono text-4xl font-semibold tabular-nums">
                  {data.delay_risk_score.toFixed(0)}
                </span>
                <span className="pb-1.5 text-sm text-muted-foreground">/ 100</span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Model-predicted likelihood of delivery slippage based on carrier, route, and
                supplier reliability.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
