export interface Priority {
  id:string; kind:string; severity:string; title:string; explanation:string; recommendation:string; method:string;
  facts:Record<string,string|number|null>;
  incoming_shipments:{id:string;reference:string;status:string;units:number;delay_days:number;eta:string|null;supplier:string|null}[];
  incidents:{id:string;title:string;status:string}[];
}
