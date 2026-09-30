"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, MonitorSmartphone, Shield, Trash2 } from "lucide-react";
import { canManageSecurity, useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface SessionRow {
  id: string;
  device_label?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  device_trusted: boolean;
  is_current: boolean;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  user_email?: string | null;
}

interface LoginEvent {
  id: string;
  user_email?: string | null;
  action: string;
  detail?: string | null;
  ip_address?: string | null;
  created_at: string;
}

interface AuthSettings {
  allowed_email_domains: string[];
  workos_organization_id?: string | null;
  sso_configured: boolean;
  mfa_required: boolean;
}

function fmt(ts: string) {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export default function SecuritySettingsPage() {
  const { currentMembership, logoutAll } = useAuth();
  const isAdmin = canManageSecurity(currentMembership?.role_slug);

  const [mySessions, setMySessions] = useState<SessionRow[]>([]);
  const [orgSessions, setOrgSessions] = useState<SessionRow[]>([]);
  const [history, setHistory] = useState<LoginEvent[]>([]);
  const [settings, setSettings] = useState<AuthSettings | null>(null);
  const [domainsText, setDomainsText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const mine = await api.get<SessionRow[]>("/auth/sessions");
      setMySessions(mine);
      if (isAdmin) {
        const [org, hist, auth] = await Promise.all([
          api.get<SessionRow[]>("/orgs/current/security/sessions").catch(() => []),
          api.get<LoginEvent[]>("/orgs/current/security/login-history?limit=50").catch(() => []),
          api.get<AuthSettings>("/orgs/current/security/settings").catch(() => null),
        ]);
        setOrgSessions(org);
        setHistory(hist);
        setSettings(auth);
        setDomainsText((auth?.allowed_email_domains || []).join(", "));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load security data");
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void load();
    }, 0);
    return () => clearTimeout(timeoutId);
  }, [load]);

  async function revokeMine(id: string) {
    setError("");
    await api.delete(`/auth/sessions/${id}`);
    await load();
  }

  async function revokeOrg(id: string) {
    setError("");
    await api.delete(`/orgs/current/security/sessions/${id}`);
    await load();
  }

  async function saveDomains() {
    setSaving(true);
    setError("");
    try {
      const domains = domainsText
        .split(/[,\s]+/)
        .map((d) => d.trim().toLowerCase())
        .filter(Boolean);
      const updated = await api.patch<AuthSettings>("/orgs/current/security/settings", {
        allowed_email_domains: domains,
      });
      setSettings(updated);
      setDomainsText(updated.allowed_email_domains.join(", "));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save domains");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading security settings…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Security"
        description="Sessions, login history, and organization authentication controls."
      />

      {error && (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <MonitorSmartphone className="h-4 w-4" /> Your active sessions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {mySessions.length === 0 && (
            <p className="text-sm text-muted-foreground">No active sessions.</p>
          )}
          {mySessions.map((s) => (
            <div
              key={s.id}
              className="flex flex-col gap-2 rounded-lg border border-border px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="space-y-1 text-sm">
                <div className="flex flex-wrap items-center gap-2 font-medium">
                  {s.device_label || "Unknown device"}
                  {s.is_current && <Badge variant="secondary">This device</Badge>}
                  {s.device_trusted && <Badge variant="outline">Remembered</Badge>}
                </div>
                <p className="text-xs text-muted-foreground">
                  {s.ip_address || "—"} · Last active {fmt(s.last_seen_at)}
                </p>
              </div>
              {!s.is_current && (
                <Button variant="outline" size="sm" onClick={() => revokeMine(s.id)}>
                  <Trash2 className="h-3.5 w-3.5" /> Revoke
                </Button>
              )}
            </div>
          ))}
          <div className="pt-2">
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                if (confirm("Sign out of all devices? You will need to sign in again.")) {
                  logoutAll();
                }
              }}
            >
              Log out everywhere
            </Button>
          </div>
        </CardContent>
      </Card>

      {isAdmin && (
        <>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Shield className="h-4 w-4" /> Authentication settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge variant={settings?.sso_configured ? "default" : "secondary"}>
                  {settings?.sso_configured ? "Enterprise SSO linked" : "SSO not linked yet"}
                </Badge>
                <Badge variant="outline">MFA: coming soon</Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                SSO connections (Okta, Entra ID, Google Workspace, Ping, etc.) are managed through
                your ATLASOPS identity configuration. Users only enter their work email — they never
                choose a provider.
              </p>
              <div className="space-y-1.5">
                <Label htmlFor="domains">Allowed email domains</Label>
                <Input
                  id="domains"
                  value={domainsText}
                  onChange={(e) => setDomainsText(e.target.value)}
                  placeholder="company.com, company.co.uk"
                />
                <p className="text-xs text-muted-foreground">
                  Used for organization discovery when teammates sign in with a matching work email.
                </p>
              </div>
              <Button size="sm" onClick={saveDomains} disabled={saving}>
                {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Save domains
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Organization sessions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {orgSessions.length === 0 && (
                <p className="text-sm text-muted-foreground">No active organization sessions.</p>
              )}
              {orgSessions.map((s) => (
                <div
                  key={s.id}
                  className="flex flex-col gap-2 rounded-lg border border-border px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="space-y-1 text-sm">
                    <div className="font-medium">{s.user_email || "Member"}</div>
                    <p className="text-xs text-muted-foreground">
                      {s.device_label || "Device"} · {s.ip_address || "—"} · {fmt(s.last_seen_at)}
                    </p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => revokeOrg(s.id)}>
                    Revoke
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Login history</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {history.length === 0 && (
                <p className="text-sm text-muted-foreground">No authentication events yet.</p>
              )}
              {history.map((h) => (
                <div
                  key={h.id}
                  className="flex flex-col gap-0.5 border-b border-border py-2 text-sm last:border-0"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium">{h.action.replaceAll("_", " ")}</span>
                    <span className="text-xs text-muted-foreground">{fmt(h.created_at)}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {h.user_email || "—"}
                    {h.ip_address ? ` · ${h.ip_address}` : ""}
                    {h.detail ? ` · ${h.detail}` : ""}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
