"""Scoped retrieval and audited persistence for recovery decision support."""
import hashlib
import json
from sqlalchemy import select
from fastapi import HTTPException
from app.models import RecoveryRecord, RecoveryCase, Inventory, Product, Warehouse
from app.services.audit import write_audit
from app.services.recovery.contracts import validate

READ_PERMISSIONS={'recovery.read','inventory.read','products.read','warehouses.read'}

def require(ctx,permission='recovery.read'):
    if not READ_PERMISSIONS.issubset(ctx.permissions) or permission not in ctx.permissions:
        raise HTTPException(403,'Recovery access requires the corresponding recovery and inventory/product/warehouse read permissions')

def serialize(row):
    return {'id':str(row.id),'kind':row.kind,'data':row.data,'updated_at':row.updated_at.isoformat()}

def snapshot(db,org):
    records=db.scalars(select(RecoveryRecord).where(RecoveryRecord.organization_id==org).order_by(RecoveryRecord.id).limit(10001)).all()
    positions=db.execute(select(Inventory,Product,Warehouse).join(Product,Product.id==Inventory.product_id).join(Warehouse,Warehouse.id==Inventory.warehouse_id).where(Inventory.organization_id==org,Product.organization_id==org,Warehouse.organization_id==org,Inventory.is_current.is_(True)).limit(10001)).all()
    if len(records)>10000 or len(positions)>10000: raise HTTPException(413,'Recovery analysis exceeds the supervised-pilot limit; do not interpret a partial dataset')
    products=db.scalars(select(Product.sku).where(Product.organization_id==org).limit(10001)).all()
    if len(products)>10000: raise HTTPException(413,'Recovery product catalog exceeds the supervised-pilot limit')
    data=[serialize(r) for r in records]
    stock=[{'id':str(i.id),'sku':p.sku,'site':w.name,'quantity':i.quantity,'snapshot_at':i.snapshot_date.isoformat() if i.snapshot_date else None} for i,p,w in positions]
    fingerprint=hashlib.sha256(json.dumps([data,sorted(stock,key=lambda p:p['id']),sorted(products)],sort_keys=True).encode()).hexdigest()
    return data,stock,set(products),fingerprint

def import_records(db,ctx,kind,raw):
    if not raw or len(raw)>5000: raise HTTPException(422,'Import must contain between 1 and 5000 rows')
    try: rows=[validate(kind,r) for r in raw]
    except ValueError as exc: raise HTTPException(422,'Invalid recovery input: '+str(exc).split('input_value')[0][:500]) from None
    keys=[r['record_id'] for r in rows]
    if len(set(keys))!=len(keys): raise HTTPException(422,'Duplicate source record IDs in one file')
    count=0
    for data in rows:
        row=db.scalar(select(RecoveryRecord).where(RecoveryRecord.organization_id==ctx.organization_id,RecoveryRecord.kind==kind,RecoveryRecord.source_key==data['record_id']).with_for_update())
        if row:
            if row.data!=data: raise HTTPException(409,'Existing source differs; use audited correction with a reason')
            continue
        row=RecoveryRecord(organization_id=ctx.organization_id,kind=kind,source_key=data['record_id'],data=data)
        db.add(row);db.flush();count+=1
        write_audit(db,organization_id=ctx.organization_id,user_id=ctx.user_id,action='recovery.import',resource='recovery_record',resource_id=str(row.id),detail=json.dumps({'original':data}))
    db.commit()
    return {'processed':len(rows),'created':count,'unchanged':len(rows)-count}
