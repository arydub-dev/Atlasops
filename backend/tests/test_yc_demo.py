from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import select, func

from app.seed.yc_demo import provision, reset_workspace
from app.core.config import settings
from app.identity.orgs import build_tenant_context
from app.models import Organization, Membership, Inventory, Product, Warehouse, Connection
from app.services.inventory_logic import reorder_recommendation
from app.services.ai_advisor import build_context, _inventory_answer
from app.tenancy.context import set_tenant, reset_tenant
from app.tenancy.rls import set_session_org


def setup_demo(db, owner_user):
    owner_user.workos_user_id = 'user_test_yc_verified'
    owner_user.email_verified_at = datetime.now(timezone.utc)
    db.commit()
    result = provision(db,owner_user.email)
    org = db.get(Organization,UUID(result['organization_id']))
    member = db.scalar(select(Membership).where(Membership.organization_id==org.id))
    return org, member


def test_requires_existing_verified_login(db, owner_user):
    with pytest.raises(ValueError,match='WorkOS'):
        provision(db,owner_user.email)


def test_demo_reconciles_and_ai_uses_actual_positions(db, owner_user):
    org, member = setup_demo(db,owner_user)
    set_session_org(db,org.id)
    assert db.scalar(select(func.count()).select_from(Product).where(Product.organization_id==org.id)) == 240
    total = db.scalar(select(func.sum(Inventory.quantity)).where(Inventory.organization_id==org.id))
    warehouse_total = db.scalar(select(func.sum(Warehouse.current_inventory)).where(Warehouse.organization_id==org.id))
    assert total == warehouse_total
    pump = db.scalar(select(Inventory).join(Product).where(Product.sku=='HP-240',Inventory.organization_id==org.id))
    assert pump.quantity == 42 and reorder_recommendation(pump)==250
    assert all(not c.credentials_encrypted and c.status.value=='not_configured' for c in db.scalars(select(Connection).where(Connection.organization_id==org.id)))
    token = set_tenant(build_tenant_context(org=org,user=owner_user,membership=member))
    try:
        context = build_context(db)
        answer = _inventory_answer(context)
        assert 'HP-240' in answer
        assert '250 units' in answer
        assert 'SHP-1050' in answer
    finally:
        reset_tenant(token)
    assert provision(db,owner_user.email)['existing'] is True


def test_reset_requires_exact_allowlist_and_preserves_other_tenant(db,owner_user,org_a,monkeypatch):
    org, member = setup_demo(db,owner_user)
    with pytest.raises(PermissionError):
        reset_workspace(db,org.id,owner_user.id)
    monkeypatch.setattr(settings,'DEMO_WORKSPACE_ID',str(org.id))
    other = org_a[0]
    with pytest.raises(PermissionError):
        reset_workspace(db,other.id,owner_user.id)
    assert reset_workspace(db,org.id,owner_user.id)['reset']
    set_session_org(db,org.id)
    assert db.scalar(select(func.count()).select_from(Product))==240
    assert db.get(Organization,other.id) is not None


def test_demo_workbook_parses_through_real_importer():
    from pathlib import Path
    from app.services.ingestion import parse_upload, validate_rows
    path = Path(__file__).parents[2] / 'docs/yc-demo-imports/atlas-manufacturing-import-kit.xlsx'
    for sheet, entity in [('suppliers','suppliers'),('warehouses','warehouses'),('products','products'),
                          ('inventory','inventory'),('inventory_refresh','inventory'),
                          ('shipments','shipments'),('shipment_update','shipments')]:
        parsed = parse_upload(path.name,path.read_bytes(),sheet)
        result = validate_rows(entity,parsed['rows'],{column:column for column in parsed['columns']})
        assert result['valid'] == len(parsed['rows']) > 0, result
        assert result['rejected'] == 0


def test_demo_viewer_cannot_reset(db, owner_user, monkeypatch):
    org, member = setup_demo(db, owner_user)
    monkeypatch.setattr(settings,'DEMO_WORKSPACE_ID',str(org.id))
    member.role_slug = 'viewer'
    db.commit()
    with pytest.raises(PermissionError,match='administrator'):
        reset_workspace(db,org.id,owner_user.id)


def test_demo_ai_does_not_include_other_company(db, owner_user, org_a):
    other = org_a[0]
    set_session_org(db,other.id)
    product = Product(organization_id=other.id,sku='PRIVATE-COMPANY-SKU',name='Confidential competitor part',category='Parts',unit_cost=1,unit_price=2)
    warehouse = Warehouse(organization_id=other.id,name='Private competitor warehouse',location='Other city',region='Other region',latitude=0,longitude=0,capacity=100,current_inventory=0)
    db.add_all([product,warehouse])
    db.flush()
    db.add(Inventory(organization_id=other.id,product_id=product.id,warehouse_id=warehouse.id,quantity=0,reorder_point=100,safety_stock=10,max_stock=200,avg_daily_demand=5,is_current=True))
    db.commit()
    org, member = setup_demo(db,owner_user)
    token = set_tenant(build_tenant_context(org=org,user=owner_user,membership=member))
    try:
        set_session_org(db,org.id)
        context = build_context(db)
        assert 'PRIVATE-COMPANY-SKU' not in str(context)
        assert 'Confidential competitor' not in str(context)
    finally:
        reset_tenant(token)
