from copy import deepcopy
from datetime import datetime, timedelta, timezone
import pytest
from app.services.recovery.simulator import compare
from test_recovery_engine import fixture,source,rule,inbound,NOW,imported  # noqa: F401


def simulate(rows,pos,selected=None):return compare(rows,pos,{'PART','SUB'},NOW,selected or ['WO-A','WO-B'])
def actions(result,n=1):return [p for p in result['plans'] if len(p['actions'])==n]


def test_transfer_donor_and_nonmutation():
    rows,pos=fixture();rows[3]['data']['quantity']=9;rows.append(rule());original=deepcopy((rows,pos))
    p=actions(simulate(rows,pos))[0]
    assert not p['feasible'] and p['new_shortages']==['WO-B']
    assert next(e for e in p['effects'] if e['work_order']=='WO-B')['after_shortfall']==2
    assert (rows,pos)==original


def test_shared_demand_and_combination():
    rows,pos=fixture()
    rows.append(source('requirement','WC',work_order='WO-C',sku='PART',site='Plant A',quantity=2,required_by=(NOW+timedelta(days=4)).isoformat()))
    rows.extend([rule(),source('rule','REPAIR',action='repair',sku='PART',site='Plant A',quantity=2,lead_days=2,permitted=True,approval_reference='ENG',repair_reference='ROTABLE-2: available quantity 2',direct_cost=10,currency='USD')])
    result=simulate(rows,pos,['WO-A','WO-C'])
    pair=next(p for p in actions(result,2) if p['feasible'])
    assert set(pair['restored_work_orders'])=={'WO-A','WO-C'}
    assert pair['known_direct_cost']==35
    assert all(e['after']=='READY' for e in pair['effects'])
    assert result['recommended_plan_id']==pair['id']


def test_overlapping_donor_consumption_blocked():
    rows,pos=fixture();rows[3]['data']['quantity']=6
    rows.append(source('requirement','WC',work_order='WO-C',sku='PART',site='Plant A',quantity=3,required_by=(NOW+timedelta(days=4)).isoformat()))
    rows.extend([rule(),{**rule(),'id':'RULE2'}])
    for p in actions(simulate(rows,pos,['WO-A','WO-C']),2):assert not p['feasible']


@pytest.mark.parametrize('change',[{'confirmed':False},{'promised_at':None},{'open_quantity':None}])
def test_uncertain_expedite_does_not_create_supported_readiness(change):
    rows,pos=fixture();rows.extend([inbound(**change),rule(action='expedite',inbound_record_id='PO')])
    assert not any(p['feasible'] for p in simulate(rows,pos)['plans'])


def test_expedite_keeps_inbound_once_and_unknown_cost():
    rows,pos=fixture();rows.append(source('requirement','WC',work_order='WO-C',sku='PART',site='Plant A',quantity=3,required_by=(NOW+timedelta(days=4)).isoformat()))
    rows.extend([inbound(promised_at=(NOW+timedelta(days=5)).isoformat()),rule(action='expedite',inbound_record_id='PO',direct_cost=None),{**rule(action='expedite',inbound_record_id='PO'),'id':'EXP2'}])
    result=simulate(rows,pos,['WO-A','WO-C'])
    assert not result['cost_comparison_enabled']
    for p in actions(result):
        assert sum(r['allocated_inbound'] for e in p['effects'] for r in e['requirements'])==3
    assert all(not p['feasible'] for p in actions(result,2))


@pytest.mark.parametrize('change',[{'lead_days':None},{'permitted':False},{'source_updated_at':'2020-01-01T00:00:00Z'},{'lead_days':10}])
def test_missing_stale_unauthorized_or_late_rule(change):
    rows,pos=fixture();rows.append(rule(**change));assert not any(p['feasible'] for p in simulate(rows,pos)['plans'])


def test_repair_identity_and_substitute_authorization():
    rows,pos=fixture();rows.append(rule(action='repair'))
    assert not actions(simulate(rows,pos))[0]['feasible']
    rows[-1]['data']['repair_reference']='Repair ticket R1 identifies available item and quantity'
    assert actions(simulate(rows,pos))[0]['feasible']
    rows[-1]=rule(action='substitute',substitute_sku='SUB')
    pos.append({'id':'IS','sku':'SUB','site':'Plant A','quantity':3})
    rows.append(source('stock','SS',sku='SUB',site='Plant A',observed_quantity=3,reserved_quantity=0,usability='usable'))
    assert actions(simulate(rows,pos))[0]['feasible']
    rows[-2]['data']['permitted']=False
    assert not actions(simulate(rows,pos))[0]['feasible']


def test_unknown_quantity_and_reservations():
    rows,pos=fixture();rows[0]['data']['reserved_quantity']=None;rows.append(rule())
    assert not any(p['feasible'] for p in simulate(rows,pos)['plans'])
    rows,pos=fixture();rows[1]['data']['reserved_quantity']=5;rows.append(rule())
    assert not actions(simulate(rows,pos))[0]['feasible']


