"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Save } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import { relativeTime } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type StudioDetail = {
  id: string;
  name: string;
  connector_type: string;
  status: string;
  health: string;
  health_score: number;
  field_mappings: { source?: string; destination?: string; transform?: string }[];
  conflict_resolution: string;
  sync_frequency?: string | null;
  webhook_url?: string | null;
  logs: {
    id: string;
    status: string;
    latency_ms: number;
    records_imported: number;
    created_at?: string | null;
    message?: string | null;
  }[];
  retry_policy?: { max_attempts?: number; backoff_seconds?: number };
};

export default function ConnectorStudioDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, loading, error, refetch } = useFetch<StudioDetail>(
    `/connector-studio/connections/${id}`,
    [id]
  );
  const [mappingsJson, setMappingsJson] = useState("");
  const [conflict, setConflict] = useState("source_wins");
  const [freq, setFreq] = useState("");
  const [webhook, setWebhook] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState("");

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error || "Not found"} />;

  if (!mappingsJson && data.field_mappings) {
    // initialize once
  }

  async function save() {
    setBusy(true);
    setMsg("");
    try {
      let mappings = data!.field_mappings;
      if (mappingsJson.trim()) mappings = JSON.parse(mappingsJson);
      await api.put(`/connector-studio/connections/${id}/config`, {
        field_mappings: mappings,
        conflict_resolution: conflict || data!.conflict_resolution,
        sync_frequency: freq || data!.sync_frequency || undefined,
        webhook_url: webhook || data!.webhook_url || undefined,
      });
      setMsg("Saved");
      await refetch();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function runPreview() {
    setBusy(true);
    try {
      const p = await api.post<Record<string, unknown>>(
        `/connector-studio/connections/${id}/preview`
      );
      setPreview(p);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title={data.name} description={`Connector Studio · ${data.connector_type}`}>
        <Link href="/connector-studio">
          <Button variant="outline" size="sm">
            <ArrowLeft className="h-3.5 w-3.5" /> Studio
          </Button>
        </Link>
        <Badge variant={data.health_score >= 70 ? "success" : "warning"}>
          Health {data.health_score}
        </Badge>
        <Badge variant="secondary">{data.status}</Badge>
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-7">
          <CardHeader>
            <CardTitle className="text-sm">Field mappings & conflict policy</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <textarea
              className="min-h-[160px] w-full rounded-md border border-input bg-background p-3 font-mono text-xs"
              placeholder={JSON.stringify(data.field_mappings || [], null, 2)}
              defaultValue={JSON.stringify(data.field_mappings || [], null, 2)}
              onChange={(e) => setMappingsJson(e.target.value)}
            />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div>
                <p className="mb-1 text-xs text-muted-foreground">Conflict resolution</p>
                <Select
                  defaultValue={data.conflict_resolution || "source_wins"}
                  onValueChange={setConflict}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="source_wins">Source wins</SelectItem>
                    <SelectItem value="destination_wins">Destination wins</SelectItem>
                    <SelectItem value="manual">Manual review</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <p className="mb-1 text-xs text-muted-foreground">Sync frequency</p>
                <Input
                  defaultValue={data.sync_frequency || ""}
                  placeholder="Hourly"
                  onChange={(e) => setFreq(e.target.value)}
                />
              </div>
              <div>
                <p className="mb-1 text-xs text-muted-foreground">Webhook URL</p>
                <Input
                  defaultValue={data.webhook_url || ""}
                  placeholder="https://…"
                  onChange={(e) => setWebhook(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={save} disabled={busy}>
                <Save className="h-3.5 w-3.5" /> Save config
              </Button>
              <Button variant="outline" onClick={runPreview} disabled={busy}>
                Sync preview
              </Button>
            </div>
            {msg && <p className="text-xs text-muted-foreground">{msg}</p>}
            {preview && (
              <pre className="overflow-auto rounded-md bg-muted/40 p-3 text-[11px]">
                {JSON.stringify(preview, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-5">
          <CardHeader>
            <CardTitle className="text-sm">Diagnostics log</CardTitle>
          </CardHeader>
          <CardContent className="max-h-[420px] space-y-2 overflow-auto">
            {(data.logs || []).length === 0 && (
              <p className="text-xs text-muted-foreground">No sync logs yet</p>
            )}
            {(data.logs || []).map((l) => (
              <div key={l.id} className="rounded-md border border-border/60 p-2 text-xs">
                <div className="flex justify-between">
                  <Badge variant="secondary">{l.status}</Badge>
                  <span className="text-muted-foreground">
                    {l.created_at ? relativeTime(l.created_at) : "—"}
                  </span>
                </div>
                <p className="mt-1 text-muted-foreground">
                  imported {l.records_imported} · {l.latency_ms}ms
                </p>
                {l.message && <p className="mt-1 text-destructive">{l.message}</p>}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
