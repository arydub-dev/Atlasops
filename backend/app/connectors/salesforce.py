"""Salesforce connector — OAuth password / client credentials / refresh + SOQL."""
from __future__ import annotations

import json
import logging
import re
from typing import Any
from uuid import uuid4
from urllib.parse import urlparse

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
from app.connectors.retry import with_retry
from app.models import Supplier
from app.models.enums import ConnectorHealth, ConnectorType

logger = logging.getLogger("supply.connectors.salesforce")

LOGIN_URL = "https://login.salesforce.com/services/oauth2/token"
TEST_LOGIN_URL = "https://test.salesforce.com/services/oauth2/token"

_SOQL_IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
DEFAULT_MAX_PAGES = 50
DEFAULT_MAX_RECORDS = 10_000


def _soql_ident(value: str, *, field: str) -> str:
    raw = (value or "").strip()
    if not _SOQL_IDENT.match(raw):
        raise ConnectorError(
            f"Invalid Salesforce {field}",
            retryable=False,
            failure_class="data_validation_failure",
        )
    return raw


def _http_failure_class(status: int) -> str:
    if status in {401, 403}:
        return "authentication_failure"
    if status == 429:
        return "rate_limiting"
    if status in {408, 425, 500, 502, 503, 504} or status >= 500:
        return "api_network_failure"
    return "unknown_failure"


def _safe_salesforce_error(resp: httpx.Response) -> str:
    """Operator-safe error: status + Salesforce error code, never raw bodies."""
    code = ""
    try:
        body = resp.json()
        if isinstance(body, dict):
            code = str(body.get("error") or body.get("errorCode") or "")
        elif isinstance(body, list) and body and isinstance(body[0], dict):
            code = str(body[0].get("errorCode") or body[0].get("error") or "")
    except Exception:  # noqa: BLE001 — body may be HTML/empty
        code = ""
    code = re.sub(r"[^A-Za-z0-9_.-]", "", code)[:80]
    suffix = f" {code}" if code else ""
    return f"Salesforce HTTP {resp.status_code}{suffix}".strip()


