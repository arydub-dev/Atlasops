"use client";
import Link from 'next/link';
import { useFetch } from '@/lib/use-fetch';
import { PageHeader } from '@/components/shared/page-header';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ErrorState, LoadingState } from '@/components/shared/states';
import type { Priority } from '@/lib/priorities';

export default function OperationsPage() {
  const {data,loading,error,refetch}=useFetch<{counts:Record<string,number>;items:Priority[];total:number;inventory_positions:number;ranking:string}>('/priorities');
  if(loading)return <LoadingState/>;
  if(error||!data)return <ErrorState message={error||'Could not load priorities'} onRetry={()=>refetch()}/>;
  return <div className="space-y-6">
    <PageHeader title="What needs attention?" description="AtlasOps turns fragmented supply-chain data into a prioritized list of problems and recommended actions for operations teams.">
      <Link href="/data-sources/import" className="text-sm font-medium text-primary underline">Import CSV / Excel</Link>
    </PageHeader>
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">{Object.entries({critical:'Critical issues',low_stock:'Low-stock positions',overstock:'Overstock positions',shipment_risks:'Shipment risks',open_incidents:'Open incidents'}).map(([key,label])=><Card key={key}><CardContent className="pt-5"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-semibold">{data.counts[key]}</p></CardContent></Card>)}</div>
    <p className="text-sm text-muted-foreground">Based on {data.inventory_positions} current inventory positions and recorded shipments. {data.ranking}</p>
    {!data.items.length&&<Card><CardContent className="space-y-3 pt-5"><h2 className="font-semibold">{data.inventory_positions?'No problems detected by the current rules.':'Start with your operational data.'}</h2><p className="text-sm text-muted-foreground">Upload warehouses and products, then inventory and shipments. Review missing or rejected records before relying on the results.</p><Link href="/data-sources/import" className="text-primary underline">Upload data</Link></CardContent></Card>}
    <div className="space-y-3">{data.items.map(item=><Link key={item.id} href={`/priorities/${item.id.replace(':','/')}`} className="block rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"><Card className="transition-colors hover:border-primary"><CardContent className="space-y-3 pt-5"><Badge variant={item.severity==='critical'?'destructive':'warning'}>{item.severity}</Badge><h2 className="text-lg font-semibold">{item.title}</h2><p className="text-sm text-muted-foreground">{item.explanation}</p><p className="text-sm"><strong>Recommended action: </strong>{item.recommendation}</p><p className="text-xs text-primary">View evidence and track an action →</p></CardContent></Card></Link>)}</div>
    {data.total>data.items.length&&<p className="text-sm text-muted-foreground">Showing the first {data.items.length} of {data.total} priorities. Review remaining positions in Inventory and Shipments.</p>}
  </div>;
}
