"""Short-lived OAuth login state (PKCE verifier + CSRF state)."""
from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import OAuthLoginState

_STATE_TTL_MINUTES = 15


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_pkce_pair() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) using S256."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def create_login_state(
    db: DBSession,
    *,
    email: str,
    domain: str,
    workos_organization_id: str | None = None,
    invite_token: str | None = None,
    remember_device: bool = False,
    return_path: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[OAuthLoginState, str, str]:
    """Create state row. Returns (row, state, code_challenge)."""
    state = secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce_pair()
    row = OAuthLoginState(
        id=uuid4(),
        state=state,
        code_verifier=verifier,
        email=email.lower().strip(),
        domain=domain.lower().strip(),
        workos_organization_id=workos_organization_id,
        invite_token=invite_token,
        remember_device=remember_device,
        return_path=return_path,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=_utcnow() + timedelta(minutes=_STATE_TTL_MINUTES),
    )
    db.add(row)
    db.flush()
    return row, state, challenge


def consume_login_state(db: DBSession, state: str | None) -> OAuthLoginState | None:
    if not state:
        return None
    row = db.scalar(select(OAuthLoginState).where(OAuthLoginState.state == state))
    if row is None or row.consumed_at is not None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= _utcnow():
        return None
    row.consumed_at = _utcnow()
    db.flush()
    return row


def safe_return_path(path: str | None) -> str:
    """Allow only same-origin relative paths (open-redirect prevention)."""
    if not path:
        return "/auth/callback"
    if not path.startswith("/") or path.startswith("//") or "\\" in path:
        return "/auth/callback"
    if any(c in path for c in (":", "@")):
        return "/auth/callback"
    return path[:500]
