"""Read-only SAP Business One Service Layer (OData v4), supervised pilot adapter."""
from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx

from app.connectors.base import Connector, ConnectorError, HealthStatus, SchemaDiscovery, SyncMode, SyncResult
from app.connectors.mapped_sync import apply_records, invalid, validate_mappings
from app.connectors.registry import register_connector
from app.connectors.retry import with_retry
from app.connectors.ssrf import assert_safe_connector_url
from app.models.enums import ConnectorHealth, ConnectorType


@register_connector
class SAPBusinessOneConnector(Connector):
    connector_type = ConnectorType.SAP_BUSINESS_ONE
    display_name = "SAP Business One"
    auth_methods = ["service_layer_session"]
    supports_incremental = False

    def _url(self, path):
        base = str(self.config.get("base_url") or "").rstrip("/") + "/"
        if urlparse(base).path != "/b1s/v2/":
            raise invalid("SAP base_url must end in /b1s/v2")
        url = urljoin(base, path)
        assert_safe_connector_url(url, connector_type=self.connector_type)
        if urlparse(url).netloc != urlparse(base).netloc or not urlparse(url).path.startswith("/b1s/v2/"):
            raise invalid("SAP pagination must remain on the configured Service Layer endpoint")
        return url

    async def _http(self, method, path, **kwargs):
        async def call():
            async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
                response = await client.request(method, self._url(path), **kwargs)
                if response.status_code in {408, 429, 500, 502, 503, 504}:
                    response.raise_for_status()
                return response
        try:
            response = await with_retry(call, retries=2)
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            raise ConnectorError("SAP Service Layer unavailable", failure_class="api_network_failure") from exc
        if not 200 <= response.status_code < 300:
            raise ConnectorError(f"SAP Service Layer HTTP {response.status_code}", retryable=False,
                failure_class="authentication_failure" if response.status_code in {401, 403} else "data_validation_failure")
        return response

    @staticmethod
    def _json(response):
        try:
            data = response.json()
        except ValueError:
            raise invalid("SAP returned malformed JSON") from None
        if not isinstance(data, dict):
            raise invalid("SAP response must be an object")
        return data

    async def authenticate(self):
        self.require_credentials("company_db", "username", "password")
        response = await self._http("POST", "Login", json={"CompanyDB": self.credentials["company_db"],
            "UserName": self.credentials["username"], "Password": self.credentials["password"]})
        data = self._json(response)
        token = data.get("SessionId")
        if not isinstance(token, str) or not token:
            raise invalid("SAP login did not return a session")
        self._access_token = token
        self._cookies = {"B1SESSION": token}
        route = response.cookies.get("ROUTEID")
        if route:
            self._cookies["ROUTEID"] = route
        return token

    async def _collection(self, source, fields, id_field, filters):
        records, seen = [], set()
        path = source
        params = {"$select": ",".join(sorted(fields)), "$orderby": id_field}
        def literal(value):
            if isinstance(value, bool):
                return str(value).lower()
            if isinstance(value, int):
                return str(value)
            return "'" + value.replace("'", "''") + "'"
        if filters:
            params["$filter"] = " and ".join(f"{key} eq {literal(value)}" for key, value in filters.items())
        for _ in range(50):
            url = self._url(path)
            if url in seen:
                raise invalid("SAP pagination cycle")
            seen.add(url)
            response = await self._http("GET", path, params=params, cookies=self._cookies)
            data = self._json(response)
            rows = data.get("value")
            if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
                raise invalid("SAP returned an invalid collection")
            records.extend(rows)
            if len(records) > 10000:
                raise invalid("SAP sync exceeds 10000 records; narrow the pilot dataset")
            path = data.get("@odata.nextLink") or data.get("odata.nextLink")
            if not path:
                return records
            if not isinstance(path, str):
                raise invalid("SAP returned an invalid next link")
            params = None
        raise invalid("SAP sync exceeds 50 pages; narrow the pilot dataset")

    async def _logout(self):
        if self._access_token:
            try:
                await self._http("POST", "Logout", cookies=self._cookies)
            except ConnectorError:
                pass  # Session expiry is bounded on the SAP server.
            finally:
                self._access_token = None
                self._cookies = {}

    async def test_connection(self):
        await self.authenticate()
        try:
            await self._http("GET", "Items", params={"$select": "ItemCode", "$top": "1"}, cookies=self._cookies)
            return True
        finally:
            await self._logout()

    async def discover_schema(self):
        await self.test_connection()
        return SchemaDiscovery(entities=[{"name": name} for name in ("BusinessPartners", "Items", "Orders")])

    async def sync(self, db, mode=SyncMode.FULL):
        specs = validate_mappings(self.config)
        permitted = {"suppliers": "BusinessPartners", "products": "Items", "sales_orders": "Orders"}
        for spec in specs:
            if spec["source"] != permitted[spec["target"]]:
                raise invalid("SAP source must match its canonical target")
            if spec["target"] == "suppliers" and spec.get("filter_equals", {}).get("CardType") != "cSupplier":
                raise invalid("SAP suppliers require CardType=cSupplier")
        result = SyncResult()
        await self.authenticate()
        try:
            with db.begin_nested():
                for spec in specs:
                    fields = {spec["id_field"], *spec["fields"].values(), *spec.get("filter_equals", {}).keys()}
                    records = await self._collection(spec["source"], fields, spec["id_field"], spec.get("filter_equals", {}))
                    apply_records(db, self, spec, records, result)
            # Full bounded refresh on every execution; no unsupported delta cursor.
            return result.finish()
        finally:
            await self._logout()

    async def health(self):
        try:
            await self.test_connection()
            return HealthStatus(ConnectorHealth.HEALTHY)
        except ConnectorError as exc:
            return HealthStatus(ConnectorHealth.DOWN, str(exc))

    def metadata_snapshot(self):
        data = super().metadata_snapshot()
        data["supports"].update(oauth=False, incremental=False)
        data["validation_status"] = "sandbox_validation_required"
        return data
