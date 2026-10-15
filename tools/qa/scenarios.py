"""Live HTTP adversarial scenarios and read-only database reconciliation."""
import csv
import io
import json
import os
from pathlib import Path
import sqlite3
import time
import httpx


def main():
    run=Path(os.environ['ATLAS_QA_RUN']).resolve()
    if not (run/'SYNTHETIC_ONLY').exists() or not os.environ['ATLAS_QA_API'].startswith('http://127.0.0.1:'):
        raise SystemExit('Only the fresh loopback QA environment is permitted')
    f=json.loads((run/'private.json').read_text()); org=f['org_id'].replace('-','')
    rows=[]; evidence=[]
    next_request=[0.0]
    # Browser imports share the loopback IP upload budget. Start this phase
    # after the real 60-second window expires; do not reset or bypass limits.
    next_upload=[time.monotonic()+61.0]
    def pace(request):
        is_upload='/data/import/' in request.url.path
        deadline=max(next_request[0],next_upload[0] if is_upload else 0)
        time.sleep(max(0,deadline-time.monotonic()))
        next_request[0]=time.monotonic()+0.85
        if is_upload:next_upload[0]=time.monotonic()+2.1
    client=httpx.Client(event_hooks={'request':[pace]},base_url=os.environ['ATLAS_QA_API']+'/api/v1',timeout=45)
    assert client.post('/auth/demo-login',json={'login_id':f['login_id'],'password':f['password']}).status_code==200
    def sql(query,args=()):
        with sqlite3.connect(f'file:{run}/qa.sqlite?mode=ro',uri=True) as db: return db.execute(query,args).fetchall()
    def check(id,area,fn):
        start=time.monotonic()
        try:
            observed=fn(); status='PASS'; description=observed or 'All named assertions passed'
        except Exception as e:
            status='FAIL'; description=type(e).__name__+': '+str(e)
        rows.append(dict(id=id,area=area,status=status,description=description,evidence=['scenarios.json#'+id],critical=True,duration_ms=round((time.monotonic()-start)*1000,2)))
        print(id,status,flush=True)
    def commit(entity,raw,mode='create',sheet=None,name='input.csv'):
        data={'entity':entity,'mode':mode}
        if sheet: data['sheet']=sheet
        preview=client.post('/data/import/preview',data=data,files={'file':(name,raw)})
        assert preview.status_code==200,preview.text
        data['mapping']=json.dumps(preview.json()['suggested_mapping'])
        response=client.post('/data/import/commit',data=data,files={'file':(name,raw)})
        assert response.status_code==200,response.text
        evidence.append({'entity':entity,'mode':mode,'preview_validation':preview.json().get('validation'),'result':response.json()})
        return response.json()
    def excel():
        source=Path(os.environ['ATLAS_QA_KIT'])
        from openpyxl import load_workbook
        workbook=load_workbook(source,read_only=True,data_only=True)
        source_rows=list(workbook['inventory_refresh'].values); headers=list(source_rows[0])
        expected={str(r[headers.index('product_sku')]):int(r[headers.index('quantity')]) for r in source_rows[1:] if r[0] is not None}
        workbook.close()
        outcome=commit('inventory',source.read_bytes(),sheet='inventory_refresh',name='qa.xlsx')
        assert outcome['rows_imported']==len(expected),outcome
        for sku,qty in expected.items():
            actual=sql('SELECT i.quantity FROM inventory i JOIN products p ON p.id=i.product_id WHERE i.organization_id=? AND i.is_current=1 AND p.sku=?',(org,sku))
            assert actual==[(qty,)],(sku,qty,actual)
        return f'Excel sheet: {len(expected)} source rows reconcile to stored quantities'
    check('IMPORT-002','imports',excel)
    header='warehouse_name,product_sku,quantity,reorder_point,max_stock,avg_daily_demand\n'
    def inventory_boundaries():
        observations=[]
        for qty,status,reorder in [(0,'stockout',292),(99,'low_stock',193),(100,'low_stock',192),(101,'ok',0),(292,'overstock',0),(2000,'overstock',0)]:
            out=commit('inventory',(header+f'Bengaluru Distribution Center,HP-240,{qty},100,292,14\n').encode())
            assert out['rows_imported']==1,out
            item=client.get('/inventory/items',params={'q':'HP-240'}).json()['items'][0]
            assert item['quantity']==qty and item['status']==status and item['reorder_recommendation']==reorder,(qty,item)
            actual=sql('SELECT quantity FROM inventory WHERE organization_id=? AND product_id=(SELECT id FROM products WHERE organization_id=? AND sku=?) AND is_current=1',(org,org,'HP-240'))
            assert actual==[(qty,)],actual
            observations.append({'quantity':qty,'status':status,'replenishment':reorder})
        evidence.append({'boundary_assertions':observations})
        return 'Zero, below, exact threshold, above threshold, exact target and overstock classifications/quantities independently asserted'
    check('INV-002','inventory reconciliation',inventory_boundaries)
    def invalid():
        before=sql('SELECT id,quantity FROM inventory WHERE organization_id=? ORDER BY id',(org,))
        cases=[b'',b'wrong_column\nwrong\n', (header+'Bengaluru Distribution Center,HP-240,-1,100,292,14\n').encode(),(header+'Bengaluru Distribution Center,,5,100,292,14\n').encode()]
        for raw in cases:
            preview=client.post('/data/import/preview',data={'entity':'inventory'},files={'file':('invalid.csv',raw)})
            assert preview.status_code in [200,400,413,422],preview.text
            if preview.status_code==200:
                assert preview.json()['validation']['valid']==0,preview.text
                rejected=client.post('/data/import/commit',data={'entity':'inventory','mapping':json.dumps(preview.json()['suggested_mapping'])},files={'file':('invalid.csv',raw)})
                assert rejected.status_code in [200,400,422],rejected.text
                if rejected.status_code==200:assert rejected.json()['rows_imported']==0,rejected.text
            after=sql('SELECT id,quantity FROM inventory WHERE organization_id=? ORDER BY id',(org,))
            assert after==before,'Invalid preview mutated stock'
        return 'Empty file, invalid columns, negative quantity and missing SKU rejected without stock mutation'
    check('IMPORT-003','imports',invalid)
    def shipment():
        raw=b'reference,origin,destination,carrier,eta\nSHP-1050,Pune,Bengaluru,QA Freight,2026-10-15T00:00:00Z\n'
        for _ in range(2):
            out=commit('shipments',raw,mode='update');assert out['rows_imported']==1,out
            actual=sql('SELECT eta FROM shipments WHERE organization_id=? AND reference=?',(org,'SHP-1050'))
            assert len(actual)==1 and actual[0][0].startswith('2026-10-15'),actual
        return 'Shipment ETA changed to source date, replay preserved exactly one shipment'
    check('SHIP-001','imports',shipment)
    def authorization():
        viewer=httpx.Client(base_url=client.base_url,cookies={f['cookie_name']:f['sessions']['viewer']},timeout=30)
        admin=httpx.Client(base_url=client.base_url,cookies={f['cookie_name']:f['sessions']['admin']},timeout=30)
        try:
            assert viewer.get('/auth/me').json()['current_membership']['role_slug']=='viewer'
            assert admin.get('/auth/me').json()['current_membership']['role_slug']=='admin'
            assert viewer.post('/incidents',json={'title':'Forbidden incident','severity':'high'}).status_code==403
            assert admin.get('/priorities/usage/summary').status_code==200
            assert client.get('/priorities/usage/summary').status_code==403
            assert client.get('/incidents/not-a-uuid').status_code==422
            return 'Fixture sessions: viewer forbidden server-side, admin usage allowed, operations admin access forbidden, malformed UUID controlled'
        finally: viewer.close();admin.close()
    check('AUTHZ-001','authorization',authorization)
    def invalid_session():
        with httpx.Client(base_url=client.base_url,cookies={f['cookie_name']:'invalid-qa-session'},timeout=30) as bad:
            assert bad.get('/auth/me').status_code==401
            assert bad.get('/inventory/items').status_code==401
        return 'Invalid opaque session denied for identity and inventory API'
    check('AUTH-002','authentication',invalid_session)
    # Controlled oversized file is rejected before parsing and must not write records.
    def large():
        before=sql('SELECT COUNT(*) FROM inventory WHERE organization_id=?',(org,))
        response=client.post('/data/import/preview',data={'entity':'inventory'},files={'file':('large.csv',b'x'*(15*1024*1024+1))})
        assert response.status_code==413,response.status_code
        assert sql('SELECT COUNT(*) FROM inventory WHERE organization_id=?',(org,))==before
        return '15 MiB + 1 byte import rejected with HTTP 413; inventory count unchanged. This is a size-limit check, not throughput evidence.'
    check('IMPORT-004','imports',large)
    def duplicate_rows():
        raw=header+'Bengaluru Distribution Center,HP-240,123,100,292,14\n'*2
        outcome=commit('inventory',raw.encode())
        assert outcome['rows_imported']==2,outcome
        actual=sql('SELECT i.quantity FROM inventory i JOIN products p ON p.id=i.product_id WHERE i.organization_id=? AND i.is_current=1 AND p.sku=?',(org,'HP-240'))
        assert actual==[(123,)],actual
        return 'Two identical snapshot rows retain one position at 123 units; rows are not summed'
    check('IMPORT-006','imports',duplicate_rows)
    def batch_import():
        product_csv='sku,name,unit_cost,unit_price\n'+''.join(f'QA-BATCH-{i},QA batch part {i},1,2\n' for i in range(1000))
        outcome=commit('products',product_csv.encode());assert outcome['rows_imported']==1000,outcome
        inventory_csv=header+''.join(f'Bengaluru Distribution Center,QA-BATCH-{i},{i%17},10,30,1\n' for i in range(1000))
        expected=sum(int(r['quantity']) for r in csv.DictReader(io.StringIO(inventory_csv)))
        before=sql('SELECT SUM(quantity) FROM inventory WHERE organization_id=? AND is_current=1',(org,))[0][0]
        for attempt in range(2):
            outcome=commit('inventory',inventory_csv.encode());assert outcome['rows_imported']==1000,outcome
            actual=sql("SELECT COUNT(*),SUM(i.quantity) FROM inventory i JOIN products p ON p.id=i.product_id WHERE i.organization_id=? AND i.is_current=1 AND p.sku LIKE 'QA-BATCH-%'",(org,))[0]
            assert actual==(1000,expected),(actual,expected)
            total=sql('SELECT SUM(quantity) FROM inventory WHERE organization_id=? AND is_current=1',(org,))[0][0]
            assert total==before+expected,(total,before,expected)
            assert sql('SELECT SUM(current_inventory) FROM warehouses WHERE organization_id=?',(org,))[0][0]==total
        return f'1,000 source inventory rows imported twice; exactly 1,000 positions and {expected} units; tenant and warehouse totals reconcile'
    check('IMPORT-005','imports',batch_import)
    (run/'scenarios.json').write_text(json.dumps({'tests':rows,'observations':evidence},indent=2))
    client.close()

if __name__=='__main__':main()