def request_plan(client):
    r=client.post('/api/v1/recovery/simulate',json={'work_orders':['WO-A','WO-B']});assert r.status_code==200,r.text
    result=r.json();chosen=next(p for p in result['plans'] if p['feasible'])
    return {'work_orders':result['work_orders'],'plan_id':chosen['id'],'signature':chosen['signature'],'fingerprint':result['fingerprint'],'rationale':'Protect all imported active work orders','due_at':(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()}


def test_plan_persistence_revalidation_overlap_and_outcome(owner_client,imported):
    payload=request_plan(owner_client)
    r=owner_client.post('/api/v1/recovery/plan-cases',json=payload);assert r.status_code==201,r.text
    cid=r.json()['id']
    assert owner_client.post('/api/v1/recovery/plan-cases',json=payload).status_code==409
    approval=owner_client.post(f'/api/v1/recovery/cases/{cid}/approve');assert approval.status_code==200,approval.text
    history=owner_client.get('/api/v1/recovery/cases').json()[0]
    assert history['data']['comparison']['baseline']['orders'] and history['data']['simulator']
    assert owner_client.post(f'/api/v1/recovery/cases/{cid}/approve').status_code==409
    r=owner_client.post(f'/api/v1/recovery/cases/{cid}/outcome',json={'reference':'SAMPLE-RESULT','notes':'Documented outcome without source mutation','completed_at':datetime.now(timezone.utc).isoformat()});assert r.status_code==200,r.text
    assert len(owner_client.get('/api/v1/recovery/cases').json()[0]['data']['final_plan_readiness'])==2


def test_changed_source_blocks_proposal_and_approval(owner_client,imported):
    payload=request_plan(owner_client);r=owner_client.post('/api/v1/recovery/plan-cases',json=payload);assert r.status_code==201
    row=next(r for r in owner_client.get('/api/v1/recovery/records').json() if r['kind']=='rule')
    assert owner_client.patch('/api/v1/recovery/records/'+row['id'],json={'expected':row['data'],'corrected':{**row['data'],'lead_days':10},'reason':'Documented timing changed'}).status_code==200
    assert owner_client.post('/api/v1/recovery/plan-cases',json=payload).status_code==409
    assert owner_client.post('/api/v1/recovery/cases/'+r.json()['id']+'/approve').status_code==409


def test_simulator_tenant_and_role_boundaries(owner_client,db,org_a,org_b,viewer_user,imported):
    from fastapi.testclient import TestClient
    from app.main import app
    from conftest import _session_client
    foreign=_session_client(TestClient(app),db,org_b[2],org_b[0]);viewer=_session_client(TestClient(app),db,viewer_user,org_a[0])
    response=foreign.post('/api/v1/recovery/simulate',json={'work_orders':['WO-A']})
    assert response.status_code in (403,422)
    assert viewer.post('/api/v1/recovery/plan-cases',json=request_plan(owner_client)).status_code==403


def test_expired_evidence_rejects_approval_without_source_edit(owner_client,imported,monkeypatch):
    from app.api.routers import recovery
    payload=request_plan(owner_client);r=owner_client.post('/api/v1/recovery/plan-cases',json=payload);assert r.status_code==201
    monkeypatch.setattr(recovery,'now',lambda:datetime.now(timezone.utc)+timedelta(days=8))
    assert owner_client.post('/api/v1/recovery/cases/'+r.json()['id']+'/approve').status_code==409


def test_cost_ranking_requires_complete_common_currency():
    rows,pos=fixture();rows.extend([rule(),source('rule','REPAIR',action='repair',sku='PART',site='Plant A',quantity=3,lead_days=2,permitted=True,approval_reference='ENG',repair_reference='RT-1',direct_cost=None,currency='USD'),source('policy','POLICY',ranking='known_cost')])
    result=simulate(rows,pos);assert not result['cost_comparison_enabled']
    rows[-2]['data']['direct_cost']=10
    result=simulate(rows,pos);assert result['cost_comparison_enabled']
    assert next(p for p in result['plans'] if p['id']==result['recommended_plan_id'])['known_direct_cost']==10
    rows[-2]['data']['currency']='EUR';assert not simulate(rows,pos)['cost_comparison_enabled']


def test_simulation_api_nonmutation_and_copilot_grounding(owner_client,imported):
    before=owner_client.get('/api/v1/recovery/overview').json()
    request_plan(owner_client)
    after=owner_client.get('/api/v1/recovery/overview').json()
    assert before['fingerprint']==after['fingerprint'] and before['orders']==after['orders']
    assert owner_client.get('/api/v1/recovery/cases').json()==[]
    r=owner_client.post('/api/v1/ai/orchestrate',json={'prompt':'Compare a recovery plan for work orders WO-A and WO-B'})
    assert r.status_code==200,r.text
    assert 'First supported plan for human review' in r.json()['response'] and 'Evidence:' in r.json()['response']


def test_same_requirement_and_rule_cannot_be_consumed_twice():
    rows,pos=fixture();rows.extend([rule(),source('rule','REPAIR',action='repair',sku='PART',site='Plant A',quantity=3,lead_days=2,permitted=True,approval_reference='ENG',repair_reference='RT-1')])
    pair=actions(simulate(rows,pos),2)[0];assert not pair['feasible']
    assert any('same requirement' in s for s in pair['limitations'])


def test_withdrawal_preserves_history_and_allows_replacement(owner_client,imported):
    payload=request_plan(owner_client);r=owner_client.post('/api/v1/recovery/plan-cases',json=payload);assert r.status_code==201
    cid=r.json()['id']
    assert owner_client.post('/api/v1/recovery/plan-cases',json=payload).status_code==409
    assert owner_client.post(f'/api/v1/recovery/cases/{cid}/withdraw',json={'reason':'Superseded by newly reviewed material plan'}).status_code==200
    assert owner_client.post(f'/api/v1/recovery/cases/{cid}/approve').status_code==409
    assert owner_client.post('/api/v1/recovery/plan-cases',json=payload).status_code==201
    cases=owner_client.get('/api/v1/recovery/cases').json();assert len(cases)==2
    assert next(c for c in cases if c['id']==cid)['data']['withdrawal']['reason']
    assert any(a['action']=='recovery.withdraw' for a in owner_client.get('/api/v1/recovery/audit').json())