@register_connector
class SalesforceConnector(Connector):
    connector_type = ConnectorType.SALESFORCE
    display_name = "Salesforce"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._instance_url: str | None = self.config.get("instance_url")

    def _http_retries(self) -> int:
        raw = self.config.get("http_retries")
        if raw is None:
            return 3
        try:
            return max(0, min(int(raw), 8))
        except (TypeError, ValueError):
            return 3

    def _max_pages(self) -> int:
        try:
            return max(1, min(int(self.config.get("max_pages") or DEFAULT_MAX_PAGES), 200))
        except (TypeError, ValueError):
            return DEFAULT_MAX_PAGES

    def _max_records(self) -> int:
        try:
            return max(1, min(int(self.config.get("max_records") or DEFAULT_MAX_RECORDS), 50_000))
        except (TypeError, ValueError):
            return DEFAULT_MAX_RECORDS

    def _token_endpoint(self) -> str:
        from app.connectors.ssrf import assert_safe_connector_url

        if self.config.get("sandbox"):
            url = TEST_LOGIN_URL
        else:
            url = self.config.get("token_url") or LOGIN_URL
        return assert_safe_connector_url(
            url, connector_type=self.connector_type, field="token_url"
        )

    async def authenticate(self) -> str:
        self.require_credentials("client_id", "client_secret")

        data: dict[str, str]
        if self.credentials.get("refresh_token"):
            data = {
                "grant_type": "refresh_token",
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "refresh_token": self.credentials["refresh_token"],
            }
        elif self.credentials.get("username") and self.credentials.get("password"):
            # Password grant (often used with security token appended to password)
            password = self.credentials["password"]
            if self.credentials.get("security_token"):
                password = password + self.credentials["security_token"]
            data = {
                "grant_type": "password",
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "username": self.credentials["username"],
                "password": password,
            }
        else:
            # Client credentials (enabled on some Connected Apps)
            data = {
                "grant_type": "client_credentials",
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
            }

        async def _token_call() -> httpx.Response:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(self._token_endpoint(), data=data)
                if resp.status_code in _RETRYABLE_STATUS:
                    resp.raise_for_status()
                return resp

        try:
            resp = await with_retry(_token_call, retries=self._http_retries())
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            raise ConnectorError(
                f"Salesforce token request failed ({status})",
                retryable=True,
                failure_class=_http_failure_class(status),
                status_code=status,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise ConnectorError(
                "Salesforce token request timed out or could not connect",
                retryable=True,
                failure_class="api_network_failure",
            ) from exc

        if resp.status_code >= 400:
            raise ConnectorError(
                _safe_salesforce_error(resp),
                retryable=False,
                failure_class="authentication_failure",
                status_code=resp.status_code,
            )
        try:
            body = resp.json()
        except json.JSONDecodeError as exc:
            raise ConnectorError(
                "Salesforce token response was not valid JSON",
                retryable=False,
                failure_class="data_validation_failure",
            ) from exc
        token = body.get("access_token") if isinstance(body, dict) else None
        instance = body.get("instance_url") if isinstance(body, dict) else None
        if not token:
            raise ConnectorError(
                "Salesforce: access_token missing from token response",
                retryable=False,
                failure_class="authentication_failure",
            )
        if instance:
            self._instance_url = instance
        if isinstance(body, dict) and body.get("refresh_token"):
            self.credentials["refresh_token"] = body["refresh_token"]
        self._access_token = token
        logger.info(
            "salesforce_authenticated org_id=%s instance_host=%s",
            self.organization_id,
            (self._instance_url or "").split("/")[2] if self._instance_url else "",
        )
        return token

    def _api_root(self) -> str:
        if not self._instance_url:
            raise ConnectorError(
                "Salesforce: instance_url unknown — authenticate first",
                retryable=False,
                failure_class="authentication_failure",
            )
        version = self.config.get("api_version") or "v59.0"
        return f"{self._instance_url.rstrip('/')}/services/data/{version}"

    def _resolve_api_url(self, path: str) -> str:
        """Join SOQL paths and Salesforce ``nextRecordsUrl`` values correctly.

        ``nextRecordsUrl`` is typically ``/services/data/vXX.X/query/<id>``
        (instance-root relative), not relative to ``/services/data/vXX.X``.
        """
        if path.startswith("http://") or path.startswith("https://"):
            return path
        instance = (self._instance_url or "").rstrip("/")
        if path.startswith("/services/"):
            if not instance:
                raise ConnectorError(
                    "Salesforce: instance_url unknown — authenticate first",
                    retryable=False,
                    failure_class="authentication_failure",
                )
            return f"{instance}{path}"
        return f"{self._api_root()}{path}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        from app.connectors.ssrf import assert_safe_connector_url

        if not self._access_token:
            await self.authenticate()
        url = self._resolve_api_url(path)
        assert_safe_connector_url(url, connector_type=self.connector_type, field="api_url")
        if urlparse(url).netloc != urlparse(self._instance_url or "").netloc:
            raise ConnectorError("Salesforce pagination changed instance", retryable=False, failure_class="data_validation_failure")

        async def _call(*, refreshed: bool = False) -> httpx.Response:
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
                **(kwargs.get("headers") or {}),
            }
            req_kwargs = {k: v for k, v in kwargs.items() if k != "headers"}
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.request(method, url, headers=headers, **req_kwargs)
                if resp.status_code == 401 and not refreshed:
                    await self.authenticate()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    resp = await client.request(method, url, headers=headers, **req_kwargs)
                if resp.status_code in _RETRYABLE_STATUS:
                    resp.raise_for_status()
                return resp

        try:
            resp = await with_retry(lambda: _call(), retries=self._http_retries())
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            raise ConnectorError(
                f"Salesforce API failed ({status})",
                retryable=True,
                failure_class=_http_failure_class(status),
                status_code=status,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise ConnectorError(
                "Salesforce API timed out or could not connect",
                retryable=True,
                failure_class="api_network_failure",
            ) from exc

        if resp.status_code in {401, 403}:
            raise ConnectorError(
                _safe_salesforce_error(resp),
                retryable=False,
                failure_class="authentication_failure",
                status_code=resp.status_code,
            )
        if resp.status_code >= 400:
            raise ConnectorError(
                _safe_salesforce_error(resp),
                retryable=False,
                failure_class=_http_failure_class(resp.status_code),
                status_code=resp.status_code,
            )
        if resp.status_code == 204 or not resp.content:
            return None
        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            raise ConnectorError(
                "Salesforce returned a malformed JSON response",
                retryable=False,
                failure_class="data_validation_failure",
                status_code=resp.status_code,
            ) from exc

    async def _soql(self, query: str) -> tuple[list[dict[str, Any]], bool]:
        """Fetch all SOQL pages. Returns (records, complete).

        ``complete`` is False when a safety cap stopped pagination before Salesforce
        reported ``done`` — callers must not advance the incremental cursor.
        """
        data = await self._request("GET", "/query", params={"q": query})
        def page_records(page):
            if not isinstance(page, dict) or not isinstance(page.get("records"), list) or any(not isinstance(r, dict) for r in page["records"]):
                raise ConnectorError("Salesforce returned an invalid record page", retryable=False, failure_class="data_validation_failure")
            if page.get("done") is False and not page.get("nextRecordsUrl"):
                raise ConnectorError("Salesforce returned an incomplete page without a continuation", retryable=False, failure_class="data_validation_failure")
            return page["records"]

        records = list(page_records(data))
        pages = 1
        max_pages = self._max_pages()
        max_records = self._max_records()
        while data and data.get("nextRecordsUrl"):
            if pages >= max_pages or len(records) >= max_records:
                logger.warning(
                    "salesforce_pagination_capped org_id=%s pages=%s records=%s",
                    self.organization_id,
                    pages,
                    len(records),
                )
                return records[:max_records], False
            data = await self._request("GET", data["nextRecordsUrl"])
            batch = list(page_records(data))
            records.extend(batch)
            pages += 1
            if not batch and not (data or {}).get("nextRecordsUrl"):
                break
        done = not bool(data and data.get("nextRecordsUrl"))
        if len(records) > max_records:
            return records[:max_records], False
        logger.info(
            "salesforce_soql_complete org_id=%s pages=%s records=%s done=%s",
            self.organization_id,
            pages,
            len(records),
            done,
        )
        return records, done

    async def test_connection(self) -> bool:
        await self.authenticate()
        data = await self._request("GET", "/")
        return bool(data)

    async def discover_schema(self) -> SchemaDiscovery:
        await self.authenticate()
        account = await self._request("GET", "/sobjects/Account/describe")
        opportunity = await self._request("GET", "/sobjects/Opportunity/describe")
        custom_object = self.config.get("supplier_object")
        entities = [
            {
                "name": "Account",
                "fields": [f["name"] for f in (account or {}).get("fields", [])[:40]],
            },
            {
                "name": "Opportunity",
                "fields": [f["name"] for f in (opportunity or {}).get("fields", [])[:40]],
            },
        ]
        if custom_object:
            ident = _soql_ident(str(custom_object), field="supplier_object")
            desc = await self._request("GET", f"/sobjects/{ident}/describe")
            entities.append(
                {
                    "name": ident,
                    "fields": [f["name"] for f in (desc or {}).get("fields", [])[:40]],
                }
            )
        return SchemaDiscovery(entities=entities)

    async def sync(self, db: Session, mode: SyncMode = SyncMode.INCREMENTAL) -> SyncResult:
        """Explicit mapped sync when configured; preserve legacy connections."""
        if "sync_entities" in self.config:
            return await self._sync_mapped(db)
        from app.core.config import get_settings
        if get_settings().requires_secure_boot:
            raise ConnectorError("Configure explicit entity mappings before production sync", retryable=False, failure_class="data_validation_failure")
        result = SyncResult()
        await self.authenticate()

        supplier_object = _soql_ident(
            str(self.config.get("supplier_object") or "Account"), field="supplier_object"
        )
        name_field = _soql_ident(str(self.config.get("name_field") or "Name"), field="name_field")
        country_field = _soql_ident(
            str(self.config.get("country_field") or "BillingCountry"), field="country_field"
        )
        region_field = _soql_ident(
            str(self.config.get("region_field") or "BillingState"), field="region_field"
        )
        category_field = _soql_ident(
            str(self.config.get("category_field") or "Type"), field="category_field"
        )
        id_field = "Id"

        where = "IsDeleted = false" if supplier_object == "Account" else "Id != null"
        if mode == SyncMode.INCREMENTAL and self.cursor.get("system_modstamp"):
            # Bind cursor as a quoted SOQL datetime literal after validation.
            cursor_raw = str(self.cursor["system_modstamp"])
            if not re.fullmatch(r"[0-9T:\.\+\-Z]{10,40}", cursor_raw):
                raise ConnectorError(
                    "Invalid SystemModstamp cursor",
                    retryable=False,
                    failure_class="data_validation_failure",
                )
            where += f" AND SystemModstamp > {cursor_raw}"

        fields = [id_field, name_field, country_field, region_field, category_field, "SystemModstamp"]
        # Opportunity path: treat partner accounts on open opps as suppliers when configured.
        # No SOQL LIMIT — Salesforce pages via nextRecordsUrl; a LIMIT would cap the whole query.
        if supplier_object == "Opportunity":
            fields = ["Id", "Name", "AccountId", "StageName", "Amount", "SystemModstamp"]
            soql = (
                f"SELECT {', '.join(fields)} FROM Opportunity "
                f"WHERE IsClosed = false ORDER BY SystemModstamp ASC"
            )
        else:
            soql = (
                f"SELECT {', '.join(fields)} FROM {supplier_object} "
                f"WHERE {where} ORDER BY SystemModstamp ASC"
            )

        try:
            records, complete = await self._soql(soql)
        except ConnectorError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ConnectorError(
                "Salesforce query failed",
                retryable=True,
                failure_class="unknown_failure",
            ) from exc

        if not complete:
            result.incomplete = True
            result.failure_class = "unknown_failure"
            result.errors.append(
                "Salesforce sync did not finish: pagination stopped before the remote dataset "
                "was fully retrieved. The incremental cursor was not advanced."
            )

        pending_by_external: dict[str, Supplier] = {}
        latest_mod = self.cursor.get("system_modstamp")

        for rec in records:
            result.records_processed += 1
            external_id = str(rec.get(id_field) or "").strip()
            if supplier_object == "Opportunity":
                name = rec.get("Name") or (f"Opportunity {external_id}" if external_id else "")
                country = "Unknown"
                region = rec.get("StageName") or "Opportunity"
                category = "opportunity"
            else:
                name = rec.get(name_field) or external_id
                country = rec.get(country_field) or "Unknown"
                region = rec.get(region_field) or "Unknown"
                category = rec.get(category_field) or "general"

            if not external_id:
                result.records_rejected += 1
                result.errors.append("Record missing Salesforce Id")
                continue
            if not name:
                result.records_rejected += 1
                result.errors.append(f"Record {external_id} missing name")
                continue

            existing = pending_by_external.get(external_id)
            if existing is None:
                existing = db.scalar(
                    select(Supplier).where(
                        Supplier.organization_id == self.organization_id,
                        Supplier.external_id == external_id,
                    )
                )
            if existing is None:
                existing = Supplier(
                    id=uuid4(),
                    organization_id=self.organization_id,
                    name=name,
                    country=str(country)[:100],
                    region=str(region)[:100],
                    category=str(category)[:100],
                    external_id=external_id,
                    supplier_score=80.0,
                    delivery_reliability=90.0,
                    average_delay_days=1.0,
                    order_fulfillment_rate=95.0,
                    defect_rate=1.0,
                    is_active=True,
                )
                db.add(existing)
            else:
                existing.name = name
                existing.country = str(country)[:100]
                existing.region = str(region)[:100]
                existing.category = str(category)[:100]
            pending_by_external[external_id] = existing
            result.records_imported += 1
            mod = rec.get("SystemModstamp")
            if mod and (latest_mod is None or str(mod) > str(latest_mod)):
                latest_mod = mod

        db.flush()
        # Only persist a new cursor when the remote dataset was fully retrieved.
        if complete:
            result.cursor = {"system_modstamp": latest_mod, "supplier_object": supplier_object}
        else:
            result.cursor = dict(self.cursor) if self.cursor else None
        return result.finish()

    async def _sync_mapped(self, db: Session) -> SyncResult:
        from app.connectors.mapped_sync import apply_records, invalid, validate_mappings

        specs = validate_mappings(self.config)
        result = SyncResult()
        await self.authenticate()
        with db.begin_nested():
            for spec in specs:
                fields = {spec["id_field"], *spec["fields"].values(), *spec.get("filter_equals", {}).keys()}
                def literal(value):
                    if isinstance(value, bool):
                        return str(value).lower()
                    if isinstance(value, int):
                        return str(value)
                    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
                filters = spec.get("filter_equals", {})
                where = " WHERE " + " AND ".join(f"{key} = {literal(value)}" for key, value in filters.items()) if filters else ""
                query = f"SELECT {', '.join(sorted(fields))} FROM {spec['source']}{where} ORDER BY {spec['id_field']} ASC"
                records, complete = await self._soql(query)
                if not complete:
                    raise invalid("Salesforce mapped sync exceeded pagination limits; no data was committed")
                apply_records(db, self, spec, records, result)
        # Full, bounded refresh; deletions and change-data capture are not inferred.
        return result.finish()

    async def health(self) -> HealthStatus:
        try:
            ok = await self.test_connection()
            return HealthStatus(
                health=ConnectorHealth.HEALTHY if ok else ConnectorHealth.DEGRADED,
                message="Salesforce reachable" if ok else "Unexpected Salesforce response",
                details={"instance_host": (self._instance_url or "").split("/")[2] if self._instance_url else ""},
            )
        except ConnectorError as exc:
            return HealthStatus(
                health=ConnectorHealth.DOWN,
                message=str(exc),
                details={"failure_class": exc.failure_class},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("salesforce_health_failed org_id=%s", self.organization_id)
            return HealthStatus(
                health=ConnectorHealth.DOWN,
                message="Salesforce health check failed",
                details={"error_type": type(exc).__name__},
            )
