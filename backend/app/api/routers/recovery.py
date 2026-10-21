"""Recovery decision support: no external writes, messages or model calls."""
from datetime import datetime,timezone
import json
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Form
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_db_with_tenant,require_permission
from app.core.uploads import assert_safe_upload,ALLOWED_IMPORT_EXTENSIONS
from app.core.rate_limit import rate_limit_upload
from app.models import RecoveryRecord,RecoveryCase,Incident,AuditLog,Organization
from app.models.enums import IncidentSeverity,IncidentStatus
from app.services import ingestion
from app.services.audit import write_audit
from app.services.recovery import engine,store,simulator
from app.services.recovery.contracts import CONTRACTS,validate
from app.tenancy.context import TenantContext
router=APIRouter(prefix='/recovery',tags=['Recovery'])

def now():return datetime.now(timezone.utc)
def inputs(db,ctx,permission='recovery.read'):
    store.require(ctx,permission)
    if permission in ('recovery.manage','recovery.approve'):
        db.scalar(select(Organization).where(Organization.id==ctx.organization_id).with_for_update())
    return store.snapshot(db,ctx.organization_id)
def report(db,ctx):
    records,stock,catalog,fingerprint=inputs(db,ctx)
    return {**engine.calculate(records,stock,catalog,now()),'fingerprint':fingerprint}

def owned(db,model,id,ctx):
    row=db.scalar(select(model).where(model.id==id,model.organization_id==ctx.organization_id).with_for_update())
    if row is None:raise HTTPException(404,'Recovery record not found')
    return row

