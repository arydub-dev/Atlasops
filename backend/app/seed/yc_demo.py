"""Operator-provisioned fictional workspace. Uses ordinary auth and domain models."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select

from app.core.config import settings
from app.identity.orgs import create_organization, build_tenant_context
from app.models import (User, Organization, Membership, OrgSetting, Supplier, Warehouse,
    Product, Inventory, Shipment, SalesOrder, Incident, Connection)
from app.models.enums import (ShipmentStatus, OrderStatus, IncidentStatus, IncidentSeverity,
    ConnectorType, ConnectorStatus, MembershipStatus)
from app.tenancy.context import set_tenant, reset_tenant
from app.tenancy.rls import set_session_org

MARKER = "atlas-manufacturing-v1"
NAME = "Atlas Manufacturing Co. — Synthetic Demo"


def provision(db, owner_email):
    owner = db.scalar(select(User).where(User.email == owner_email.strip().lower(), User.is_active.is_(True)))
    if not owner or not owner.workos_user_id or not owner.email_verified_at:
        raise ValueError("Demo owner must first sign in through WorkOS with a verified email")
    existing = db.scalars(select(Organization).where(Organization.owner_user_id == owner.id)).all()
    for org in existing:
        if (org.settings or {}).get("demo_dataset") == MARKER:
            return {"organization_id": str(org.id), "existing": True}
    org, member = create_organization(db, name=NAME, owner=owner)
    org.settings = {**org.settings, "demo_dataset": MARKER}
    db.add(OrgSetting(organization_id=org.id, key="operating_mode", value="demo"))
    populate(db, org, owner.id)
    db.commit()
    refresh_derived(db, org, owner, member)
    return {"organization_id": str(org.id), "name": org.name, "existing": False}


def populate(db, org, owner_id):
    set_session_org(db, org.id)
    now = datetime.now(timezone.utc)
    suppliers = []
    for name in ["Apex Industrial Components", "Meridian Motion Systems", "Nova Mechanical Supply", "Vertex Controls"]:
        supplier = Supplier(organization_id=org.id, name=name, country="India", region="South Asia",
            category="Industrial components", supplier_score=75, delivery_reliability=75,
            average_delay_days=0.5, order_fulfillment_rate=100, defect_rate=0)
        db.add(supplier); suppliers.append(supplier)
    warehouses = []
    for name, location, lat, lon in [
        ("Bengaluru Distribution Center", "Bengaluru",12.97,77.59),
        ("Mumbai Regional Warehouse","Mumbai",19.08,72.88),
        ("Chennai Assembly Hub","Chennai",13.08,80.27),
        ("Delhi Service Depot","Delhi",28.61,77.21)]:
        warehouse = Warehouse(organization_id=org.id,name=name,location=location,region="India",latitude=lat,longitude=lon,capacity=30000,current_inventory=0)
        db.add(warehouse); warehouses.append(warehouse)
    db.flush()
    products = []
    families = [("HP","Hydraulic Pump"),("IV","Industrial Valve"),("SM","Servo Motor"),("CM","Control Module"),("BA","Bearing Assembly")]
    for i in range(240):
        code, title = families[i % len(families)]
        sku = "HP-240" if i == 0 else f"{code}-{820+i}"
        product = Product(organization_id=org.id,sku=sku,name=f"{title} {sku}",category=title,
            unit_cost=500 if i == 0 else 20 + (i % 20)*15,unit_price=750 if i == 0 else 35+(i % 20)*22,
            lead_time_days=14,supplier_id=suppliers[i % 4].id)
        db.add(product); products.append(product)
    db.flush()
    for i, product in enumerate(products):
        warehouse = warehouses[i % 4]
        quantity = 42 if i == 0 else 900 if i == 1 else 0 if i % 37 == 0 else 25 if i % 17 == 0 else 150+i%100
        maximum = 292 if i == 0 else 300
        db.add(Inventory(organization_id=org.id,warehouse_id=warehouse.id,product_id=product.id,
            quantity=quantity,reorder_point=100,safety_stock=30,max_stock=maximum,
            avg_daily_demand=14 if i == 0 else 1 if i == 1 else 5,is_current=True,snapshot_date=now))
        warehouse.current_inventory += quantity
    shipments = []
    for supplier_index, supplier in enumerate(suppliers):
        for n in range(10):
            delivered = n < 8
            late = n in {2,6,8}
            days = 2 if late else 0
            product = products[supplier_index + (n * 4 if delivered else 0)]
            shipment = Shipment(organization_id=org.id,reference=f"SHP-{1042+supplier_index*10+n}",
                origin="Pune components hub",destination=warehouses[supplier_index].name,carrier="Fictional Meridian Freight",
                current_location="Pune transit hub" if not delivered else warehouses[supplier_index].location,
                status=ShipmentStatus.DELIVERED if delivered else ShipmentStatus.DELAYED if late else ShipmentStatus.IN_TRANSIT,
                supplier_id=supplier.id,product_id=product.id,warehouse_id=warehouses[supplier_index].id,
                units=250,value_usd=250*product.unit_cost,
                shipped_at=now-timedelta(days=20-n),eta=now+timedelta(days=1 if not delivered else -10+n),
                delivered_at=now+timedelta(days=-10+n+days) if delivered else None,
                delay_days=days,delay_risk_score=80 if not delivered and late else 5)
            db.add(shipment); shipments.append(shipment)
    db.flush()
    for i in range(12):
        product = products[i]
        db.add(SalesOrder(organization_id=org.id,reference=f"SO-DEMO-{2000+i}",
            status=[OrderStatus.OPEN,OrderStatus.CONFIRMED,OrderStatus.DELIVERED][i%3],
            customer_name=["Fictional Northstar Assembly", "Fictional Summit Equipment"][i%2],
            currency="USD",total_amount=20*product.unit_price,ordered_at=now-timedelta(days=5),
            promised_at=now+timedelta(days=4),warehouse_id=warehouses[i%4].id,
            line_items=[{"product_id":str(product.id),"sku":product.sku,"quantity":20,"unit_price":product.unit_price}],
            meta={"synthetic":True}))
    for i, title in enumerate(["Critical hydraulic pump shortage", "Review excess valve inventory", "Bearing replenishment reviewed"]):
        db.add(Incident(organization_id=org.id,title=title,severity=IncidentSeverity.CRITICAL if i==0 else IncidentSeverity.MEDIUM,
            status=IncidentStatus.RESOLVED if i==2 else IncidentStatus.OPEN,owner_user_id=owner_id,
            summary="Synthetic training scenario. Review recorded stock, thresholds and linked shipments before acting.",
            recommendations=["Review the calculated replenishment quantity and confirm the supplier delivery date."],
            affected_entities=[{"type":"warehouse","id":str(warehouses[i%4].id)},
                {"type":"product","id":str(products[i].id)}, {"type":"shipment","id":str(shipments[i*10+8].id)}],
            resolution="Planner confirmed replenishment in this fictional scenario" if i==2 else None,
            resolved_at=now-timedelta(days=1) if i==2 else None))
    for ctype, name in [(ConnectorType.SAP_BUSINESS_ONE,"SAP Business One"),(ConnectorType.SALESFORCE,"Salesforce")]:
        db.add(Connection(organization_id=org.id,name=f"{name} — Sandbox credentials required",
            connector_type=ctype,status=ConnectorStatus.NOT_CONFIGURED,is_active=False,
            config={"validation_status":"sandbox_credentials_required"}))
    db.flush()


def refresh_derived(db, org, owner, member):
    from app.services.risk_engine import recompute_all
    from app.services.alert_engine import generate_alerts
    token = set_tenant(build_tenant_context(org=org,user=owner,membership=member))
    try:
        set_session_org(db,org.id)
        recompute_all(db)
        generate_alerts(db, deliver_notifications=False)
    finally:
        reset_tenant(token)


def reset_workspace(db, org_id, user_id):
    """Explicit operator allowlist plus current demo-admin membership. No arbitrary targets."""
    if str(org_id) != settings.DEMO_WORKSPACE_ID:
        raise PermissionError("This organization is not the configured demo workspace")
    set_session_org(db,org_id)
    org = db.scalar(select(Organization).where(Organization.id==org_id).with_for_update())
    member = db.scalar(select(Membership).where(Membership.organization_id==org_id,
        Membership.user_id==user_id,Membership.status==MembershipStatus.ACTIVE))
    if not org or (org.settings or {}).get("demo_dataset") != MARKER or not member or member.role_slug not in {"owner","admin"}:
        raise PermissionError("Demo administrator access required")
    # Do not delete anything from a workspace subsequently connected to real systems.
    connections = db.scalars(select(Connection).where(Connection.organization_id==org_id)).all()
    if any(c.credentials_encrypted for c in connections):
        raise ValueError("Disconnect external credentials before resetting the fictional workspace")
    from app.core.database import Base
    clear_tables = {"shipment_events","inventory","sales_orders","purchase_orders","shipments","products",
        "suppliers","warehouses","incidents","alerts","risk_assessments","operational_events",
        "import_jobs","connector_sync_logs","connector_dead_letters","connections","alert_deliveries"}
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in clear_tables:
            db.execute(delete(table).where(table.c.organization_id==org_id))
    db.flush()
    populate(db,org,org.owner_user_id)
    from app.services.audit import write_audit
    write_audit(db, organization_id=org_id, user_id=user_id, action="demo_reset",
        resource="organization", resource_id=str(org_id), detail=MARKER)
    db.commit()
    refresh_derived(db,org,db.get(User,user_id),member)
    return {"reset":True,"organization_id":str(org_id),"synthetic":True}
