"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, Plug, RefreshCw, Trash2, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { DataSource, IntegrationTemplate } from "@/lib/types";
import { formatNumber, relativeTime } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { LoadingState, ErrorState } from "@/components/shared/states";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConnectorIcon, HealthDot, StatusBadge } from "@/components/data/data-bits";

const FREQS = ["Real-time", "Every 15 min", "Hourly", "Daily", "Weekly"];

export default function ConnectorConfigPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { user } = useAuth();
  const canWrite = user && user.role !== "executive";

  const [source, setSource] = useState<DataSource | null>(null);
  const [templates, setTemplates] = useState<IntegrationTemplate[]>([]);
  const [error, setError] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [auth, setAuth] = useState("");
  const [freq, setFreq] = useState("");
  const [webhook, setWebhook] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    api.get<DataSource>(`/data/sources/${id}`)
      .then((s) => {
        setSource(s);
        setBaseUrl(s.base_url ?? "");
        setAuth(s.auth_method ?? "");
        setFreq(s.sync_frequency ?? "");
        setWebhook(s.webhook_url ?? "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Not found"));
    api.get<IntegrationTemplate[]>("/data/integrations").then(setTemplates).catch(() => {});
  }, [id]);

  if (error) return <ErrorState message={error} />;
  if (!source) return <LoadingState label="Loading connector…" />;

  const template = templates.find((t) => t.type === source.connector_type);
  const authMethods = template?.auth_methods ?? ["API Key", "OAuth2", "Basic", "None"];

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.put<DataSource>(`/data/sources/${id}/config`, {
        base_url: baseUrl,
        api_key: apiKey || undefined,
        auth_method: auth || undefined,
        sync_frequency: freq || undefined,
        webhook_url: webhook || undefined,
      });
      setSource(updated);
      setApiKey("");
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  }

  async function test() {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await api.post<{ ok: boolean; message: string }>(`/data/sources/${id}/test`);
      setTestResult(r);
    } finally {
      setTesting(false);
    }
  }

  async function sync() {
    setSyncing(true);
    try {
      await api.post(`/data/sources/${id}/sync`);
      const s = await api.get<DataSource>(`/data/sources/${id}`);
      setSource(s);
    } finally {
      setSyncing(false);
    }
  }

  async function remove() {
    await api.delete(`/data/sources/${id}`);
    router.push("/data-sources/connectors");
  }

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.push("/data-sources/connectors")}
        className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to connectors
      </button>

      <PageHeader title={source.name} description={template?.description ?? "Connector configuration"}>
        <StatusBadge status={source.status} />
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Base URL</Label>
              <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.example.com/v1" disabled={!canWrite} />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Authentication Method</Label>
                <Select value={auth} onValueChange={setAuth} disabled={!canWrite}>
                  <SelectTrigger><SelectValue placeholder="Select method" /></SelectTrigger>
                  <SelectContent>
                    {authMethods.map((m) => (
                      <SelectItem key={m} value={m}>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Sync Frequency</Label>
                <Select value={freq} onValueChange={setFreq} disabled={!canWrite}>
                  <SelectTrigger><SelectValue placeholder="Select frequency" /></SelectTrigger>
                  <SelectContent>
                    {FREQS.map((f) => (
                      <SelectItem key={f} value={f}>{f}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>API Key {source.api_key_masked && <span className="text-muted-foreground">(stored: {source.api_key_masked})</span>}</Label>
              <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="Enter to update — stored masked" disabled={!canWrite} />
            </div>
            <div className="space-y-1.5">
              <Label>Webhook URL</Label>
              <Input value={webhook} onChange={(e) => setWebhook(e.target.value)} placeholder="https://your-app/webhooks/ingest" disabled={!canWrite} />
            </div>

            {canWrite && (
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <Button onClick={save} disabled={saving}>
                  {saving ? "Saving…" : saved ? "Saved ✓" : "Save configuration"}
                </Button>
                <Button variant="outline" onClick={test} disabled={testing}>
                  <Plug className="h-3.5 w-3.5" /> {testing ? "Testing…" : "Test connection"}
                </Button>
                <Button variant="outline" onClick={sync} disabled={syncing}>
                  <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} /> Sync now
                </Button>
              </div>
            )}

            {testResult && (
              <div className={`flex items-center gap-2 rounded-lg border p-3 text-sm ${testResult.ok ? "border-success/30 bg-success/10 text-success" : "border-destructive/30 bg-destructive/10 text-destructive"}`}>
                {testResult.ok ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                {testResult.message}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-sm">Status</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Row label="Type"><span className="flex items-center gap-1.5"><ConnectorIcon type={source.connector_type} className="h-4 w-4" />{template?.name ?? source.connector_type}</span></Row>
              <Row label="Status"><StatusBadge status={source.status} /></Row>
              <Row label="Health"><HealthDot health={source.health} withLabel /></Row>
              <Row label="Records"><span className="font-mono tabular-nums">{formatNumber(source.record_count)}</span></Row>
              <Row label="Last Sync"><span className="text-muted-foreground">{source.last_sync_at ? relativeTime(source.last_sync_at) : "never"}</span></Row>
            </CardContent>
          </Card>
          {canWrite && (
            <Button variant="outline" className="w-full text-destructive hover:text-destructive" onClick={remove}>
              <Trash2 className="h-3.5 w-3.5" /> Remove connector
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border/40 pb-2 last:border-0 last:pb-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{children}</span>
    </div>
  );
}