@router.get('/overview')
def overview(db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.read'))):
    return report(db,ctx)

@router.get('/records')
def records(db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.read'))):
    return inputs(db,ctx)[0]

@router.get('/contracts')
def contracts(ctx:TenantContext=Depends(require_permission('recovery.read'))):
    return {kind:model.model_json_schema() for kind,model in CONTRACTS.items()}

@router.post('/import/{kind}',dependencies=[Depends(rate_limit_upload)])
def upload(kind:str,file:UploadFile=File(...),sheet:str|None=Form(None),db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.manage'))):
    store.require(ctx,'recovery.manage')
    if 'imports.create' not in ctx.permissions:raise HTTPException(403,'Import permission required')
    content=file.file.read(15*1024*1024+1)
    assert_safe_upload(filename=file.filename or '',content_type=file.content_type,size=len(content),allowed_extensions=ALLOWED_IMPORT_EXTENSIONS,max_bytes=15*1024*1024)
    try: parsed=ingestion.parse_upload(file.filename or '',content,sheet)
    except ValueError:raise HTTPException(422,'File could not be parsed') from None
    return store.import_records(db,ctx,kind,parsed['rows'])

class Correction(BaseModel):
    expected:dict
    corrected:dict
    reason:str=Field(min_length=5,max_length=2000)

@router.patch('/records/{id}')
def correct(id:UUID,payload:Correction,db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.manage'))):
    store.require(ctx,'recovery.manage');row=owned(db,RecoveryRecord,id,ctx)
    if row.data!=payload.expected:raise HTTPException(409,'Source changed; reload before correcting')
    try:data=validate(row.kind,payload.corrected)
    except ValueError:raise HTTPException(422,'Invalid corrected record') from None
    if data['record_id']!=row.source_key:raise HTTPException(422,'Source identity cannot be changed')
    write_audit(db,organization_id=ctx.organization_id,user_id=ctx.user_id,action='recovery.correct',resource='recovery_record',resource_id=str(id),detail=json.dumps({'original':row.data,'corrected':data,'reason':payload.reason}))
    row.data=data;db.commit();return store.serialize(row)

@router.get('/planner')
def planner(work_order:str,db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.read'))):
    records,stock,catalog,fingerprint=inputs(db,ctx)
    return {**engine.options(records,stock,catalog,now(),work_order),'fingerprint':fingerprint}

class Choice(BaseModel):
    work_order:str=Field(min_length=1,max_length=160)
    option_id:str
    fingerprint:str
    rationale:str=Field(min_length=5,max_length=2000)
    due_at:datetime

@router.post('/cases',status_code=201)
def choose(payload:Choice,db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.manage'))):
    records,stock,catalog,fingerprint=inputs(db,ctx,'recovery.manage')
    if 'alerts.create' not in ctx.permissions:raise HTTPException(403,'Incident creation permission required')
    if payload.due_at.tzinfo is None:raise HTTPException(422,'Due date needs a timezone')
    if fingerprint!=payload.fingerprint:raise HTTPException(409,'Source records changed; recompute the plan')
    plan=engine.options(records,stock,catalog,now(),payload.work_order)
    option=next((o for o in plan['options'] if o['id']==payload.option_id and o['feasible']),None)
    if not option:raise HTTPException(422,'Select a supported feasible option')
    reject_overlap(db,ctx,option,simulator_only=True)
    incident=Incident(organization_id=ctx.organization_id,title='Recovery: '+payload.work_order,severity=IncidentSeverity.HIGH,status=IncidentStatus.OPEN,owner_user_id=ctx.user_id,summary=payload.rationale,affected_entities=[{'type':'work_order','id':payload.work_order}],recommendations=plan['options'],linked_alert_ids=[],linked_risk_ids=[])
    db.add(incident);db.flush()
    case=RecoveryCase(organization_id=ctx.organization_id,incident_id=incident.id,work_order=payload.work_order,status='proposed',data={'plan':plan,'chosen':option,'fingerprint':fingerprint,'rationale':payload.rationale,'owner':str(ctx.user_id),'due_at':payload.due_at.astimezone(timezone.utc).isoformat(),'proposed_at':now().isoformat()})
    db.add(case);db.flush()
    write_audit(db,organization_id=ctx.organization_id,user_id=ctx.user_id,action='recovery.propose',resource='recovery_case',resource_id=str(case.id),detail=json.dumps(case.data))
    db.commit();return {'id':str(case.id),'incident_id':str(incident.id)}

@router.get('/cases')
def cases(db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.read'))):
    store.require(ctx)
    rows=db.execute(select(RecoveryCase,Incident).join(Incident,Incident.id==RecoveryCase.incident_id).where(RecoveryCase.organization_id==ctx.organization_id,Incident.organization_id==ctx.organization_id).order_by(RecoveryCase.created_at.desc()).limit(501)).all()
    if len(rows)>500:raise HTTPException(413,'Case history exceeds the supervised-pilot report limit')
    return [{'id':str(c.id),'incident_id':str(c.incident_id),'work_order':c.work_order,'status':c.status,'data':c.data,'incident_status':i.status.value,'assigned_user_id':str(i.owner_user_id) if i.owner_user_id else None,'opened_at':c.created_at.isoformat(),'resolved_at':i.resolved_at.isoformat() if i.resolved_at else None} for c,i in rows]

@router.post('/cases/{id}/approve')
def approve(id:UUID,db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.approve'))):
    records,stock,catalog,fingerprint=inputs(db,ctx,'recovery.approve');case=owned(db,RecoveryCase,id,ctx)
    if case.status!='proposed':raise HTTPException(409,'Only proposed cases may be approved')
    if fingerprint!=case.data['fingerprint']:raise HTTPException(409,'Source records changed; a new plan is required')
    if case.data.get('simulator'):
        try: comparison=simulator.compare(records,stock,catalog,now(),case.data['work_orders'])
        except ValueError as exc: raise HTTPException(409,str(exc)) from None
        selected=next((p for p in comparison['plans'] if p['id']==case.data['chosen']['id'] and p['feasible']),None)
        if not selected or selected['signature']!=case.data['chosen']['signature']:
            raise HTTPException(409,'Plan changed or is no longer feasible; create a new proposal')
        reject_overlap(db,ctx,selected,exclude=case.id)
    else:
        plan=engine.options(records,stock,catalog,now(),case.work_order)
        if not any(o['id']==case.data['chosen']['id'] and o['feasible'] for o in plan['options']):raise HTTPException(409,'Option no longer feasible')
        reject_overlap(db,ctx,{'evidence':case.data['chosen']['evidence']},exclude=case.id,simulator_only=True)
    case.status='approved';case.data={**case.data,'approved_by':str(ctx.user_id),'approved_at':now().isoformat()}
    write_audit(db,organization_id=ctx.organization_id,user_id=ctx.user_id,action='recovery.approve',resource='recovery_case',resource_id=str(id),detail='Human approved decision support; no external action executed')
    db.commit();return {'status':case.status,'external_action_executed':False}

class Outcome(BaseModel):
    reference:str=Field(min_length=3,max_length=255)
    notes:str=Field(min_length=5,max_length=4000)
    completed_at:datetime
    direct_cost:float|None=Field(default=None,ge=0,allow_inf_nan=False)
    currency:str|None=Field(default=None,min_length=3,max_length=3)

@router.post('/cases/{id}/outcome')
def outcome(id:UUID,payload:Outcome,db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.manage'))):
    store.require(ctx,'recovery.manage');case=owned(db,RecoveryCase,id,ctx)
    if case.status!='approved':raise HTTPException(409,'An approved case without a recorded outcome is required')
    if payload.completed_at.tzinfo is None or payload.completed_at>now():raise HTTPException(422,'Actual completion must be a timezone-aware past timestamp')
    current=report(db,ctx)
    final=next((o for o in current['orders'] if o['work_order']==case.work_order),None)
    deadlines=[engine.date(r['required_by']) for r in case.data['plan']['baseline']['requirements'] if r['required_by']]
    incident=db.scalar(select(Incident).where(Incident.id==case.incident_id,Incident.organization_id==ctx.organization_id))
    resolved_on_time=(final['status']=='READY' and incident is not None and incident.status==IncidentStatus.RESOLVED and now()<=min(deadlines)) if final and deadlines else None
    case.status='outcome_recorded';case.data={**case.data,'outcome':payload.model_dump(mode='json'),'recorded_by':str(ctx.user_id),'recorded_at':now().isoformat(),'final_readiness':final,'on_time':resolved_on_time,'action_completed_by_deadline':payload.completed_at<=min(deadlines) if deadlines else None}
    if case.data.get('simulator'):
        case.data={**case.data,'final_plan_readiness':current['orders'],'estimated_direct_cost':case.data['chosen']['known_direct_cost'],'estimated_currency':case.data['chosen']['currency']}
    write_audit(db,organization_id=ctx.organization_id,user_id=ctx.user_id,action='recovery.outcome',resource='recovery_case',resource_id=str(id),detail=json.dumps(case.data['outcome']))
    db.commit();return {'status':case.status,'final_readiness':final,'notice':'Outcome is user-recorded evidence; the linked incident follows its existing lifecycle.'}

@router.get('/audit')
def audit(db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.read'))):
    store.require(ctx)
    return [{'id':str(r.id),'at':r.created_at.isoformat(),'user':str(r.user_id),'action':r.action,'record_id':r.resource_id,'detail':r.detail} for r in db.scalars(select(AuditLog).where(AuditLog.organization_id==ctx.organization_id,AuditLog.resource.in_(['recovery_record','recovery_case'])).order_by(AuditLog.created_at.desc()).limit(500))]


class SimulationRequest(BaseModel):
    work_orders:list[str]=Field(min_length=1,max_length=8)

@router.post('/simulate')
def simulate(payload:SimulationRequest,db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.read'))):
    records,stock,catalog,fingerprint=inputs(db,ctx)
    try: result=simulator.compare(records,stock,catalog,now(),payload.work_orders)
    except ValueError as exc:raise HTTPException(422,str(exc)) from None
    return {**result,'fingerprint':fingerprint}

class PlanChoice(SimulationRequest):
    plan_id:str
    signature:str
    fingerprint:str
    rationale:str=Field(min_length=5,max_length=2000)
    due_at:datetime


def reject_overlap(db,ctx,plan,exclude=None,simulator_only=False):
    active=db.scalars(select(RecoveryCase).where(RecoveryCase.organization_id==ctx.organization_id,RecoveryCase.status.in_(['proposed','approved']))).all()
    evidence=set(plan.get('evidence',[]))
    for case in active:
        if case.id==exclude or (simulator_only and not case.data.get('simulator')):continue
        if evidence.intersection(case.data['chosen'].get('evidence',[])):
            raise HTTPException(409,'An active recovery decision already uses this evidence; review the existing incident first')

@router.post('/plan-cases',status_code=201)
def choose_plan(payload:PlanChoice,db:Session=Depends(get_db_with_tenant),ctx:TenantContext=Depends(require_permission('recovery.manage'))):
    records,stock,catalog,fingerprint=inputs(db,ctx,'recovery.manage')
    if 'alerts.create' not in ctx.permissions:raise HTTPException(403,'Incident creation permission required')
    if payload.due_at.tzinfo is None:raise HTTPException(422,'Due date needs a timezone')
    if fingerprint!=payload.fingerprint:raise HTTPException(409,'Source records changed; recompute the plan')
    try: comparison=simulator.compare(records,stock,catalog,now(),payload.work_orders)
    except ValueError as exc:raise HTTPException(422,str(exc)) from None
    chosen=next((p for p in comparison['plans'] if p['id']==payload.plan_id and p['feasible']),None)
    if not chosen or chosen['signature']!=payload.signature:raise HTTPException(409,'Plan changed or is unsupported; recompute before review')
    reject_overlap(db,ctx,chosen)
    primary=sorted(payload.work_orders)[0]
    incident=Incident(organization_id=ctx.organization_id,title='Recovery plan: '+primary,severity=IncidentSeverity.HIGH,status=IncidentStatus.OPEN,owner_user_id=ctx.user_id,summary=payload.rationale,affected_entities=[{'type':'work_order','id':o['work_order']} for o in comparison['baseline']['orders']],recommendations=[{'plan_id':p['id'],'description':p['description'],'limitations':p['limitations']} for p in comparison['plans']],linked_alert_ids=[],linked_risk_ids=[])
    db.add(incident);db.flush()
    case=RecoveryCase(organization_id=ctx.organization_id,incident_id=incident.id,work_order=primary,status='proposed',data={'simulator':True,'work_orders':comparison['work_orders'],'comparison':comparison,'plan':{'baseline':next(o for o in comparison['baseline']['orders'] if o['work_order']==primary)},'chosen':chosen,'fingerprint':fingerprint,'rationale':payload.rationale,'owner':str(ctx.user_id),'due_at':payload.due_at.astimezone(timezone.utc).isoformat(),'proposed_at':now().isoformat()})
    db.add(case);db.flush()
    write_audit(db,organization_id=ctx.organization_id,user_id=ctx.user_id,action='recovery.propose_plan',resource='recovery_case',resource_id=str(case.id),detail=json.dumps(case.data))
    db.commit();return {'id':str(case.id),'incident_id':str(incident.id),'external_action_executed':False}
