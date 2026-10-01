"""Synthetic in-process API baseline; deliberately refuses remote/production databases."""
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

url = urlsplit(os.environ.get('DATABASE_URL', ''))
if url.hostname not in {'127.0.0.1', 'localhost'} or url.path != '/atlasops_pilot_benchmark':
    raise SystemExit('Only local /atlasops_pilot_benchmark is allowed')
os.environ.update(ENVIRONMENT='test', ALLOW_CREATE_ALL_ON_STARTUP='false',
                  SEED_ON_STARTUP='false', WORKOS_API_KEY='', WORKOS_CLIENT_ID='',
                  STRIPE_SECRET_KEY='', OPENAI_API_KEY='', FEATURE_BILLING_ENFORCE='false',
                  CONNECTOR_SYNC_INLINE='true', REDIS_URL='redis://127.0.0.1:1/0')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.config import settings
from app.seed.synthetic import seed_sandbox
from app.identity.sessions import create_session
from app.models import Organization, User
from app.main import app

with SessionLocal() as db:
    email = f'baseline-{uuid4().hex}@example.invalid'
    seed_sandbox(db, owner_email=email, org_name='Synthetic pilot baseline',
                 n_suppliers=25, n_warehouses=10, n_products=100, n_shipments=1000)
    user = db.scalar(select(User).where(User.email == email))
    org = db.scalar(select(Organization).where(Organization.owner_user_id == user.id))
    _, token = create_session(db, user=user, organization_id=org.id)
    db.commit()
    org_id = str(org.id)

results = {'scope': 'Local in-process sequential API baseline; excludes network/TLS/browser and concurrent load',
           'data': {'shipments': 1000, 'suppliers': 25, 'warehouses': 10, 'products': 100}, 'cases': []}
with TestClient(app) as client:
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    client.headers['X-Organization-Id'] = org_id
    for path in ['/api/v1/shipments?limit=25', '/api/v1/mission-control']:
        samples = []
        for _ in range(20):
            start = time.perf_counter()
            response = client.get(path)
            assert response.status_code == 200, f'{path}: HTTP {response.status_code}'
            samples.append((time.perf_counter()-start)*1000)
        samples.sort()
        results['cases'].append({'path': path, 'requests': 20, 'p50_ms': round(samples[9],2), 'p95_ms': round(samples[18],2)})
    rows = 'name,country,region,category\n'+''.join(f'Imported supplier {i},USA,West,Components\n' for i in range(1000))
    mapping = {k:k for k in ['name','country','region','category']}
    start = time.perf_counter()
    response = client.post('/api/v1/data/import/commit', data={'entity':'suppliers','mapping':json.dumps(mapping)},
                           files={'file':('suppliers.csv',rows.encode(),'text/csv')})
    assert response.status_code == 200, response.status_code
    assert response.json()['rows_imported'] == 1000
    results['import'] = {'rows':1000, 'duration_ms':round((time.perf_counter()-start)*1000,2)}
Path('/private/tmp/atlasops-pilot-baseline.json').write_text(json.dumps(results,indent=2))
print('PASS: synthetic baseline written without sessions or customer data')
