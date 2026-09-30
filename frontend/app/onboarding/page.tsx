"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, Loader2 } from "lucide-react";
import { api, setOrgId } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Organization } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingState } from "@/components/shared/states";

export default function OnboardingOrgPage() {
  const { user, currentOrganization, loading, refresh } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!loading && user && currentOrganization) {
      router.replace("/onboarding/plan");
    }
  }, [loading, user, currentOrganization, router]);

  if (loading || !user) {
    return <LoadingState label="Loading…" />;
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const org = await api.post<Organization>("/orgs", { name: name.trim() });
      setOrgId(org.id);
      await refresh();
      router.push("/onboarding/plan");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create organization");
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Building2 className="h-5 w-5 text-primary" />
          Create your organization
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Supply is multi-tenant. Start by naming the workspace your team will operate in.
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="org-name">Organization name</Label>
            <Input
              id="org-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Logistics"
              minLength={2}
              required
              autoFocus
            />
          </div>
          {error && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
          )}
          <Button type="submit" disabled={submitting || name.trim().length < 2}>
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Continue
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
