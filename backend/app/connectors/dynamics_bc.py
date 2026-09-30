"""Microsoft Dynamics 365 Business Central connector — real OAuth + BC API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.base import (
    Connector,
    ConnectorError,
    HealthStatus,
    SchemaDiscovery,
    SyncMode,
    SyncResult,
)
from app.connectors.registry import register_connector
from app.models import Product, Shipment
from app.models.enums import ConnectorHealth, ConnectorType, ShipmentStatus

TOKEN_URL_TMPL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
BC_API_BASE = "https://api.businesscentral.dynamics.com/v2.0"


@register_connector
class DynamicsBCConnector(Connector):
    connector_type = ConnectorType.DYNAMICS_BC
    display_name = "Microsoft Dynamics 365 Business Central"

    def _api_base(self) -> str:
        from app.connectors.ssrf import assert_safe_connector_url

        environment = self.config.get("environment") or "production"
        company_id = self.config.get("company_id")
        base = self.config.get("api_base") or BC_API_BASE
        assert_safe_connector_url(base, connector_type=self.connector_type, field="api_base")
        # company_id is resolved during sync if missing
        if company_id:
            return f"{base}/{self.credentials.get('tenant_id')}/{environment}/api/v2.0/companies({company_id})"
        return f"{base}/{self.credentials.get('tenant_id')}/{environment}/api/v2.0"

    def _token_url(self) -> str:
        from app.connectors.ssrf import assert_safe_connector_url

        tenant = self.credentials.get("tenant_id") or self.config.get("tenant_id")
        if not tenant:
            raise ConnectorError("Dynamics BC: tenant_id is required")
        url = TOKEN_URL_TMPL.format(tenant=tenant)
        return assert_safe_connector_url(
            url, connector_type=self.connector_type, field="token_url"
        )

    async def authenticate(self) -> str:
        """Client credentials or authorization-code refresh."""
        self.require_credentials("client_id", "client_secret", "tenant_id")

        data: dict[str, str]
        if self.credentials.get("refresh_token"):
            data = {
                "grant_type": "refresh_token",
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "refresh_token": self.credentials["refresh_token"],
                "scope": self.credentials.get(
                    "scope", "https://api.businesscentral.dynamics.com/.default"
                ),
            }
        else:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "scope": self.credentials.get(
                    "scope", "https://api.businesscentral.dynamics.com/.default"
                ),
            }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self._token_url(), data=data)
            if resp.status_code >= 400:
                raise ConnectorError(
                    f"Dynamics BC token request failed ({resp.status_code})"
                )
            body = resp.json()
            token = body.get("access_token")
            if not token:
                raise ConnectorError("Dynamics BC: access_token missing from token response")
            if body.get("refresh_token"):
                self.credentials["refresh_token"] = body["refresh_token"]
            self._access_token = token
            return token

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self._access_token:
            await self.authenticate()
        url = path if path.startswith("http") else f"{self._api_base()}{path}"
        from app.connectors.ssrf import assert_safe_connector_url
        url = assert_safe_connector_url(url, connector_type=self.connector_type, field="request_url")
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            **(kwargs.pop("headers", {}) or {}),
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.request(method, url, headers=headers, **kwargs)
            if resp.status_code == 401:
                await self.authenticate()
                headers["Authorization"] = f"Bearer {self._access_token}"
                resp = await client.request(method, url, headers=headers, **kwargs)
            if resp.status_code >= 400:
                raise ConnectorError(
                    f"Dynamics BC API request failed ({resp.status_code})"
                )
            if resp.status_code == 204 or not resp.content:
                return None
            return resp.json()

    async def _collection(self, path: str, params: dict | None = None) -> list[dict]:
        """Fetch bounded pages; incomplete results must never advance sync cursors."""
        records: list[dict] = []
        seen: set[str] = set()
        for _ in range(50):
            if path in seen:
                raise ConnectorError("Dynamics BC pagination cycle", retryable=False)
            seen.add(path)
            payload = await self._request("GET", path, params=params)
            page = (payload or {}).get("value")
            if not isinstance(page, list) or any(not isinstance(row, dict) for row in page):
                raise ConnectorError("Dynamics BC malformed collection", retryable=False)
            records.extend(page)
            if len(records) > 10000:
                raise ConnectorError("Dynamics BC record limit exceeded; narrow sync scope", retryable=False)
            next_path = payload.get("@odata.nextLink")
            if not next_path:
                return records
            if not isinstance(next_path, str):
                raise ConnectorError("Dynamics BC malformed next link", retryable=False)
            path, params = next_path, None
        raise ConnectorError("Dynamics BC page limit exceeded; narrow sync scope", retryable=False)

    async def test_connection(self) -> bool:
        await self.authenticate()
        data = await self._request("GET", "/companies")
        companies = (data or {}).get("value") or []
        return len(companies) >= 0  # empty tenant still means auth worked

    async def discover_schema(self) -> SchemaDiscovery:
        await self.authenticate()
        companies = ((await self._request("GET", "/companies")) or {}).get("value") or []
        entities = [
            {"name": "companies", "count_hint": len(companies)},
            {"name": "items", "fields": ["number", "displayName", "type", "unitCost", "unitPrice"]},
            {
                "name": "salesOrders",
                "fields": ["number", "externalDocumentNumber", "orderDate", "status", "totalAmountIncludingTax"],
            },
        ]
        return SchemaDiscovery(entities=entities, raw={"companies": companies})

    async def _ensure_company(self) -> str:
        company_id = self.config.get("company_id")
        if company_id:
            return company_id
        data = await self._request("GET", "/companies")
        companies = (data or {}).get("value") or []
        if not companies:
            raise ConnectorError("Dynamics BC: no companies found for this tenant")
        company_id = companies[0]["id"]
        self.config["company_id"] = company_id
        return company_id

    async def sync(self, db: Session, mode: SyncMode = SyncMode.INCREMENTAL) -> SyncResult:
        result = SyncResult()
        await self.authenticate()
        await self._ensure_company()

        # --- Items → Products ---
        items_path = "/items"
        params: dict[str, str] = {"$top": "200"}
        if mode == SyncMode.INCREMENTAL and self.cursor.get("items_modified"):
            params["$filter"] = f"lastModifiedDateTime gt {self.cursor['items_modified']}"

        items = await self._collection(items_path, params=params)
        latest_item_mod = self.cursor.get("items_modified")

        for item in items:
            result.records_processed += 1
            external_id = str(item.get("id") or item.get("number") or "")
            sku = str(item.get("number") or external_id)
            if not sku:
                result.records_rejected += 1
                result.errors.append("Item missing number/id")
                continue
            existing = db.scalar(
                select(Product).where(
                    Product.organization_id == self.organization_id,
                    Product.external_id == external_id,
                )
            )
            if existing is None:
                existing = db.scalar(
                    select(Product).where(
                        Product.organization_id == self.organization_id,
                        Product.sku == sku,
                    )
                )
            if existing is None:
                existing = Product(
                    organization_id=self.organization_id,
                    sku=sku,
                    name=item.get("displayName") or sku,
                    category=item.get("itemCategoryCode") or item.get("type") or "general",
                    unit_cost=float(item.get("unitCost") or 0),
                    unit_price=float(item.get("unitPrice") or 0),
                    lead_time_days=14,
                    external_id=external_id,
                )
                db.add(existing)
            else:
                existing.name = item.get("displayName") or existing.name
                existing.unit_cost = float(item.get("unitCost") or existing.unit_cost)
                existing.unit_price = float(item.get("unitPrice") or existing.unit_price)
                existing.external_id = external_id
            result.records_imported += 1
            mod = item.get("lastModifiedDateTime")
            if mod and (latest_item_mod is None or mod > latest_item_mod):
                latest_item_mod = mod

        # --- Sales Orders → Shipments ---
        orders_path = "/salesOrders"
        order_params: dict[str, str] = {"$top": "200"}
        if mode == SyncMode.INCREMENTAL and self.cursor.get("orders_modified"):
            order_params["$filter"] = f"lastModifiedDateTime gt {self.cursor['orders_modified']}"

        orders = await self._collection(orders_path, params=order_params)
        latest_order_mod = self.cursor.get("orders_modified")

        for order in orders:
            result.records_processed += 1
            external_id = str(order.get("id") or order.get("number") or "")
            reference = str(order.get("number") or order.get("externalDocumentNumber") or external_id)
            if not reference:
                result.records_rejected += 1
                result.errors.append("Sales order missing number")
                continue

            existing = db.scalar(
                select(Shipment).where(
                    Shipment.organization_id == self.organization_id,
                    Shipment.external_id == external_id,
                )
            )
            if existing is None:
                existing = db.scalar(
                    select(Shipment).where(
                        Shipment.organization_id == self.organization_id,
                        Shipment.reference == reference,
                    )
                )

            order_date = order.get("orderDate") or order.get("postingDate")
            try:
                shipped_at = (
                    datetime.fromisoformat(str(order_date).replace("Z", "+00:00"))
                    if order_date
                    else datetime.now(timezone.utc)
                )
            except ValueError:
                shipped_at = datetime.now(timezone.utc)

            status_raw = (order.get("status") or "Open").lower()
            if "ship" in status_raw or status_raw == "released":
                status = ShipmentStatus.IN_TRANSIT
            elif "invoice" in status_raw or "complete" in status_raw:
                status = ShipmentStatus.DELIVERED
            else:
                status = ShipmentStatus.IN_TRANSIT

            ship_to = order.get("shipToName") or order.get("sellToCustomerName") or "Customer"
            bill_to = order.get("billToName") or order.get("sellToCustomerName") or "Origin"

            if existing is None:
                existing = Shipment(
                    id=uuid4(),
                    organization_id=self.organization_id,
                    reference=reference,
                    origin=bill_to,
                    destination=ship_to,
                    carrier="Dynamics BC",
                    current_location=ship_to,
                    status=status,
                    delay_risk_score=0.0,
                    units=int(order.get("totalQuantity") or 0),
                    value_usd=float(order.get("totalAmountIncludingTax") or order.get("totalAmountExcludingTax") or 0),
                    shipped_at=shipped_at,
                    eta=shipped_at,
                    external_id=external_id,
                    tracking_number=order.get("externalDocumentNumber"),
                )
                db.add(existing)
            else:
                existing.destination = ship_to
                existing.status = status
                existing.value_usd = float(
                    order.get("totalAmountIncludingTax") or existing.value_usd
                )
                existing.external_id = external_id
            result.records_imported += 1
            mod = order.get("lastModifiedDateTime")
            if mod and (latest_order_mod is None or mod > latest_order_mod):
                latest_order_mod = mod

        db.flush()
        result.cursor = {
            "items_modified": latest_item_mod,
            "orders_modified": latest_order_mod,
            "company_id": self.config.get("company_id"),
        }
        return result.finish()

    async def health(self) -> HealthStatus:
        try:
            ok = await self.test_connection()
            return HealthStatus(
                health=ConnectorHealth.HEALTHY if ok else ConnectorHealth.DEGRADED,
                message="Dynamics BC reachable" if ok else "Dynamics BC auth ok but unexpected response",
            )
        except Exception as exc:  # noqa: BLE001 — surface as health
            return HealthStatus(health=ConnectorHealth.DOWN, message=str(exc))
