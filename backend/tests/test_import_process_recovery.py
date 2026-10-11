"""Real process death against disposable PostgreSQL, never a supplied database."""
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from sqlalchemy import select

from app.core.database import engine
from app.models import ImportJob, Inventory, Warehouse
from app.tenancy.rls import set_session_org
from test_pilot_import_journey import upload

pytestmark = pytest.mark.skipif(
    os.environ.get('SUPPLY_CI_POSTGRES') != '1' or not os.environ.get('ATLAS_QA_RUN'),
    reason='Process-death verification requires the disposable QA PostgreSQL runner')

CHILD = r'''
import os, sys, time
from pathlib import Path
from uuid import UUID
from app.core.database import SessionLocal
from app.services import ingestion
from app.tenancy.rls import set_session_org
org, stage, marker = sys.argv[1:]
def pause():
    Path(marker).write_text('reached')
    while True: time.sleep(.05)
db = SessionLocal()
set_session_org(db, UUID(org))
original = ingestion._transform_row
calls = 0
def transform(*args, **kwargs):
    global calls
    calls += 1
    if stage == 'between_rows' and calls == 2: pause()
    return original(*args, **kwargs)
ingestion._transform_row = transform
rows = [{'warehouse_name':'Recovery DC','product_sku':sku,'quantity':qty} for sku,qty in [('REC-A','17'),('REC-B','23')]]
ingestion.commit_import(db, organization_id=UUID(org), entity='inventory', rows=rows,
    mapping={k:k for k in rows[0]}, source_name='process-death.csv', source_type='csv')
if stage == 'before_commit': pause()
db.commit()
if stage == 'after_commit': pause()
'''


@pytest.mark.parametrize('stage', ['between_rows', 'before_commit', 'after_commit'])
def test_import_process_death_and_retry(owner_client, db, org_a, tmp_path, stage):
    # Guard against accidentally using a staging/customer URL with destructive tests.
    run = Path(os.environ['ATLAS_QA_RUN'])
    assert (run/'SYNTHETIC_ONLY').is_file()
    assert engine.url.host == '127.0.0.1' and engine.url.username == 'qa_app'
    upload(owner_client, 'warehouses', 'name,location,region,capacity\nRecovery DC,Chicago,US,1000\n')
    for sku in ['REC-A', 'REC-B']:
        upload(owner_client, 'products', f'sku,name,unit_cost,unit_price\n{sku},Synthetic part,1,2\n')
    org_id = org_a[0].id
    db.commit()
    marker = tmp_path/'checkpoint'
    with (tmp_path/'child.log').open('w') as log:
        child = subprocess.Popen([sys.executable,'-c',CHILD,str(org_id),stage,str(marker)],
                                 env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic()+20
            while not marker.exists() and child.poll() is None and time.monotonic()<deadline:
                time.sleep(.05)
            assert marker.exists(), 'Import child did not reach the controlled checkpoint'
            child.kill()  # SIGKILL: no Python cleanup, rollback handler or mocked success.
            child.wait(timeout=10)
            assert child.returncode != 0
        finally:
            if child.poll() is None: child.kill(); child.wait(timeout=10)
    db.expire_all(); set_session_org(db, org_id)
    rows = db.scalars(select(Inventory).where(Inventory.organization_id==org_id)).all()
    jobs = db.scalars(select(ImportJob).where(ImportJob.organization_id==org_id,
                                            ImportJob.source_name=='process-death.csv')).all()
    if stage == 'after_commit':
        assert sorted(r.quantity for r in rows)==[17,23]
        assert len(jobs)==1 and jobs[0].status.value=='success'
        assert jobs[0].rows_imported==2
    else:
        assert rows==[] and jobs==[]  # Entire outer transaction disappeared.
    db.commit()
    raw=b'warehouse_name,product_sku,quantity\nRecovery DC,REC-A,17\nRecovery DC,REC-B,23\n'
    import json
    for _ in range(2):
        response=owner_client.post('/api/v1/data/import/commit', data={'entity':'inventory',
            'mapping':json.dumps({k:k for k in ['warehouse_name','product_sku','quantity']})},
            files={'file':('recovery.csv',raw,'text/csv')})
        assert response.status_code==200
        assert response.json()['rows_imported']==2 and response.json()['rows_rejected']==0
    db.expire_all(); set_session_org(db,org_id)
    rows=db.scalars(select(Inventory).where(Inventory.organization_id==org_id)).all()
    assert len(rows)==2 and sorted(r.quantity for r in rows)==[17,23]
    assert db.scalar(select(Warehouse).where(Warehouse.organization_id==org_id)).current_inventory==40
    listed=owner_client.get('/api/v1/inventory/items').json()
    assert listed['total']==2 and sum(r['quantity'] for r in listed['items'])==40
