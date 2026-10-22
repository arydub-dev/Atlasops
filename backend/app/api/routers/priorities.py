from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.deps import get_db_with_tenant, require_permission
from app.models import Incident, Inventory, Shipment, AuditLog, ImportJob, AIReport, Organization
from app.models.enums import IncidentSeverity, IncidentStatus
from app.services.priorities import operational_priorities
from app.services.audit import write_audit
from app.tenancy.context import TenantContext

router=APIRouter(prefix='/priorities',tags=['Operational priorities'],dependencies=[
    Depends(require_permission(p)) for p in ['inventory.read','shipments.read','suppliers.read','warehouses.read','alerts.read']])

@router.get('')
def feed(db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('mission.read'))):
    result=operational_priorities(db,ctx.organization_id)
    result['items']=result['items'][:50]
    return result

def find(db,org_id,kind,entity_id):
    key=f'{kind}:{entity_id}'
    row=next((i for i in operational_priorities(db,org_id)['items'] if i['id']==key),None)
    if row is None: raise HTTPException(404,'This priority no longer exists or is outside your organization')
    return row

@router.get('/usage/summary')
def usage(db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('org.usage.read'))):
    org_id=ctx.organization_id
    def count(model,*conditions):
        return db.scalar(select(func.count()).select_from(model).where(model.organization_id==org_id,*conditions)) or 0
    org=db.get(Organization,org_id)
    return {'scope':'Current organization, all stored history; seeded records included',
        'synthetic_workspace':bool((org.settings or {}).get('demo_dataset')),
        'imports':count(ImportJob),'accepted_import_rows':db.scalar(select(func.coalesce(func.sum(ImportJob.rows_imported),0)).where(ImportJob.organization_id==org_id)),
        'incidents_created':count(Incident),'incidents_resolved':count(Incident,Incident.status==IncidentStatus.RESOLVED),
        'stored_ai_reports':count(AIReport),'recommendation_view_events':count(AuditLog,AuditLog.action=='recommendation_viewed'),
        'users_who_viewed_recommendations':db.scalar(select(func.count(func.distinct(AuditLog.user_id))).where(AuditLog.organization_id==org_id,AuditLog.action=='recommendation_viewed')),
        'current_detected_problems':operational_priorities(db,org_id)['total']}


@router.get('/{kind}/{entity_id}')
def detail(kind:str,entity_id:UUID,db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('mission.read'))):
    return find(db,ctx.organization_id,kind,entity_id)

class Action(BaseModel):
    notes:str=Field(default='',max_length=4000)

@router.post('/{kind}/{entity_id}/view')
def record_view(kind:str,entity_id:UUID,db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('mission.read'))):
    item=find(db,ctx.organization_id,kind,entity_id)
    write_audit(db,organization_id=ctx.organization_id,user_id=ctx.user_id,action='recommendation_viewed',resource='priority',resource_id=item['id'])
    db.commit()
    return {'recorded':True}

@router.post('/{kind}/{entity_id}/incident')
def act(kind:str,entity_id:UUID,payload:Action,db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('alerts.create'))):
    model=Inventory if kind=='inventory' else Shipment if kind=='shipment' else None
    if model is None: raise HTTPException(404,'Priority not found')
    if db.scalar(select(model).where(model.id==entity_id,model.organization_id==ctx.organization_id).with_for_update()) is None:
        raise HTTPException(404,'Priority not found')
    item=find(db,ctx.organization_id,kind,entity_id)
    active=next((i for i in item['incidents'] if i['status'] not in ['resolved','closed']),None)
    if active: return {'id':active['id'],'created':False}
    incident=Incident(organization_id=ctx.organization_id,title=item['title'][:255],
        severity=IncidentSeverity(item['severity']),status=IncidentStatus.OPEN,owner_user_id=ctx.user_id,
        summary=item['explanation'] + ('\nOperator note: '+payload.notes if payload.notes else ''),
        affected_entities=item['entities'],recommendations=[item['recommendation']])
    db.add(incident); db.flush()
    write_audit(db,organization_id=ctx.organization_id,user_id=ctx.user_id,action='priority_incident_created',
        resource='incident',resource_id=str(incident.id),detail=item['id'])
    db.commit()
    return {'id':str(incident.id),'created':True}
