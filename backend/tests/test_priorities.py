from uuid import uuid4
from tests.test_pilot_import_journey import upload


def seed(client):
    upload(client,'warehouses','name,location,region,capacity\nPilot DC,Chicago,US,1000\n')
    upload(client,'products','sku,name,unit_cost,unit_price\nP-1,Pump,10,20\n')
    upload(client,'inventory','warehouse_name,product_sku,quantity,reorder_point,max_stock,avg_daily_demand\nPilot DC,P-1,2,10,30,1\n')


def test_import_detect_explain_act_resolve_and_refresh(owner_client):
    seed(owner_client)
    response=owner_client.get('/api/v1/priorities')
    assert response.status_code==200,response.text
    feed=response.json()
    assert feed['counts']['critical']==1 and feed['counts']['low_stock']==1
    item=feed['items'][0]
    path='/api/v1/priorities/'+item['id'].replace(':','/')
    detail=owner_client.get(path).json()
    assert detail['facts']['replenishment_units']==28
    assert detail['facts']['days_of_supply']==2
    assert detail['incoming_shipments']==[]
    upload(owner_client,'shipments','reference,origin,destination,carrier,status,product_sku,warehouse_name\nINBOUND-1,Port,Pilot DC,Carrier,delayed,P-1,Pilot DC\n')
    linked=owner_client.get(path).json()['incoming_shipments']
    assert len(linked)==1 and linked[0]['reference']=='INBOUND-1'
    assert owner_client.post(path+'/view').status_code==200
    usage=owner_client.get('/api/v1/priorities/usage/summary')
    assert usage.status_code==200,usage.text
    assert usage.json()['recommendation_view_events']==1
    created=owner_client.post(path+'/incident',json={'notes':'Confirm delivery before ordering'})
    assert created.status_code==200,created.text
    incident=created.json()['id']
    assert owner_client.post(path+'/incident',json={}).json()=={'id':incident,'created':False}
    assert owner_client.get(path).json()['incidents'][0]['id']==incident
    assert owner_client.patch('/api/v1/incidents/'+incident,json={'status':'investigating','assign_to_me':True}).status_code==200
    assert owner_client.post('/api/v1/incidents/'+incident+'/resolve',json={'resolution':'Stock received and reconciled'}).status_code==200
    # A completed task must not pretend to change physical stock.
    assert owner_client.get('/api/v1/priorities').json()['counts']['low_stock']==1
    upload(owner_client,'inventory','warehouse_name,product_sku,quantity,reorder_point,max_stock,avg_daily_demand\nPilot DC,P-1,20,10,30,1\n')
    refreshed=owner_client.get('/api/v1/priorities').json()
    assert refreshed['counts']['low_stock']==0 and refreshed['counts']['open_incidents']==0
    assert owner_client.get(path).status_code==404


def test_unknown_or_other_tenant_priority_not_exposed(owner_client,org_b,db):
    from app.models import Shipment
    from app.models.enums import ShipmentStatus
    from app.tenancy.rls import set_session_org
    from datetime import datetime,timezone
    org=org_b[0]; set_session_org(db,org.id)
    s=Shipment(organization_id=org.id,reference='PRIVATE-SHIPMENT',origin='A',destination='B',carrier='C',current_location='A',status=ShipmentStatus.DELAYED,units=1,value_usd=1,shipped_at=datetime.now(timezone.utc),eta=datetime.now(timezone.utc),delay_days=3)
    db.add(s);db.commit()
    assert 'PRIVATE-SHIPMENT' not in owner_client.get('/api/v1/priorities').text
    assert owner_client.get(f'/api/v1/priorities/shipment/{s.id}').status_code==404
    assert owner_client.post(f'/api/v1/priorities/shipment/{s.id}/incident',json={}).status_code==404


def test_viewer_cannot_turn_priority_into_action(viewer_client):
    assert viewer_client.post(f'/api/v1/priorities/inventory/{uuid4()}/incident',json={}).status_code==403
