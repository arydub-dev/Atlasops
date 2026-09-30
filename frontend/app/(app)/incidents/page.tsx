"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Plus, Siren } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import type { IncidentSummary } from "@/lib/types";
import { relativeTime, titleCase } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const SEV: Record<string, "destructive" | "warning" | "secondary" | "default"> = {
  critical: "destructive",
  high: "destructive",
  medium: "warning",
  low: "secondary",
};

export default function IncidentsPage() {
  const router = useRouter();
  const { data, loading, error } = useFetch<IncidentSummary[]>("/incidents");
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);

  async function createIncident() {
    if (!title.trim() || busy) return;
    setBusy(true);
    try {
      const created = await api.post<{ id: string }>("/incidents", {
        title: title.trim(),
        severity: "high",
      });
      setTitle("");
      setCreating(false);
      router.push(`/incidents/${created.id}`);
    } catch {
      setBusy(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  const items = data || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Incidents"
        description="First-class operational incidents linked to alerts, risks, and graph entities."
      >
        <Button size="sm" onClick={() => setCreating((v) => !v)}>
          <Plus className="h-3.5 w-3.5" /> New incident
        </Button>
      </PageHeader>

      {creating && (
        <Card>
          <CardContent className="flex flex-col gap-3 pt-5 sm:flex-row">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Incident title — e.g. Supplier disruption impacting West Coast DCs"
              onKeyDown={(e) => e.key === "Enter" && createIncident()}
            />
            <Button onClick={createIncident} disabled={busy || !title.trim()}>
              Create
            </Button>
          </CardContent>
        </Card>
      )}

      {items.length === 0 ? (
        <EmptyState
          icon={Siren}
          title="No incidents"
          message="Create an incident from open alerts or start one manually to track resolution."
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-left text-[11px] uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-2.5 font-medium">Severity</th>
                <th className="px-4 py-2.5 font-medium">Incident</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="hidden px-4 py-2.5 font-medium md:table-cell">Affected</th>
                <th className="px-4 py-2.5 text-right font-medium">Opened</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((inc) => (
                <tr key={inc.id} className="hover:bg-accent/30">
                  <td className="px-4 py-3">
                    <Badge variant={SEV[inc.severity] || "secondary"}>{inc.severity}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/incidents/${inc.id}`} className="font-medium hover:underline">
                      {inc.title}
                    </Link>
                    {inc.summary && (
                      <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{inc.summary}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs capitalize">{titleCase(inc.status)}</td>
                  <td className="hidden px-4 py-3 text-xs text-muted-foreground md:table-cell">
                    {inc.affected_count ?? 0} entities
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                    {inc.created_at ? relativeTime(inc.created_at) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
