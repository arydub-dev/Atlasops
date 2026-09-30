"use client";

import Link from "next/link";
import { Building2, Key, ShieldAlert, Users, Webhook } from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import { api } from "@/lib/api";
import { canManageSecurity, useAuth } from "@/lib/auth";
import { roleLabel } from "@/lib/constants";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useState } from "react";

type Member = { id: string; email?: string; full_name?: string; role_slug: string; status: string };
type Token = { id: string; name: string; token_prefix?: string; revoked_at?: string | null };
type WebhookRow = { id: string; url: string; is_active: boolean };
type Audit = { id: string; action: string; resource: string; created_at: string };

export default function EnterpriseAdminPage() {
  const { currentOrganization, currentMembership } = useAuth();
  const isAdmin = canManageSecurity(currentMembership?.role_slug);
  const { data: members, loading } = useFetch<Member[]>(
    isAdmin ? "/orgs/current/members" : null
  );
  const { data: tokens, refetch: refetchTokens } = useFetch<Token[]>(
    isAdmin ? "/orgs/current/tokens" : null
  );
  const { data: webhooks } = useFetch<WebhookRow[]>(isAdmin ? "/orgs/current/webhooks" : null);
  const { data: audit } = useFetch<Audit[]>(isAdmin ? "/orgs/current/audit-logs" : null);
  const { data: security } = useFetch<{
    recommendations: string[];
    api_tokens: { active: number; total: number };
    failed_logins: unknown[];
  }>(isAdmin ? "/security-center" : null);
  const [busy, setBusy] = useState(false);

  async function emergencyLockout() {
    if (!isAdmin) return;
    if (!confirm("Revoke all sessions and API tokens for this organization?")) return;
    setBusy(true);
    try {
      await api.post("/security-center/emergency-lockout");
      await refetchTokens();
    } finally {
      setBusy(false);
    }
  }

  if (!isAdmin) {
    return (
      <ErrorState message="Enterprise Admin is limited to organization owners and administrators." />
    );
  }

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Enterprise Administration"
        description="Members, tokens, webhooks, audit, branding, and security controls."
      >
        <Link href="/settings/security">
          <Button variant="outline" size="sm">
            <ShieldAlert className="h-3.5 w-3.5" /> Security sessions
          </Button>
        </Link>
        <Button variant="destructive" size="sm" disabled={busy} onClick={emergencyLockout}>
          Emergency lockout
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardContent className="pt-5">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Building2 className="h-4 w-4" />
              <span className="text-xs uppercase">Organization</span>
            </div>
            <p className="mt-2 font-medium">{currentOrganization?.name}</p>
            <p className="text-xs text-muted-foreground">{currentOrganization?.slug}</p>
            <Badge className="mt-2" variant="secondary">
              {currentOrganization?.plan}
            </Badge>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs uppercase text-muted-foreground">API tokens</p>
            <p className="mt-2 text-3xl font-semibold">
              {security?.api_tokens?.active ?? tokens?.length ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">active of {security?.api_tokens?.total ?? "—"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs uppercase text-muted-foreground">Failed logins (14d)</p>
            <p className="mt-2 text-3xl font-semibold">{security?.failed_logins?.length ?? 0}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Users className="h-4 w-4" /> Members
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(members || []).map((m) => (
              <div key={m.id} className="flex justify-between text-sm">
                <span>{m.full_name || m.email || m.id.slice(0, 8)}</span>
                <Badge variant="secondary">{roleLabel(m.role_slug)}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="lg:col-span-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Key className="h-4 w-4" /> API keys
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(tokens || []).length === 0 && (
              <p className="text-xs text-muted-foreground">No tokens — create via API or billing tooling</p>
            )}
            {(tokens || []).map((t) => (
              <div key={t.id} className="flex items-center justify-between text-sm">
                <span>{t.name}</span>
                <Badge variant={t.revoked_at ? "outline" : "success"}>
                  {t.revoked_at ? "revoked" : "active"}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="lg:col-span-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Webhook className="h-4 w-4" /> Webhooks
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(webhooks || []).map((w) => (
              <div key={w.id} className="truncate text-xs">
                {w.url}{" "}
                <Badge variant={w.is_active ? "success" : "secondary"} className="ml-1">
                  {w.is_active ? "active" : "off"}
                </Badge>
              </div>
            ))}
            {(webhooks || []).length === 0 && (
              <p className="text-xs text-muted-foreground">No webhook endpoints configured</p>
            )}
          </CardContent>
        </Card>
        <Card className="lg:col-span-6">
          <CardHeader>
            <CardTitle className="text-sm">Audit trail</CardTitle>
          </CardHeader>
          <CardContent className="max-h-64 space-y-2 overflow-auto">
            {(audit || []).slice(0, 20).map((a) => (
              <div key={a.id} className="text-xs">
                <span className="font-medium">{a.action}</span>{" "}
                <span className="text-muted-foreground">on {a.resource}</span>
              </div>
            ))}
            {audit && audit.length === 0 && (
              <p className="text-xs text-muted-foreground">No audit entries recorded yet.</p>
            )}
            {!audit && (
              <p className="text-xs text-muted-foreground">Loading audit trail...</p>
            )}
          </CardContent>
        </Card>
      </div>

      {(security?.recommendations || []).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Security recommendations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {security!.recommendations.map((r, i) => (
              <p key={i} className="rounded-md bg-muted/40 px-3 py-2 text-xs">
                {r}
              </p>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
