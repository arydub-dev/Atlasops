"""Transactional email via Resend (optional)."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("supply.email")


def resend_configured() -> bool:
    return bool(settings.RESEND_API_KEY and settings.EMAIL_FROM)


def send_email(
    *,
    to: str | list[str],
    subject: str,
    html: str,
    text: str | None = None,
) -> dict[str, Any]:
    """Send email through Resend. No-ops with a logged skip when unset."""
    recipients = [to] if isinstance(to, str) else list(to)
    if not resend_configured():
        logger.info("email_skipped reason=resend_unset to=%s subject=%s", recipients, subject)
        return {"ok": False, "skipped": True, "reason": "resend_unset"}

    payload: dict[str, Any] = {
        "from": settings.EMAIL_FROM,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    with httpx.Client(timeout=20.0) as client:
        resp = client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code >= 400:
            logger.error("resend_failed status=%s body=%s", resp.status_code, resp.text[:500])
            return {"ok": False, "status": resp.status_code, "body": resp.text[:500]}
        data = resp.json() if resp.content else {}
        return {"ok": True, "id": data.get("id"), "skipped": False}
