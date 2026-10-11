"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, Plug, RefreshCw, Trash2, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { canWriteRole, useAuth } from "@/lib/auth";
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

const FREQS = ["Manual", "Every 15 min", "Hourly", "Daily", "Weekly"];

function customerReason(source: DataSource): string {
  const raw = `${source.failure_class || ""} ${source.last_error || ""}`.toLowerCase();
  if (raw.includes("auth") || raw.includes("401") || raw.includes("403") || raw.includes("invalid_grant")) {
    return "Authentication expired";
  }
  if (raw.includes("429") || raw.includes("rate")) {
    return "The provider is temporarily rate-limited. Try again shortly.";
  }
  if (raw.includes("timeout") || raw.includes("network") || raw.includes("503") || raw.includes("502")) {
    return "The provider is temporarily unavailable. The sync will retry automatically.";
  }
  if (source.last_error) {
    return source.last_error;
  }
  return "Synchronization did not complete.";
}

export default function ConnectorConfigPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { currentMembership } = useAuth();
  const canWrite = canWriteRole(currentMembership?.role_slug);

  const [source, setSource] = useState<DataSource | null>(null);
  const [templates, setTemplates] = useState<IntegrationTemplate[]>([]);
  const [error, setError] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [companyDb, setCompanyDb] = useState("");
  const [mappingJson, setMappingJson] = useState("[]");
  const [saveError, setSaveError] = useState("");
  const [sandbox, setSandbox] = useState(false);
  const [auth, setAuth] = useState("");
  const [freq, setFreq] = useState("");
  const [webhook, setWebhook] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncStartedAt, setSyncStartedAt] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<DataSource>(`/data/sources/${id}`)
      .then((s) => {
        setSource(s);
        setBaseUrl(s.base_url ?? "");
        setAuth(s.auth_method ?? "");
        setFreq(s.sync_frequency ?? "");
        setWebhook(s.webhook_url ?? "");
        setSandbox(Boolean(s.config?.sandbox));
        setMappingJson(JSON.stringify(s.config?.sync_entities ?? [], null, 2));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Not found"));
    api.get<IntegrationTemplate[]>("/data/integrations").then(setTemplates).catch(() => {});
  }, [id]);

  useEffect(() => {
    if (source?.status !== "syncing") return;
    const t = setInterval(() => {
      api
        .get<DataSource>(`/data/sources/${id}`)
        .then(setSource)
        .catch(() => {});
    }, 3000);
    return () => clearInterval(t);
  }, [source?.status, id]);

  if (error) return <ErrorState message={error} />;
  if (!source) return <LoadingState label="Loading connector…" />;

  const template = templates.find((t) => t.type === source.connector_type);
  const authMethods = template?.auth_methods ?? ["API Key", "OAuth2", "Basic", "None"];
  const isSalesforce = source.connector_type === "salesforce" || source.connector_type === "salesforce_crm";
  const isSap = source.connector_type === "sap_business_one";
  const notConnected = source.status === "not_configured" || source.status === "disconnected";
  const inProgress = source.status === "syncing" || syncing;
  const failed = source.status === "error";

  async function save() {
    setSaving(true);
    setSaved(false);
    setSaveError("");
    try {
      const credentials: Record<string, string> = {};
      if (isSalesforce) {
        if (clientId) credentials.client_id = clientId;
        if (clientSecret) credentials.client_secret = clientSecret;
        if (username) credentials.username = username;
        if (password) credentials.password = password;
      } else if (isSap) {
        if (username) credentials.username = username;
        if (password) credentials.password = password;
        if (companyDb) credentials.company_db = companyDb;
      } else if (apiKey) {
        credentials.api_key = apiKey;
      }
      const config: Record<string, unknown> = isSalesforce ? { sandbox } : {};
      if (isSalesforce || isSap) {
        const mappings: unknown = JSON.parse(mappingJson);
        if (!Array.isArray(mappings) || mappings.length === 0) throw new Error("Add explicit entity mappings before saving this connector.");
        config.sync_entities = mappings;
      }
      const updated = await api.put<DataSource>(`/data/sources/${id}/config`, {
        base_url: baseUrl,
        api_key: !isSalesforce && !isSap && apiKey ? apiKey : undefined,
        credentials: Object.keys(credentials).length ? credentials : undefined,
        config,
        auth_method: auth || undefined,
        sync_frequency: freq || undefined,
        webhook_url: webhook || undefined,
      });
      setSource(updated);
      setApiKey("");
      setClientSecret("");
      setPassword("");
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Could not save connector");
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
      const s = await api.get<DataSource>(`/data/sources/${id}`);
      setSource(s);
    } catch (e) {
      setTestResult({
        ok: false,
        message: e instanceof Error ? e.message : "Connection test failed",
      });
    } finally {
      setTesting(false);
    }
  }

  async function sync() {
    setSyncing(true);
    setSyncStartedAt(new Date().toISOString());
    try {
      await api.post(`/data/sources/${id}/sync`);
      const s = await api.get<DataSource>(`/data/sources/${id}`);
      setSource(s);
    } finally {
      setSyncing(false);
    }
  }

  async function reconnect() {
    await api.post(`/data/sources/${id}/disconnect`);
    const s = await api.get<DataSource>(`/data/sources/${id}`);
    setSource(s);
    setClientId("");
    setClientSecret("");
    setUsername("");
    setPassword("");
    setApiKey("");
    setTestResult(null);
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

      {notConnected && (
        <Card>
          <CardContent className="flex items-center justify-between p-4 text-sm">
            <span className="font-medium">Not Connected</span>
            {canWrite && (
              <Button size="sm" onClick={save} disabled={saving}>
                Connect
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {testing && (
        <Card>
          <CardContent className="p-4 text-sm text-muted-foreground">Validating connection…</CardContent>
        </Card>
      )}

      {inProgress && (
        <Card>
          <CardContent className="p-4 text-sm">
            <p className="font-medium">Sync in progress</p>
            <p className="mt-1 text-muted-foreground">
              Started {relativeTime(syncStartedAt || source.last_sync_at || new Date().toISOString())}
            </p>
          </CardContent>
        </Card>
      )}

      {source.status === "connected" && source.last_sync_at && !inProgress && (
        <Card>
          <CardContent className="p-4 text-sm">
            <p className="font-medium">Connected</p>
            <p className="mt-1 text-muted-foreground">Last successful sync: {relativeTime(source.last_sync_at)}</p>
          </CardContent>
        </Card>
      )}

      {failed && (
        <Card>
          <CardContent className="space-y-3 p-4 text-sm">
            <p className="font-medium text-destructive">Sync failed</p>
            <div>
              <p className="text-muted-foreground">Reason</p>
              <p className="mt-0.5">{customerReason(source)}</p>
            </div>
            {canWrite && (
              <div>
                <p className="text-muted-foreground">Action</p>
                <Button variant="outline" size="sm" className="mt-1" onClick={reconnect}>
                  Reconnect
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!isSalesforce && (
              <div className="space-y-1.5">
                <Label>Base URL</Label>
                <Input
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://api.example.com/v1"
                  disabled={!canWrite}
                />
              </div>
            )}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Authentication Method</Label>
                <Select value={auth} onValueChange={setAuth} disabled={!canWrite}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select method" />
                  </SelectTrigger>
                  <SelectContent>
                    {authMethods.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Sync Frequency</Label>
                <Select value={freq} onValueChange={setFreq} disabled={!canWrite}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select frequency" />
                  </SelectTrigger>
                  <SelectContent>
                    {FREQS.map((f) => (
                      <SelectItem key={f} value={f}>
                        {f}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {isSap && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">SAP Business One Service Layer v4. Enter an operator-approved HTTPS endpoint ending in /b1s/v2. Use a dedicated read-only integration user.</p>
                <Label htmlFor="sap-company">Company database</Label>
                <Input id="sap-company" value={companyDb} onChange={(e) => setCompanyDb(e.target.value)} placeholder="Enter to update stored value" disabled={!canWrite} />
                <Label htmlFor="sap-user">Integration username</Label>
                <Input id="sap-user" value={username} onChange={(e) => setUsername(e.target.value)} disabled={!canWrite} />
                <Label htmlFor="sap-password">Password</Label>
                <Input id="sap-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Stored encrypted" disabled={!canWrite} />
              </div>
            )}
            {(isSalesforce || isSap) && (
              <div className="space-y-2">
                <Label htmlFor="sync-mappings">Explicit entity mappings (JSON)</Label>
                <p className="text-sm text-muted-foreground">Supervised pilot configuration: select source objects, destination fields and order status mappings with your implementation contact. Sync refreshes up to 10,000 records per object. Orders include headers only; source deletions are not applied. Sandbox reconciliation is required before daily use.</p>
                <textarea id="sync-mappings" className="min-h-48 w-full rounded border bg-background p-3 font-mono text-xs" value={mappingJson} onChange={(e) => setMappingJson(e.target.value)} disabled={!canWrite} spellCheck={false} />
              </div>
            )}
            {isSalesforce ? (
              <>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label>Connected App client ID</Label>
                    <Input
                      value={clientId}
                      onChange={(e) => setClientId(e.target.value)}
                      placeholder={source.credential_hints?.client_id ? "Stored — enter to replace" : "Enter client id"}
                      disabled={!canWrite}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>
                      Client secret{" "}
                      {source.credential_hints?.client_secret_masked && (
                        <span className="text-muted-foreground">(stored: {source.credential_hints.client_secret_masked})</span>
                      )}
                    </Label>
                    <Input
                      type="password"
                      value={clientSecret}
                      onChange={(e) => setClientSecret(e.target.value)}
                      placeholder="Enter to update — stored encrypted"
                      disabled={!canWrite}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label>Username</Label>
                    <Input
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder={source.credential_hints?.username_masked ? "Stored — enter to replace" : "Optional password grant"}
                      disabled={!canWrite}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Password</Label>
                    <Input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter to update — stored encrypted"
                      disabled={!canWrite}
                    />
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={sandbox}
                    onChange={(e) => setSandbox(e.target.checked)}
                    disabled={!canWrite}
                  />
                  Sandbox (test.salesforce.com)
                </label>
              </>
            ) : !isSap ? (
              <div className="space-y-1.5">
                <Label>
                  API Key {source.api_key_masked && <span className="text-muted-foreground">(stored: {source.api_key_masked})</span>}
                </Label>
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter to update — stored masked"
                  disabled={!canWrite}
                />
              </div>
            ) : null}
            {saveError && <p role="alert" className="text-sm text-destructive">{saveError}</p>}

            <div className="space-y-1.5">
              <Label>Webhook URL</Label>
              <Input
                value={webhook}
                onChange={(e) => setWebhook(e.target.value)}
                placeholder="https://your-app/webhooks/ingest"
                disabled={!canWrite}
              />
            </div>

            {canWrite && (
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <Button onClick={save} disabled={saving}>
                  {saving ? "Saving…" : saved ? "Saved ✓" : notConnected ? "Connect" : "Save configuration"}
                </Button>
                <Button variant="outline" onClick={test} disabled={testing}>
                  <Plug className="h-3.5 w-3.5" /> {testing ? "Validating connection…" : "Test connection"}
                </Button>
                <Button variant="outline" onClick={sync} disabled={syncing || source.status === "syncing"}>
                  <RefreshCw className={`h-3.5 w-3.5 ${inProgress ? "animate-spin" : ""}`} /> Sync now
                </Button>
              </div>
            )}

            {testResult && (
              <div
                className={`flex items-center gap-2 rounded-lg border p-3 text-sm ${
                  testResult.ok
                    ? "border-success/30 bg-success/10 text-success"
                    : "border-destructive/30 bg-destructive/10 text-destructive"
                }`}
              >
                {testResult.ok ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                {testResult.message}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Row label="Type">
                <span className="flex items-center gap-1.5">
                  <ConnectorIcon type={source.connector_type} className="h-4 w-4" />
                  {template?.name ?? source.connector_type}
                </span>
              </Row>
              <Row label="Status">
                <StatusBadge status={source.status} />
              </Row>
              <Row label="Health">
                <HealthDot health={source.health} withLabel />
              </Row>
              <Row label="Records">
                <span className="font-mono tabular-nums">{formatNumber(source.record_count)}</span>
              </Row>
              <Row label="Last Sync">
                <span className="text-muted-foreground">{source.last_sync_at ? relativeTime(source.last_sync_at) : "never"}</span>
              </Row>
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
