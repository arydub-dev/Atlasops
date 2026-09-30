"""Alert channel delivery — email (Resend), webhook, future Slack/Teams."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_str
from app.core.html_safe import escape_html
from app.core.outbound_url import assert_safe_outbound_url
from app.integrations import email as email_client
from app.integrations import flags
from app.models import Alert, AlertDelivery, Membership, Organization, User, WebhookEndpoint
from app.models.enums import AlertChannel, DeliveryStatus, MembershipStatus

logger = logging.getLogger("supply.alerts.channels")


def urlparse_host(url: str) -> str:
    from urllib.parse import urlparse

    try:
        return urlparse(url).hostname or "invalid-url"
    except Exception:  # noqa: BLE001
        return "invalid-url"


def _signed_webhook_headers(secret_encrypted: bytes | None, body: bytes) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "User-Agent": "ATLASOPS-Webhook/1.0"}
    if not secret_encrypted:
        return headers
    try:
        secret = decrypt_str(secret_encrypted)
    except Exception:  # noqa: BLE001
        return headers
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    headers["X-Atlasops-Signature"] = f"sha256={digest}"
    return headers


def _post_json(url: str, payload: dict[str, Any], *, secret_encrypted: bytes | None = None) -> httpx.Response:
    body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    headers = _signed_webhook_headers(secret_encrypted, body)
    with httpx.Client(timeout=10.0, follow_redirects=False) as client:
        return client.post(url, content=body, headers=headers)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _org_alert_emails(db: Session, org_id: UUID) -> list[str]:
    rows = db.execute(
        select(User.email)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.organization_id == org_id,
            Membership.status == MembershipStatus.ACTIVE,
            Membership.role_slug.in_(["owner", "admin", "operations_director", "operations_manager"]),
        )
    ).all()
    return [r[0] for r in rows if r[0]]


def _record(
    db: Session,
    *,
    org_id: UUID,
    alert_id: UUID,
    channel: AlertChannel,
    status: DeliveryStatus,
    destination: str | None,
    response: str | None,
) -> AlertDelivery:
    row = AlertDelivery(
        organization_id=org_id,
        alert_id=alert_id,
        channel=channel,
        status=status,
        destination=destination,
        response=(response or "")[:2000] if response else None,
        attempts=1,
        sent_at=_utcnow() if status == DeliveryStatus.SENT else None,
    )
    db.add(row)
    return row


def dispatch_alert(db: Session, alert: Alert) -> list[AlertDelivery]:
    """Fan-out a newly created alert to configured channels."""
    deliveries: list[AlertDelivery] = []
    org_id = alert.organization_id

    # Always mark in-app as delivered (alert row itself is the channel).
    deliveries.append(
        _record(
            db,
            org_id=org_id,
            alert_id=alert.id,
            channel=AlertChannel.IN_APP,
            status=DeliveryStatus.SENT,
            destination="mission-control",
            response="in_app",
        )
    )

    if flags.is_enabled("alert_email_delivery", default=True):
        recipients = _org_alert_emails(db, org_id)
        if recipients:
            result = email_client.send_email(
                to=recipients,
                subject=f"[ATLASOPS] {alert.title}",
                html=(
                    f"<p><strong>{escape_html(alert.title)}</strong></p>"
                    f"<p>{escape_html(alert.message)}</p>"
                ),
                text=f"{alert.title}\n\n{alert.message}",
            )
            status = (
                DeliveryStatus.SENT
                if result.get("ok")
                else DeliveryStatus.SKIPPED
                if result.get("skipped")
                else DeliveryStatus.FAILED
            )
            deliveries.append(
                _record(
                    db,
                    org_id=org_id,
                    alert_id=alert.id,
                    channel=AlertChannel.EMAIL,
                    status=status,
                    destination=",".join(recipients[:10]),
                    response=str(result),
                )
            )

    # Org webhook endpoints subscribed to "alert.*" or "*"
    endpoints = db.scalars(
        select(WebhookEndpoint).where(
            WebhookEndpoint.organization_id == org_id,
            WebhookEndpoint.is_active.is_(True),
        )
    ).all()
    payload: dict[str, Any] = {
        "type": "alert.created",
        "alert": {
            "id": str(alert.id),
            "title": alert.title,
            "message": alert.message,
            "priority": alert.priority.value if hasattr(alert.priority, "value") else str(alert.priority),
            "alert_type": alert.alert_type.value
            if hasattr(alert.alert_type, "value")
            else str(alert.alert_type),
            "entity_type": alert.entity_type,
            "entity_id": str(alert.entity_id) if alert.entity_id else None,
        },
    }
    for ep in endpoints:
        events = ep.events or []
        if events and "*" not in events and "alert.created" not in events and "alert.*" not in events:
            continue
        try:
            safe_url = assert_safe_outbound_url(ep.url, field="webhook.url")
            resp = _post_json(safe_url, payload, secret_encrypted=ep.secret_encrypted)
            status = DeliveryStatus.SENT if resp.status_code < 300 else DeliveryStatus.FAILED
            deliveries.append(
                _record(
                    db,
                    org_id=org_id,
                    alert_id=alert.id,
                    channel=AlertChannel.WEBHOOK,
                    status=status,
                    destination=safe_url,
                    response=f"HTTP {resp.status_code}",
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("alert_webhook_failed host=%s err=%s", urlparse_host(ep.url), exc)
            deliveries.append(
                _record(
                    db,
                    org_id=org_id,
                    alert_id=alert.id,
                    channel=AlertChannel.WEBHOOK,
                    status=DeliveryStatus.FAILED,
                    destination=urlparse_host(ep.url),
                    response=type(exc).__name__,
                )
            )

    # Slack / Teams adapters: destinations live in org.settings until dedicated models exist.
    org = db.get(Organization, org_id)
    settings_dict = (org.settings if org else {}) or {}
    slack_url = settings_dict.get("slack_webhook_url")
    if slack_url:
        try:
            safe_url = assert_safe_outbound_url(
                str(slack_url), field="slack_webhook_url", require_known_chat_host=True
            )
            resp = _post_json(
                safe_url,
                {"text": f"*ATLASOPS*\n{alert.title}\n{alert.message}"},
            )
            status = DeliveryStatus.SENT if resp.status_code < 300 else DeliveryStatus.FAILED
            resp_text = f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            status = DeliveryStatus.FAILED
            resp_text = type(exc).__name__
            safe_url = urlparse_host(str(slack_url))
        deliveries.append(
            _record(
                db,
                org_id=org_id,
                alert_id=alert.id,
                channel=AlertChannel.SLACK,
                status=status,
                destination=str(safe_url)[:200],
                response=resp_text,
            )
        )

    teams_url = settings_dict.get("teams_webhook_url")
    if teams_url:
        try:
            safe_url = assert_safe_outbound_url(
                str(teams_url), field="teams_webhook_url", require_known_chat_host=True
            )
            resp = _post_json(
                safe_url,
                {
                    "@type": "MessageCard",
                    "summary": alert.title,
                    "themeColor": "0076D7",
                    "title": alert.title,
                    "text": alert.message,
                },
            )
            status = DeliveryStatus.SENT if resp.status_code < 300 else DeliveryStatus.FAILED
            resp_text = f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            status = DeliveryStatus.FAILED
            resp_text = type(exc).__name__
            safe_url = urlparse_host(str(teams_url))
        deliveries.append(
            _record(
                db,
                org_id=org_id,
                alert_id=alert.id,
                channel=AlertChannel.TEAMS,
                status=status,
                destination=str(safe_url)[:200],
                response=resp_text,
            )
        )

    db.flush()
    return deliveries


def dispatch_new_alerts(db: Session, alerts: list[Alert]) -> int:
    count = 0
    for alert in alerts:
        dispatch_alert(db, alert)
        count += 1
    return count


def notify_org_channels(
    db: Session,
    org_id: UUID,
    *,
    subject: str,
    body: str,
    channels: list[str] | None = None,
) -> dict[str, Any]:
    """Send a free-form notification across configured org channels (workflow actions)."""
    wanted = {c.lower() for c in (channels or ["email", "slack", "teams", "webhook"])}
    results: dict[str, Any] = {}
    org = db.get(Organization, org_id)
    settings_dict = (org.settings if org else {}) or {}

    if "email" in wanted:
        recipients = _org_alert_emails(db, org_id)
        if recipients:
            results["email"] = email_client.send_email(
                to=recipients,
                subject=f"[ATLASOPS] {subject}",
                html=(
                    f"<p><strong>{escape_html(subject)}</strong></p>"
                    f"<p>{escape_html(body)}</p>"
                ),
                text=f"{subject}\n\n{body}",
            )
        else:
            results["email"] = {"ok": False, "skipped": True, "reason": "no_recipients"}

    if "slack" in wanted and settings_dict.get("slack_webhook_url"):
        try:
            safe_url = assert_safe_outbound_url(
                str(settings_dict["slack_webhook_url"]),
                field="slack_webhook_url",
                require_known_chat_host=True,
            )
            resp = _post_json(safe_url, {"text": f"*{subject}*\n{body}"})
            results["slack"] = {"ok": resp.status_code < 300, "status": resp.status_code}
        except Exception as exc:  # noqa: BLE001
            results["slack"] = {"ok": False, "error": type(exc).__name__}

    if "teams" in wanted and settings_dict.get("teams_webhook_url"):
        try:
            safe_url = assert_safe_outbound_url(
                str(settings_dict["teams_webhook_url"]),
                field="teams_webhook_url",
                require_known_chat_host=True,
            )
            resp = _post_json(
                safe_url,
                {"@type": "MessageCard", "summary": subject, "title": subject, "text": body},
            )
            results["teams"] = {"ok": resp.status_code < 300, "status": resp.status_code}
        except Exception as exc:  # noqa: BLE001
            results["teams"] = {"ok": False, "error": type(exc).__name__}

    if "webhook" in wanted:
        endpoints = db.scalars(
            select(WebhookEndpoint).where(
                WebhookEndpoint.organization_id == org_id,
                WebhookEndpoint.is_active.is_(True),
            )
        ).all()
        wh_results = []
        for ep in endpoints:
            try:
                safe_url = assert_safe_outbound_url(ep.url, field="webhook.url")
                resp = _post_json(
                    safe_url,
                    {"type": "workflow.notify", "subject": subject, "body": body},
                    secret_encrypted=ep.secret_encrypted,
                )
                wh_results.append({"host": urlparse_host(safe_url), "ok": resp.status_code < 300})
            except Exception as exc:  # noqa: BLE001
                wh_results.append(
                    {"host": urlparse_host(ep.url), "ok": False, "error": type(exc).__name__}
                )
        results["webhook"] = wh_results

    return results
