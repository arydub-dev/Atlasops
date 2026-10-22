"""Regression cases for QA AI-001 and AI-003 through customer API paths."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Inventory, Product, Shipment, Supplier, Warehouse
from app.models.enums import ShipmentStatus
from app.seed.yc_demo import populate
from app.tenancy.rls import set_session_org


@pytest.fixture
def inventory_case(db, org_a, owner_user):
    org = org_a[0]
    populate(db, org, owner_user.id)
    product = db.scalar(select(Product).where(Product.organization_id == org.id, Product.sku == 'HP-240'))
    product.sku = 'REQUESTED-999'
    item = db.scalar(select(Inventory).where(Inventory.organization_id == org.id, Inventory.product_id == product.id))
    item.quantity = 80
    db.commit()
    return org, product, item


@pytest.mark.parametrize('endpoint', ['chat', 'orchestrate'])
def test_explicit_sku_outside_summary_limit(owner_client, inventory_case, monkeypatch, endpoint):
    from app.services.ai_providers import LocalEngineProvider
    seen = {}
    original = LocalEngineProvider.answer
    def observe(self, prompt, context):
        seen.update(context)
        return original(self, prompt, context)
    monkeypatch.setattr(LocalEngineProvider, 'answer', observe)
    response = owner_client.post('/api/v1/ai/'+endpoint, json={'prompt':'Why is REQUESTED-999 at risk? State current quantity and replenishment units.'})
    assert response.status_code == 200, response.text
    text = response.json()['response']
    assert 'REQUESTED-999' in text, text
    assert '80' in text and '212' in text, text
    assert '292' in text, 'The calculation must identify the configured target'


def test_broad_inventory_summary_remains_bounded(owner_client, inventory_case, monkeypatch):
    from app.services.ai_providers import LocalEngineProvider
    seen = {}
    original = LocalEngineProvider.answer
    def observe(self, prompt, context):
        seen.update(context)
        return original(self, prompt, context)
    monkeypatch.setattr(LocalEngineProvider, 'answer', observe)
    response = owner_client.post('/api/v1/ai/orchestrate', json={'prompt':'Summarize low stock inventory'})
    assert response.status_code == 200
    assert len(seen['inventory_priorities']) == 20
    assert 'REQUESTED-999' not in {r['sku'] for r in seen['inventory_priorities']}
    assert 'replenishment' in response.json()['response']


@pytest.mark.parametrize('endpoint', ['chat', 'orchestrate'])
def test_delivery_without_evidence_abstains(owner_client, endpoint):
    response = owner_client.post('/api/v1/ai/'+endpoint, json={'prompt':'Which supplier delivered exactly 10,000 units yesterday?'})
    assert response.status_code == 200
    text = response.json()['response'].lower()
    assert 'cannot verify' in text or 'cannot be verified' in text, text
    assert 'lowest performers' not in text


def add_delivery(db, org, *, name='Evidence Supplier', units=10000, delivered_at=None):
    set_session_org(db, org.id)
    now = datetime.now(timezone.utc)
    supplier = Supplier(organization_id=org.id, name=name, country='US', region='US', category='Synthetic')
    db.add(supplier); db.flush()
    shipment = Shipment(organization_id=org.id, reference='EVIDENCE-DELIVERY', origin='A', destination='B',
        carrier='Synthetic carrier', current_location='B', supplier_id=supplier.id,
        units=units, value_usd=1, status=ShipmentStatus.DELIVERED,
        shipped_at=now-timedelta(days=3), eta=now-timedelta(days=1),
        delivered_at=delivered_at or now-timedelta(days=1), delay_days=0)
    db.add(shipment); db.commit()
    return shipment


@pytest.mark.parametrize('endpoint', ['chat', 'orchestrate'])
def test_delivery_with_evidence_identifies_record(owner_client, db, org_a, endpoint):
    shipment = add_delivery(db, org_a[0])
    response = owner_client.post('/api/v1/ai/'+endpoint, json={'prompt':'Which supplier delivered exactly 10,000 units yesterday?'})
    assert response.status_code == 200
    text = response.json()['response']
    assert 'Evidence Supplier' in text and shipment.reference in text, text
    assert '10,000' in text or '10000' in text
    assert shipment.delivered_at.date().isoformat() in text


def test_explicit_healthy_sku_uses_zero_replenishment(owner_client, db, inventory_case):
    inventory_case[2].quantity = 150
    db.commit()
    response = owner_client.post('/api/v1/ai/orchestrate', json={'prompt':'Check requested-999 stock.'})
    assert response.status_code == 200
    text = response.json()['response']
    assert 'REQUESTED-999' in text and '150 units' in text
    assert 'suggested replenishment 0 units' in text
    assert 'above the reorder point' in text
    assert 'below reorder thresholds' not in text


def test_explicit_sku_without_current_position_does_not_substitute_other_stock(owner_client, db, inventory_case):
    inventory_case[2].is_current = False
    db.commit()
    response = owner_client.post('/api/v1/ai/chat', json={'prompt':'Check REQUESTED-999 stock.'})
    assert response.status_code == 200
    assert 'cannot verify current inventory' in response.json()['response']


def test_sku_matching_is_whole_identifier(owner_client, inventory_case):
    response = owner_client.post('/api/v1/ai/chat', json={'prompt':'Check REQUESTED-9999 stock.'})
    assert response.status_code == 200
    assert 'REQUESTED-999)' not in response.json()['response']


@pytest.mark.parametrize('endpoint', ['chat', 'orchestrate'])
def test_specific_facts_do_not_depend_on_external_provider(owner_client, db, org_a, inventory_case, monkeypatch, endpoint):
    from app.core.config import settings
    from app.services import ai_providers
    monkeypatch.setattr(settings, 'OPENAI_API_KEY', 'synthetic-provider-key')
    def forbidden():
        raise AssertionError('Factual evidence must not be replaced by a model completion')
    monkeypatch.setattr(ai_providers, 'get_ai_provider', forbidden)
    for prompt, expected in [('Check REQUESTED-999 stock.', '212 units'),
                             ('Which supplier delivered exactly 10,000 units yesterday?', 'cannot verify')]:
        response = owner_client.post('/api/v1/ai/'+endpoint, json={'prompt':prompt})
        assert response.status_code == 200, response.text
        assert expected in response.json()['response']
        assert response.json()['model'] == 'local-engine'
    add_delivery(db, org_a[0])
    response = owner_client.post('/api/v1/ai/'+endpoint, json={'prompt':'Which supplier delivered exactly 10,000 units yesterday?'})
    assert response.status_code == 200
    assert 'EVIDENCE-DELIVERY' in response.json()['response']


@pytest.mark.parametrize('endpoint', ['chat', 'orchestrate'])
def test_delivery_matching_only_other_tenant_still_abstains(owner_client, db, org_a, org_b, endpoint):
    add_delivery(db, org_b[0], name='OTHER-TENANT-PRIVATE-SUPPLIER')
    response = owner_client.post('/api/v1/ai/'+endpoint, json={'prompt':'Which supplier delivered exactly 10,000 units yesterday?'})
    assert response.status_code == 200
    assert 'cannot verify' in response.json()['response']
    assert 'OTHER-TENANT-PRIVATE-SUPPLIER' not in response.text
    from app.models import AIReport
    set_session_org(db, org_a[0].id)
    for report in db.scalars(select(AIReport).where(AIReport.organization_id == org_a[0].id)):
        assert 'OTHER-TENANT-PRIVATE-SUPPLIER' not in str(report.context_snapshot)


def test_explicit_sku_never_retrieves_same_sku_from_other_tenant(owner_client, db, inventory_case, org_b):
    other = org_b[0]
    set_session_org(db, other.id)
    product = Product(organization_id=other.id, sku='REQUESTED-999', name='OTHER-PRIVATE-PRODUCT', category='Synthetic', unit_cost=1, unit_price=2)
    warehouse = Warehouse(organization_id=other.id, name='OTHER-PRIVATE-WAREHOUSE', location='B', region='B', capacity=100, latitude=0, longitude=0)
    db.add_all([product,warehouse]); db.flush()
    db.add(Inventory(organization_id=other.id, product_id=product.id, warehouse_id=warehouse.id,
        quantity=987654321, reorder_point=100, max_stock=200, avg_daily_demand=1, is_current=True))
    db.commit()
    response = owner_client.post('/api/v1/ai/chat', json={'prompt':'Check REQUESTED-999 stock.'})
    assert response.status_code == 200
    assert '80 units' in response.json()['response'] and '212 units' in response.json()['response']
    assert 'OTHER-PRIVATE' not in response.text and '987654321' not in response.text
    from app.models import AIReport
    set_session_org(db, inventory_case[0].id)
    for report in db.scalars(select(AIReport).where(AIReport.organization_id == inventory_case[0].id)):
        assert 'OTHER-PRIVATE' not in str(report.context_snapshot)
        assert '987654321' not in str(report.context_snapshot)


@pytest.mark.parametrize('permission', ['shipments.read', 'suppliers.read'])
def test_delivery_requires_both_read_permissions(owner_client, db, org_a, permission):
    add_delivery(db, org_a[0])
    org_a[1].role_slug = 'custom:qa'
    org_a[1].custom_permissions = ['ai.chat', permission]
    db.commit()
    response = owner_client.post('/api/v1/ai/orchestrate', json={'prompt':'Which supplier delivered exactly 10,000 units yesterday?'})
    assert response.status_code == 200
    assert 'cannot verify' in response.json()['response']
    assert 'Evidence Supplier' not in response.text and 'EVIDENCE-DELIVERY' not in response.text


@pytest.mark.parametrize('permission', ['inventory.read', 'warehouses.read'])
def test_explicit_sku_does_not_bypass_inventory_permissions(owner_client, db, org_a, inventory_case, permission):
    org_a[1].role_slug = 'custom:qa'
    org_a[1].custom_permissions = ['ai.chat', permission]
    db.commit()
    response = owner_client.post('/api/v1/ai/orchestrate', json={'prompt':'Check REQUESTED-999 stock.'})
    assert response.status_code == 200
    assert '212' not in response.json()['response'] and '80 units' not in response.json()['response']


@pytest.mark.parametrize('mismatch', ['quantity', 'date', 'status', 'timestamp'])
def test_eta_and_unrelated_deliveries_are_not_evidence(owner_client, db, org_a, mismatch):
    shipment = add_delivery(db, org_a[0])
    if mismatch == 'quantity': shipment.units = 9999
    if mismatch == 'date': shipment.delivered_at = datetime.now(timezone.utc)-timedelta(days=2)
    if mismatch == 'status': shipment.status = ShipmentStatus.IN_TRANSIT
    if mismatch == 'timestamp': shipment.delivered_at = None
    db.commit()
    response = owner_client.post('/api/v1/ai/orchestrate', json={'prompt':'Which supplier delivered exactly 10,000 units yesterday?'})
    assert response.status_code == 200
    assert 'cannot verify' in response.json()['response']
    assert 'Evidence Supplier' not in response.text


def test_delivery_utc_day_boundaries(owner_client, db, org_a):
    start = datetime(2026, 10, 8, tzinfo=timezone.utc)
    shipment = add_delivery(db, org_a[0], delivered_at=start)
    prompt = 'Which supplier delivered exactly 10,000 units on 2026-10-08 UTC?'
    assert 'EVIDENCE-DELIVERY' in owner_client.post('/api/v1/ai/chat', json={'prompt':prompt}).json()['response']
    shipment.delivered_at = start+timedelta(days=1)
    db.commit()
    assert 'cannot verify' in owner_client.post('/api/v1/ai/chat', json={'prompt':prompt}).json()['response']


@pytest.mark.parametrize('prompt', [
    'Which supplier delivered at least 10,000 units yesterday?',
    'Which supplier delivered exactly 10,000 units yesterday in Tokyo?',
    'Which supplier delivered exactly 10,000 units on 2026-02-30?',
    'Did Acme deliver 10,000 units yesterday?',
    'Which supplier delivered exactly 10.5 units yesterday?',
])
def test_unsupported_delivery_constraints_request_clarification(owner_client, db, org_a, prompt):
    add_delivery(db, org_a[0])
    response = owner_client.post('/api/v1/ai/orchestrate', json={'prompt':prompt})
    assert response.status_code == 200
    assert 'cannot verify' in response.json()['response']
    assert 'Evidence Supplier' not in response.text


def test_supplier_summary_still_answers_summary_question(owner_client, db, org_a):
    add_delivery(db, org_a[0])
    response = owner_client.post('/api/v1/ai/orchestrate', json={'prompt':'Summarize supplier delivery performance'})
    assert response.status_code == 200
    assert 'Supplier performance' in response.json()['response']
    assert 'Evidence Supplier' in response.json()['response']
