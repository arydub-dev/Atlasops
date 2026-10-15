"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ErrorState, LoadingState } from "@/components/shared/states";

type Order = { work_order: string; status: string; requirements: { sku: string; site: string; shortfall: number | null }[] };
type RecoveryCase = { id: string; work_order: string; status: string; incident_id: string; incident_status: string; resolved_at: string | null };

export function ReadinessOverview() {
  const { currentOrganization } = useAuth();
  const [tour, setTour] = useState(true);
  const overview = useFetch<{ orders: Order[]; as_of: string }>("/recovery/overview", [currentOrganization?.id]);
  const cases = useFetch<RecoveryCase[]>("/recovery/cases", [currentOrganization?.id]);
  const demo = currentOrganization?.settings?.private_demo === true || currentOrganization?.settings?.demo_dataset === "atlas-manufacturing-v1";
  const attention = overview.data?.orders.filter(o => o.status !== "READY") ?? [];
  const pending = cases.data?.filter(c => c.status === "proposed" || c.status === "approved") ?? [];
  const resolved = cases.data?.filter(c => c.incident_status === "resolved").sort((a,b) => (b.resolved_at ?? "").localeCompare(a.resolved_at ?? "")) ?? [];
  return <section aria-label="Maintenance and recovery" className="space-y-4">
    {demo && <div className="rounded-lg border bg-muted/30 p-4">
      <div className="flex items-center justify-between gap-3"><h2 className="font-semibold">Explore the demo</h2><Button variant="ghost" onClick={() => setTour(!tour)}>{tour ? "Hide guide" : "Show guide"}</Button></div>
      {tour && <><p className="mt-2 text-sm text-muted-foreground">Use synthetic records to explore a decision. Approvals record intent; they do not move stock or contact suppliers.</p><ol className="mt-4 grid gap-3 text-sm md:grid-cols-3">
        <li><Link className="font-medium text-primary underline" href="/inventory">1. Review inventory exceptions</Link></li>
        <li><Link className="font-medium text-primary underline" href="/recovery">2. Investigate a critical spare shortage</Link></li>
        <li><Link className="font-medium text-primary underline" href="/recovery">3. Compare and record a recovery action</Link></li>
      </ol></>}
    </div>}
    <div className="grid gap-4 xl:grid-cols-2">
      <article className="rounded-lg border p-4">
        <h2 className="font-semibold">Maintenance requiring attention</h2>
        <p className="mt-1 text-sm text-muted-foreground">Work orders marked At Risk, Shortage or Unknown by the readiness calculation.</p>
        {overview.loading ? <LoadingState /> : overview.error ? <ErrorState message={overview.error} onRetry={overview.refetch} /> : <>
          <p className="my-3 text-2xl font-semibold">{attention.length} <span className="text-sm font-normal text-muted-foreground">of {overview.data?.orders.length ?? 0} recorded work orders</span></p>
          {attention.slice(0,5).map(o => <Link key={o.work_order} href="/recovery" className="flex flex-wrap items-center justify-between gap-2 border-t py-3 text-sm"><span><strong>{o.work_order}</strong><span className="block text-muted-foreground">{[...new Set(o.requirements.map(r=>`${r.sku} · ${r.site}`))].join(", ")}</span></span><Badge variant={o.status === "SHORTAGE" ? "destructive" : o.status === "UNKNOWN" ? "muted" : "warning"}>{o.status}</Badge></Link>)}
          {!attention.length && <p className="text-sm text-muted-foreground">{overview.data?.orders.length ? "No recorded work orders currently require attention." : "No maintenance requirements have been loaded. Readiness is not yet established."}</p>}
          <Link className="mt-3 inline-block text-sm text-primary underline" href="/recovery">Review all readiness calculations</Link>
        </>}
      </article>
      <article className="rounded-lg border p-4">
        <h2 className="font-semibold">Recovery actions and resolutions</h2>
        <p className="mt-1 text-sm text-muted-foreground">Proposed and approved cases awaiting a recorded outcome; recently resolved linked incidents.</p>
        {cases.loading ? <LoadingState /> : cases.error ? <ErrorState message={cases.error} onRetry={cases.refetch} /> : <>
          <p className="my-3 text-2xl font-semibold">{pending.length} <span className="text-sm font-normal text-muted-foreground">pending recovery cases</span></p>
          {pending.slice(0,3).map(c=><Link key={c.id} href={`/incidents/${c.incident_id}`} className="flex justify-between gap-2 border-t py-3 text-sm"><strong>{c.work_order}</strong><span>{c.status}</span></Link>)}
          {!pending.length && <p className="text-sm text-muted-foreground">No pending recovery decisions recorded.</p>}
          <h3 className="mt-4 text-sm font-semibold">Recently resolved</h3>
          {resolved.slice(0,3).map(c=><Link key={c.id} href={`/incidents/${c.incident_id}`} className="mt-2 block text-sm text-primary underline">{c.work_order} · Resolved {c.resolved_at ? new Date(c.resolved_at).toLocaleDateString() : "(date unavailable)"}</Link>)}
          {!resolved.length && <p className="mt-2 text-sm text-muted-foreground">No resolved recovery incidents recorded.</p>}
        </>}
      </article>
    </div>
  </section>;
}
