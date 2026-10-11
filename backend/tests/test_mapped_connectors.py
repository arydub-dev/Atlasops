"""Contract tests with synthetic provider responses; no sandbox claim."""
import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from app.connectors.base import ConnectorError
from app.connectors.mapped_sync import validate_mappings
from app.connectors.salesforce import SalesforceConnector
from app.connectors.sap_business_one import SAPBusinessOneConnector
from app.connectors.ssrf import SSRFError
from app.core.config import get_settings
from app.models import Connection, Product, SalesOrder
from app.models.enums import ConnectorType
from app.tenancy.rls import set_session_org

PRODUCT = {"source":"Product2", "target":"products", "id_field":"Id", "fields":{
    "sku":"ProductCode", "name":"Name", "category":"Family", "unit_cost":"Cost__c",
    "unit_price":"Price__c", "lead_time_days":"LeadDays__c"}}
ORDER = {"source":"Order", "target":"sales_orders", "id_field":"Id", "fields":{
    "reference":"OrderNumber", "status":"Status", "currency":"CurrencyIsoCode", "total_amount":"TotalAmount", "ordered_at":"EffectiveDate"},
    "status_map":{"Draft":"draft", "Activated":"confirmed"}}
ROW = {"Id":"p1", "ProductCode":"PART-1", "Name":"Part", "Family":"Parts", "Cost__c":5, "Price__c":10, "LeadDays__c":3}
ORDER_ROW = {"Id":"o1", "OrderNumber":"ORDER-1", "Status":"Activated", "CurrencyIsoCode":"USD", "TotalAmount":20, "EffectiveDate":"2026-10-03"}


def connector(db, org_a, specs, cls=SalesforceConnector):
    oid = org_a[0].id
    set_session_org(db, oid)
    conn = Connection(id=uuid4(), organization_id=oid, name="Pilot", connector_type=cls.connector_type)
    db.add(conn)
    db.commit()
    set_session_org(db, oid)
    return cls(organization_id=oid, config={"sync_entities":deepcopy(specs), "_connection_id":str(conn.id)})


def test_salesforce_products_orders_refresh_without_duplicates(db, org_a):
    c = connector(db, org_a, [PRODUCT, ORDER])
    c.authenticate = AsyncMock(return_value="token")
    c._soql = AsyncMock(side_effect=[([ROW], True), ([ORDER_ROW], True)])
    result = asyncio.run(c.sync(db))
    assert result.records_imported == 2
    db.commit()
    set_session_org(db, org_a[0].id)
    c._soql = AsyncMock(side_effect=[([{**ROW, "Price__c":12}], True), ([ORDER_ROW], True)])
    asyncio.run(c.sync(db))
    assert len(db.scalars(select(Product)).all()) == 1
    assert db.scalar(select(Product)).unit_price == 12
    order = db.scalar(select(SalesOrder))
    assert order.status.value == "confirmed"
    assert order.meta["scope"] == "order_header_only"
    assert len(db.scalars(select(SalesOrder)).all()) == 1


def test_mapping_failure_rolls_back_earlier_entities(db, org_a):
    c = connector(db, org_a, [PRODUCT, ORDER])
    c.authenticate = AsyncMock(return_value="token")
    c._soql = AsyncMock(side_effect=[([ROW], True), ([{**ORDER_ROW, "Status":"Mystery"}], True)])
    with pytest.raises(ConnectorError, match="Unmapped"):
        asyncio.run(c.sync(db))
    assert db.scalar(select(Product)) is None
    assert db.scalar(select(SalesOrder)) is None


@pytest.mark.parametrize("change", [{"Cost__c":None}, {"Cost__c":"NaN"}, {"LeadDays__c":1.5}, {"ProductCode":"X"*65}])
def test_invalid_values_never_invent_defaults(db, org_a, change):
    c = connector(db, org_a, [PRODUCT])
    c.authenticate = AsyncMock(return_value="token")
    c._soql = AsyncMock(return_value=([{**ROW, **change}], True))
    with pytest.raises(ConnectorError):
        asyncio.run(c.sync(db))
    assert db.scalar(select(Product)) is None


