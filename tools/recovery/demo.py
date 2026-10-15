"""Generate synthetic CSV inputs; does not connect to any database or deployment."""
import csv
from datetime import datetime,timedelta,timezone
from pathlib import Path
import argparse

def generate(folder,now):
    folder.mkdir(parents=True,exist_ok=True)
    stamp=now.isoformat();deadline=(now+timedelta(days=3)).isoformat()
    datasets={
      'suppliers':[dict(name='Synthetic supplier',country='US',region='US',category='Synthetic demo',supplier_score=80,delivery_reliability=90,average_delay_days=1,order_fulfillment_rate=95,defect_rate=1)],
      'products':[dict(sku='SPARE-1',name='Synthetic pump spare',unit_cost=10,unit_price=20)],
      'warehouses':[dict(name=site,location='Synthetic plant',region='US',capacity=1000) for site in ['Plant A','Plant B']],
      'inventory':[dict(warehouse_name=site,product_sku='SPARE-1',quantity=q,reorder_point=1,safety_stock=0,max_stock=20,avg_daily_demand=1) for site,q in [('Plant A',2),('Plant B',10)]],
      'stock':[dict(record_id='stock-'+site[-1],source='Synthetic count sheet',source_updated_at=stamp,sku='SPARE-1',site=site,observed_quantity=q,reserved_quantity=0,usability='usable') for site,q in [('Plant A',2),('Plant B',10)]],
      'requirement':[dict(record_id='line-'+site[-1],source='Synthetic maintenance plan',source_updated_at=stamp,work_order='WO-'+site[-1],sku='SPARE-1',site=site,quantity=q,required_by=deadline,status='planned',asset='Pump-'+site[-1],priority=1) for site,q in [('Plant A',5),('Plant B',9)]],
      'inbound':[dict(record_id='PO-line-1',source='Synthetic supplier commitment',source_updated_at=stamp,po='PO-1',line='1',sku='SPARE-1',site='Plant A',supplier='Synthetic supplier',ordered_quantity=3,open_quantity=3,promised_at=(now+timedelta(days=5)).isoformat(),date_source='Synthetic confirmed promise',confirmed=True)],
      'rule':[
       dict(record_id='transfer-1',source='Synthetic transfer authorization',source_updated_at=stamp,action='transfer',sku='SPARE-1',site='Plant A',donor_site='Plant B',quantity=3,lead_days=1,direct_cost=25,currency='USD',approval_reference='AUTH-TRANSFER',owner='Materials planner',permitted=True),
       dict(record_id='expedite-1',source='Synthetic expedited commitment',source_updated_at=stamp,action='expedite',sku='SPARE-1',site='Plant A',quantity=3,lead_days=1,direct_cost=90,currency='USD',approval_reference='AUTH-EXPEDITE',inbound_record_id='PO-line-1',owner='Purchasing planner',permitted=True)]}
    for kind,rows in datasets.items():
        fields=sorted(set().union(*(r.keys() for r in rows)))
        with (folder/(kind+'.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    (folder/'README.txt').write_text('Synthetic Recovery Engine demo. Generated '+stamp+'\n\nImport suppliers.csv, products.csv, warehouses.csv and inventory.csv through the existing Data Sources importer (in that order).\nThen import stock.csv, requirement.csv, inbound.csv and rule.csv from Critical spares readiness > Import, selecting each matching record type.\nFiles are available at /recovery-demo/<filename>.csv.\n\nWO-A is short by 3. Plant B has 10 but needs 9: transferring 3 would create donor risk and must be rejected. The documented expedite option advances the existing 3-unit PO line without duplicating inbound. Its known direct cost is USD 90.\nChoose the expedite option, record a rationale and due date, propose it, and approve it in Resolution history. No purchase order or external system is changed.\nUse the linked incident for assignment and lifecycle updates. Record a synthetic actual outcome reference. Readiness remains unchanged until authorized source imports/corrections establish the new operational facts.\nFor a final READY result, review the inbound source and correct promised_at to the documented expedited date with a reason, or import a new current inventory snapshot plus an audited stock-evidence correction after receipt; do not count a received PO as still open.\n\nAfter seven days these files intentionally become stale. Regenerate synthetic dates with tools/recovery/demo.py; never silently refresh timestamps on real source data.\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('frontend/public/recovery-demo'));args=parser.parse_args()
    generate(args.output,datetime.now(timezone.utc))
