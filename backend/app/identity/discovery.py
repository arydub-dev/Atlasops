"""Organization / IdP discovery from work email domain."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.identity import workos as workos_client
from app.identity.workos import WorkOSNotConfigured
from app.models import Invitation, Organization
from app.models.enums import InvitationStatus, OrgStatus

logger = logging.getLogger("supply.discovery")

_EMAIL_RE = re.compile(r"^[^@\s]+@([^@\s]+\.[^@\s]+)$")


@dataclass(slots=True)
class DiscoveryResult:
    email: str
    domain: str
    workos_organization_id: str | None
    local_organization_id: str | None
    mode: str  # sso | authkit
    invite_token: str | None = None


def extract_email_domain(email: str) -> tuple[str, str]:
    cleaned = email.lower().strip()
    match = _EMAIL_RE.match(cleaned)
    if not match:
        raise ValueError("Enter a valid work email address")
    return cleaned, match.group(1)


def find_local_org_for_domain(db: DBSession, domain: str) -> Organization | None:
    rows = db.scalars(
        select(Organization).where(
            Organization.deleted_at.is_(None),
            Organization.status != OrgStatus.DELETED,
        )
    ).all()
    for org in rows:
        settings = org.settings or {}
        allowed = settings.get("allowed_email_domains") or settings.get("allowed_domains") or []
        if isinstance(allowed, str):
            allowed = [allowed]
        normalized = {str(d).lower().strip() for d in allowed if d}
        if domain in normalized:
            return org
        # Also match slug-style corporate domains stored as branding
        branding = org.branding or {}
        brand_domain = str(branding.get("email_domain") or "").lower().strip()
        if brand_domain and brand_domain == domain:
            return org
    # Prefer org already linked to WorkOS with matching stored domain hint
    for org in rows:
        if org.workos_organization_id:
            settings = org.settings or {}
            if str(settings.get("primary_email_domain") or "").lower() == domain:
                return org
    return None


def _pending_invite_token(db: DBSession, email: str) -> str | None:
    inv = db.scalar(
        select(Invitation)
        .where(
            Invitation.email == email,
            Invitation.status == InvitationStatus.PENDING,
        )
        .order_by(Invitation.created_at.desc())
    )
    if inv is None:
        return None
    expires = inv.expires_at
    from datetime import datetime, timezone

    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        return None
    return inv.token


def discover_organization(
    db: DBSession,
    *,
    email: str,
    invite_token: str | None = None,
) -> DiscoveryResult:
    cleaned, domain = extract_email_domain(email)
    local = find_local_org_for_domain(db, domain)
    workos_org_id = local.workos_organization_id if local else None

    if workos_org_id is None:
        try:
            found = workos_client.find_organization_id_by_domain(domain)
            if found:
                workos_org_id = found
                if local and not local.workos_organization_id:
                    local.workos_organization_id = found
                    settings = dict(local.settings or {})
                    settings["primary_email_domain"] = domain
                    local.settings = settings
                    db.flush()
        except WorkOSNotConfigured:
            pass
        except Exception:
            logger.exception("WorkOS domain discovery failed for %s", domain)

    # Only honor an explicitly supplied invite token. Auto-attaching any pending
    # invite for the email enables silent org-join / privilege escalation on login.
    token = (invite_token or "").strip() or None
    if token:
        # Validate the token still exists for this email (do not leak other invites).
        pending = _pending_invite_token(db, cleaned)
        if pending != token:
            token = None
    mode = "sso" if workos_org_id else "authkit"
    return DiscoveryResult(
        email=cleaned,
        domain=domain,
        workos_organization_id=workos_org_id,
        local_organization_id=str(local.id) if local else None,
        mode=mode,
        invite_token=token,
    )
