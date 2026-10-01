"""UPS Tracking API connector — OAuth client credentials + tracking sync."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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
from app.core.config import settings
from app.models import Shipment, ShipmentEvent
from app.models.enums import ConnectorHealth, ConnectorType, ShipmentStatus

DEFAULT_TOKEN_URL = "https://onlinetools.ups.com/security/v1/oauth/token"
DEFAULT_TRACK_BASE = "https://onlinetools.ups.com/api/track/v1/details"


@register_connector
class UPSConnector(Connector):
    connector_type = ConnectorType.UPS
    display_name = "UPS Tracking"

    def _client_id(self) -> str:
        return self.credentials.get("client_id") or settings.UPS_CLIENT_ID

    def _client_secret(self) -> str:
        return self.credentials.get("client_secret") or settings.UPS_CLIENT_SECRET

    def _base_url(self) -> str:
        from app.connectors.ssrf import assert_safe_connector_url

        raw = (
            self.config.get("base_url")
            or settings.UPS_BASE_URL
            or "https://onlinetools.ups.com"
        ).rstrip("/")
        return assert_safe_connector_url(
            raw, connector_type=self.connector_type, field="base_url"
        ).rstrip("/")

    async def authenticate(self) -> str:
        from app.connectors.ssrf import assert_safe_connector_url

        client_id = self._client_id()
        client_secret = self._client_secret()
        if not client_id or not client_secret:
            self.require_credentials("client_id", "client_secret")

        token_url = self.config.get("token_url") or f"{self._base_url()}/security/v1/oauth/token"
        token_url = assert_safe_connector_url(
            token_url, connector_type=self.connector_type, field="token_url"
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                token_url,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code >= 400:
                raise ConnectorError(
                    f"UPS token request failed ({resp.status_code})"
                )
            body = resp.json()
            token = body.get("access_token")
            if not token:
                raise ConnectorError("UPS: access_token missing from token response")
            self._access_token = token
            return token

    async def _track(self, tracking_number: str) -> dict[str, Any]:
        if not self._access_token:
            await self.authenticate()
        track_base = self.config.get("track_url") or f"{self._base_url()}/api/track/v1/details"
        from urllib.parse import quote
        from app.connectors.ssrf import assert_safe_connector_url
        url = assert_safe_connector_url(
            f"{track_base}/{quote(tracking_number, safe='')}",
            connector_type=self.connector_type, field="track_url")
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "transId": f"supply-{tracking_number}",
            "transactionSrc": "Supply",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url, headers=headers, params={"locale": "en_US"})
            if resp.status_code == 401:
                await self.authenticate()
                headers["Authorization"] = f"Bearer {self._access_token}"
                resp = await client.get(url, headers=headers, params={"locale": "en_US"})
            if resp.status_code >= 400:
                raise ConnectorError(
                    f"UPS tracking request failed ({resp.status_code})"
                )
            return resp.json()

    @staticmethod
    def _map_status(code: str | None, description: str | None) -> ShipmentStatus:
        blob = f"{code or ''} {description or ''}".lower()
        if any(x in blob for x in ("delivered", "del")):
            return ShipmentStatus.DELIVERED
        if any(x in blob for x in ("exception", "delay", "held")):
            return ShipmentStatus.DELAYED
        if any(x in blob for x in ("customs",)):
            return ShipmentStatus.CUSTOMS_HOLD
        if any(x in blob for x in ("warehouse", "origin", "pickup")):
            return ShipmentStatus.AT_WAREHOUSE
        return ShipmentStatus.IN_TRANSIT

    async def test_connection(self) -> bool:
        await self.authenticate()
        return bool(self._access_token)

    async def discover_schema(self) -> SchemaDiscovery:
        return SchemaDiscovery(
            entities=[
                {
                    "name": "tracking",
                    "fields": [
                        "trackingNumber",
                        "status",
                        "statusDescription",
                        "location",
                        "activityDate",
                    ],
                }
            ]
        )

    async def sync(self, db: Session, mode: SyncMode = SyncMode.INCREMENTAL) -> SyncResult:
        """Update tenant shipments that have a UPS tracking_number."""
        result = SyncResult()
        await self.authenticate()

        q = select(Shipment).where(
            Shipment.organization_id == self.organization_id,
            Shipment.tracking_number.is_not(None),
        )
        if mode == SyncMode.INCREMENTAL:
            q = q.where(Shipment.status != ShipmentStatus.DELIVERED)

        only = self.config.get("tracking_numbers")
        if only:
            q = q.where(Shipment.tracking_number.in_([str(t) for t in only]))
        shipments = list(db.scalars(q.limit(1001)).all())
        if len(shipments) > 1000:
            raise ConnectorError("UPS sync exceeds 1000 shipments; narrow tracking scope", retryable=False)

        for shipment in shipments:
            tn = (shipment.tracking_number or "").strip()
            if not tn:
                continue
            result.records_processed += 1
            try:
                payload = await self._track(tn)
            except ConnectorError as exc:
                result.records_rejected += 1
                result.errors.append(str(exc))
                continue

            # UPS Track API v1 shape
            track_resp = (payload.get("trackResponse") or {}).get("shipment") or []
            if not track_resp:
                result.records_rejected += 1
                result.errors.append(f"No trackResponse for {tn}")
                continue

            pkg = (track_resp[0].get("package") or [None])[0] or {}
            activities = pkg.get("activity") or []
            current_status = pkg.get("currentStatus") or {}
            status_code = current_status.get("code")
            status_desc = current_status.get("description")
            if not status_desc and activities:
                status_desc = (activities[0].get("status") or {}).get("description")
                status_code = (activities[0].get("status") or {}).get("statusCode")

            new_status = self._map_status(status_code, status_desc)
            location = ""
            if activities:
                loc = activities[0].get("location") or {}
                addr = loc.get("address") or {}
                parts = [addr.get("city"), addr.get("stateProvince"), addr.get("country")]
                location = ", ".join(p for p in parts if p)

            shipment.status = new_status
            if location:
                shipment.current_location = location
            shipment.carrier = shipment.carrier or "UPS"
            if new_status == ShipmentStatus.DELIVERED and shipment.delivered_at is None:
                shipment.delivered_at = datetime.now(timezone.utc)

            # Append newest activity as event when present
            if activities:
                act = activities[0]
                note = (act.get("status") or {}).get("description") or status_desc
                db.add(
                    ShipmentEvent(
                        organization_id=self.organization_id,
                        shipment_id=shipment.id,
                        status=new_status,
                        location=location or shipment.current_location,
                        note=note,
                        occurred_at=datetime.now(timezone.utc),
                    )
                )

            result.records_imported += 1

        db.flush()
        result.cursor = {
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode.value,
        }
        return result.finish()

    async def health(self) -> HealthStatus:
        try:
            ok = await self.test_connection()
            return HealthStatus(
                health=ConnectorHealth.HEALTHY if ok else ConnectorHealth.DEGRADED,
                message="UPS OAuth reachable" if ok else "UPS auth unexpected",
            )
        except Exception as exc:  # noqa: BLE001
            return HealthStatus(health=ConnectorHealth.DOWN, message=str(exc))