def test_other_source_collision_rejected(db, org_a):
    c = connector(db, org_a, [PRODUCT])
    db.add(Product(organization_id=org_a[0].id, sku="PART-1", name="Manual", category="Parts", unit_cost=7, unit_price=15))
    db.commit()
    set_session_org(db, org_a[0].id)
    c.authenticate = AsyncMock(return_value="token")
    c._soql = AsyncMock(return_value=([ROW], True))
    with pytest.raises(ConnectorError, match="different source"):
        asyncio.run(c.sync(db))
    assert db.scalar(select(Product)).name == "Manual"


def test_incomplete_page_is_not_success(db, org_a):
    c = connector(db, org_a, [PRODUCT])
    c.authenticate = AsyncMock(return_value="token")
    c._soql = AsyncMock(return_value=([ROW], False))
    with pytest.raises(ConnectorError, match="pagination"):
        asyncio.run(c.sync(db))
    assert db.scalar(select(Product)) is None


def test_mapping_rejects_query_injection_and_supplier_inference():
    mapping = deepcopy(PRODUCT)
    mapping["source"] = "Product2 WHERE Name != null"
    with pytest.raises(ConnectorError):
        validate_mappings({"sync_entities":[mapping]})
    with pytest.raises(ConnectorError):
        validate_mappings({"sync_entities":[{"source":"Account", "target":"suppliers", "id_field":"Id", "fields":{"name":"Name"}}]})


def test_salesforce_next_page_cannot_receive_token_on_other_host():
    c = SalesforceConnector(organization_id=uuid4(), config={"instance_url":"https://one.my.salesforce.com"})
    c._access_token = "secret"
    with pytest.raises(ConnectorError, match="changed instance"):
        asyncio.run(c._request("GET", "https://two.my.salesforce.com/steal"))


def test_sap_http_session_pagination_and_refresh(db, org_a, monkeypatch):
    monkeypatch.setattr(get_settings(), "SAP_BUSINESS_ONE_ALLOWED_ORIGINS", "https://erp.example.com")
    spec = deepcopy(PRODUCT)
    spec["source"] = "Items"
    c = connector(db, org_a, [spec], SAPBusinessOneConnector)
    c.config["base_url"] = "https://erp.example.com/b1s/v2"
    c.credentials = {"company_db":"TEST", "username":"reader", "password":"test-only"}
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path.endswith("Login"):
            return httpx.Response(200, json={"SessionId":"session"}, headers={"set-cookie":"ROUTEID=.node1"})
        assert "B1SESSION=session" in request.headers["cookie"]
        if request.url.path.endswith("Logout"):
            return httpx.Response(204)
        if request.url.params.get("$skip"):
            return httpx.Response(200, json={"value":[]})
        return httpx.Response(200, json={"value":[ROW], "@odata.nextLink":"Items?$skip=1"})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    assert asyncio.run(c.sync(db)).records_imported == 1
    assert asyncio.run(c.sync(db)).records_imported == 1
    assert len(db.scalars(select(Product)).all()) == 1
    assert calls[-1].url.path.endswith("Logout")
    assert c._access_token is None


def test_sap_rejects_unapproved_or_cross_origin_urls(monkeypatch):
    monkeypatch.setattr(get_settings(), "SAP_BUSINESS_ONE_ALLOWED_ORIGINS", "https://erp.example.com")
    c = SAPBusinessOneConnector(organization_id=uuid4(), config={"base_url":"https://erp.example.com/b1s/v2"})
    with pytest.raises(SSRFError):
        c._url("https://attacker.example.com/b1s/v2/Items")
    with pytest.raises(ConnectorError):
        c._url("/different/Items")
    c.config["base_url"] = "https://127.0.0.1/b1s/v2"
    with pytest.raises(SSRFError):
        c._url("Items")
