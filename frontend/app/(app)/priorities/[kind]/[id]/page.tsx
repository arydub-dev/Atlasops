"use client";
import { useParams,useRouter } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { useFetch } from '@/lib/use-fetch';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import type { Priority } from '@/lib/priorities';
import { PageHeader } from '@/components/shared/page-header';
import { Card,CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ErrorState,LoadingState } from '@/components/shared/states';

export default function PriorityPage(){
  const params=useParams<{kind:string;id:string}>(); const router=useRouter();
  const {currentMembership}=useAuth();
  const path=`/priorities/${params.kind}/${params.id}`;
  const {data,loading,error}=useFetch<Priority>(path,[path]);
  const [notes,setNotes]=useState('');const [busy,setBusy]=useState(false);const [failure,setFailure]=useState('');
  const recorded=useRef('');
  useEffect(()=>{if(data&&recorded.current!==path){recorded.current=path;void api.post(path+'/view',{}).catch(()=>{recorded.current='';});}},[data,path]);
  async function act(){setBusy(true);setFailure('');try{const result=await api.post<{id:string}>(path+'/incident',{notes});router.push('/incidents/'+result.id);}catch(e){setFailure(e instanceof Error?e.message:'Could not create incident');}finally{setBusy(false);}}
  if(loading)return <LoadingState/>;if(error||!data)return <ErrorState message={error||'Priority no longer available'}/>;
  const canAct=['owner','admin','operations_director','operations_manager','demo_operator'].includes(currentMembership?.role_slug||'');
  return <div className="space-y-6"><Link href="/mission-control" className="text-sm text-primary underline">← Operational priorities</Link>
    <PageHeader title={data.title} description={data.severity+' priority · based on recorded data'}/>
    <Card><CardContent className="space-y-4 pt-5"><h2 className="font-semibold">What is happening?</h2><p>{data.explanation}</p><dl className="grid gap-4 sm:grid-cols-2">{Object.entries(data.facts).filter(([key])=>key!=='id').map(([key,value])=><div key={key}><dt className="text-xs uppercase text-muted-foreground">{key.replaceAll('_',' ')}</dt><dd className="mt-1 text-sm">{value===null?'Not available':String(value)}</dd></div>)}</dl></CardContent></Card>
    <Card><CardContent className="space-y-3 pt-5"><h2 className="font-semibold">Related incoming shipments</h2>{data.incoming_shipments.length?data.incoming_shipments.map(s=><div key={s.id} className="rounded border p-3"><Link href={'/shipments/'+s.id} className="font-medium text-primary underline">{s.reference}</Link><p className="text-sm">{s.status} · {s.units} units · recorded delay {s.delay_days} days</p><p className="text-sm text-muted-foreground">Supplier: {s.supplier||'Not available'} · ETA: {s.eta||'Not available'}</p></div>):<p className="text-sm text-muted-foreground">No linked active inbound shipment is recorded for this position. Missing relationships do not prove there is no inbound stock.</p>}</CardContent></Card>
    <Card><CardContent className="space-y-3 pt-5"><h2 className="font-semibold">Rule-based recommendation</h2><p>{data.recommendation}</p><p className="text-sm text-muted-foreground">{data.method}</p><Link href="/advisor" className="text-sm text-primary underline">Discuss recorded data with the advisor</Link></CardContent></Card>
    <Card><CardContent className="space-y-3 pt-5"><h2 className="font-semibold">Track the action</h2>{data.incidents.map(i=><Link key={i.id} href={'/incidents/'+i.id} className="block text-sm text-primary underline">{i.title} · {i.status}</Link>)}{canAct?<><label htmlFor="action-notes" className="text-sm">Operator note</label><Input id="action-notes" value={notes} onChange={e=>setNotes(e.target.value)} maxLength={4000} placeholder="What needs to happen next?"/><Button disabled={busy} onClick={act}>{busy?'Opening incident…':'Create or open incident'}</Button><p className="text-xs text-muted-foreground">Assigned to you. An existing open incident for this priority is reused.</p></>:<p className="text-sm text-muted-foreground">An operations account is required to create incidents.</p>}{failure&&<p role="alert" className="text-destructive">{failure}</p>}</CardContent></Card>
  </div>;
}
