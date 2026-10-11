"""Current, explainable operational priorities. No prediction or cached alert dependency."""
from sqlalchemy import select
from app.models import Inventory, Product, Warehouse, Supplier, Shipment, Incident
from app.models.enums import ShipmentStatus, IncidentStatus
from app.services.inventory_logic import inventory_status, days_of_supply, reorder_recommendation


def operational_priorities(db, org_id):
    inventory = db.execute(select(Inventory, Product, Warehouse)
        .join(Product, Inventory.product_id == Product.id).join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .where(Inventory.organization_id == org_id, Product.organization_id == org_id,
               Warehouse.organization_id == org_id, Inventory.is_current.is_(True))).all()
    suppliers = {s.id:s.name for s in db.scalars(select(Supplier).where(Supplier.organization_id == org_id))}
    shipments = db.scalars(select(Shipment).where(Shipment.organization_id == org_id,
        Shipment.status.in_([ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELAYED, ShipmentStatus.CUSTOMS_HOLD]))).all()
    incidents = db.scalars(select(Incident).where(Incident.organization_id == org_id).order_by(Incident.created_at.desc())).all()
    items = []
    counts = {'critical':0,'low_stock':0,'overstock':0,'shipment_risks':0,
              'open_incidents':sum(i.status not in {IncidentStatus.RESOLVED,IncidentStatus.CLOSED} for i in incidents)}
    def shipment_fact(s):
        return {'id':str(s.id),'reference':s.reference,'status':s.status.value,'units':s.units,
                'delay_days':s.delay_days,'eta':s.eta.isoformat() if s.eta else None,
                'supplier':suppliers.get(s.supplier_id)}
    for inv,product,warehouse in inventory:
        state=inventory_status(inv)
        if state=='ok': continue
        cover=days_of_supply(inv.quantity,inv.avg_daily_demand)
        shortage=state in {'low_stock','stockout'}
        severity='critical' if shortage and (inv.quantity<=0 or (cover is not None and cover<=3)) else 'high' if shortage else 'medium'
        counts['low_stock' if shortage else 'overstock']+=1
        counts['critical']+=severity=='critical'
        incoming=[shipment_fact(s) for s in shipments if s.product_id==product.id and s.warehouse_id==warehouse.id]
        recommendation=reorder_recommendation(inv)
        entities=[{'type':'inventory','id':str(inv.id)},{'type':'product','id':str(product.id),'label':product.sku},
                  {'type':'warehouse','id':str(warehouse.id),'label':warehouse.name}]
        entities += [{'type':'shipment','id':s['id'],'label':s['reference']} for s in incoming]
        items.append({'id':f'inventory:{inv.id}','kind':'inventory','severity':severity,
            'title':f'{product.sku}: {"stock shortage" if shortage else "excess stock"} at {warehouse.name}',
            'explanation':f'{inv.quantity} units compared with a reorder threshold of {inv.reorder_point} and target stock of {inv.max_stock or inv.reorder_point*2}.',
            'recommendation':f'Review replenishment of {recommendation} units and confirm inbound delivery dates.' if shortage else 'Pause replenishment and review excess stock against demand.',
            'method':'Rule-based replenishment: max(target stock − current quantity, 0) when at or below threshold. Incoming stock and reservations are not netted. Shipment links show association, not proven causation.',
            'facts':{'sku':product.sku,'product':product.name,'warehouse':warehouse.name,'supplier':suppliers.get(product.supplier_id),
                'quantity':inv.quantity,'threshold':inv.reorder_point,'target_stock':inv.max_stock or inv.reorder_point*2,
                'days_of_supply':cover,'average_daily_demand':inv.avg_daily_demand,'replenishment_units':recommendation,
                'snapshot_at':inv.snapshot_date.isoformat() if inv.snapshot_date else None},
            'incoming_shipments':incoming,'entities':entities})
    for shipment in shipments:
        if shipment.status not in {ShipmentStatus.DELAYED,ShipmentStatus.CUSTOMS_HOLD} and not shipment.delay_days: continue
        counts['shipment_risks']+=1
        items.append({'id':f'shipment:{shipment.id}','kind':'shipment','severity':'high',
            'title':f'{shipment.reference}: delivery needs attention',
            'explanation':f'Status {shipment.status.value}; recorded delay {shipment.delay_days} days.',
            'recommendation':'Confirm the delivery date with the supplier and review affected inventory.',
            'method':'Observed shipment status and recorded delay; not a predicted delivery probability.',
            'facts':shipment_fact(shipment),'incoming_shipments':[],
            'entities':[{'type':'shipment','id':str(shipment.id),'label':shipment.reference}]})
    for item in items:
        def related(incident):
            links={(e.get('type'),e.get('id')) for e in (incident.affected_entities or [])}
            if (item['kind'],item['id'].split(':',1)[1]) in links: return True
            pair={(e['type'],e['id']) for e in item['entities'] if e['type'] in {'product','warehouse'}}
            return item['kind']=='inventory' and len(pair)==2 and pair.issubset(links)
        item['incidents']=[{'id':str(i.id),'title':i.title,'status':i.status.value} for i in incidents
            if related(i)]
    items.sort(key=lambda i:({'critical':0,'high':1,'medium':2}[i['severity']],
        i['facts'].get('days_of_supply') if i['facts'].get('days_of_supply') is not None else 1e12,i['id']))
    return {'counts':counts,'items':items,'total':len(items),'inventory_positions':len(inventory),
        'ranking':'Severity first, then recorded days of stock coverage. Resolving an incident does not change physical inventory.'}
