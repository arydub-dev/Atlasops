"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import type { IncidentDetail } from "@/lib/types";
import { relativeTime, titleCase } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Markdown } from "@/components/shared/markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import Link from "next/link";

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { data, loading, error, refetch } = useFetch<IncidentDetail>(`/incidents/${params.id}`, [
    params.id,
  ]);
  const { user, currentMembership } = useAuth();
  const canResolve = ["owner", "admin", "operations_director", "operations_manager", "warehouse_manager", "transportation"].includes(currentMembership?.role_slug || "");
  const [actionError, setActionError] = useState("");
  const [resolution, setResolution] = useState("");
  const [busy, setBusy] = useState(false);

  async function resolve() {
    if (!resolution.trim() || busy) return;
    setBusy(true);
    setActionError("");
    try {
      await api.post(`/incidents/${params.id}/resolve`, { resolution: resolution.trim() });
      await refetch();
      setResolution("");
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not resolve incident");
    } finally {
      setBusy(false);
    }
  }

  async function progress(body: { status?: string; assign_to_me?: boolean }) {
    if (busy) return;
    setBusy(true); setActionError("");
    try { await api.patch(`/incidents/${params.id}`, body); await refetch(); }
    catch (e) { setActionError(e instanceof Error ? e.message : "Update failed"); }
    finally { setBusy(false); }
  }

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error || "Incident not found"} />;

  const open = !["resolved", "closed"].includes(data.status);

  return (
    <div className="space-y-6">
      <PageHeader title={data.title} description="Incident investigation workspace">
        <Button variant="outline" size="sm" onClick={() => router.push("/incidents")}>
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Button>
        <Badge variant={data.severity === "critical" || data.severity === "high" ? "destructive" : "warning"}>
          {data.severity}
        </Badge>
        <Badge variant="secondary">{titleCase(data.status)}</Badge>
      </PageHeader>

      {actionError && <p role="alert" className="text-destructive">{actionError}</p>}
      {open && canResolve && <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" disabled={busy || data.owner_user_id === user?.id} onClick={() => progress({assign_to_me:true})}>{data.owner_user_id === user?.id ? "Assigned to you" : "Assign to me"}</Button>
        {data.status === "open" && <Button disabled={busy} onClick={() => progress({status:"investigating"})}>Start investigation</Button>}
        {data.status === "investigating" && <Button disabled={busy} onClick={() => progress({status:"mitigating"})}>Start mitigation</Button>}
      </div>}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-8">
          <CardHeader>
            <CardTitle className="text-sm">{data.ai_summary ? "AI Summary" : "Incident Summary"}</CardTitle>
          </CardHeader>
          <CardContent>
            {data.ai_summary || data.summary ? (
              <Markdown content={data.ai_summary || data.summary || ""} />
            ) : (
              <p className="text-sm text-muted-foreground">No summary generated yet.</p>
            )}
            {data.recommendations && data.recommendations.length > 0 && (
              <div className="mt-4 space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Recommendations
                </p>
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {data.recommendations.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle className="text-sm">Affected Entities</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(data.affected_entities || []).length === 0 && (
              <p className="text-xs text-muted-foreground">No linked entities</p>
            )}
            {(data.affected_entities || []).map((e, i) => (
              <Link
                key={i}
                href={`/graph?type=${e.type}&id=${e.id}`}
                className="block rounded-md border border-border/60 px-3 py-2 text-xs hover:bg-accent/40"
              >
                <span className="font-medium capitalize">{e.type}</span>
                <span className="ml-2 text-muted-foreground">{e.label || e.id.slice(0, 8)}</span>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="relative border-l border-border/70 pl-4">
            {(data.timeline || []).map((e) => (
              <li key={e.id} className="pb-4 last:pb-0">
                <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-primary" />
                <div className="flex justify-between gap-2">
                  <p className="text-sm font-medium">{e.title}</p>
                  {e.occurred_at && (
                    <span className="text-[11px] text-muted-foreground">{relativeTime(e.occurred_at)}</span>
                  )}
                </div>
                {e.summary && <p className="text-xs text-muted-foreground">{e.summary}</p>}
              </li>
            ))}
            {(data.timeline || []).length === 0 && (
              <p className="text-sm text-muted-foreground">No timeline events yet.</p>
            )}
          </ol>
        </CardContent>
      </Card>

      {open && canResolve ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Resolve Incident</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 sm:flex-row">
            <Input
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              placeholder="Resolution notes — what fixed the issue"
            />
            <Button onClick={resolve} disabled={busy || !resolution.trim()}>
              <CheckCircle2 className="h-3.5 w-3.5" /> Resolve
            </Button>
          </CardContent>
        </Card>
      ) : !open ? (
        <Card>
          <CardContent className="pt-5 text-sm">
            <p className="font-medium">Resolved</p>
            <p className="mt-1 text-muted-foreground">{data.resolution}</p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
