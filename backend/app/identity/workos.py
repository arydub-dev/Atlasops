"""WorkOS AuthKit / SSO integration."""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger("supply.workos")


class WorkOSNotConfigured(RuntimeError):
    pass


def _client():
    if not settings.workos_configured:
        raise WorkOSNotConfigured(
            "WorkOS is not configured. Set WORKOS_API_KEY and WORKOS_CLIENT_ID."
        )
    from workos import WorkOSClient

    return WorkOSClient(api_key=settings.WORKOS_API_KEY, client_id=settings.WORKOS_CLIENT_ID)


def get_authorization_url(
    *,
    provider: str | None = None,
    organization_id: str | None = None,
    login_hint: str | None = None,
    domain_hint: str | None = None,
    state: str | None = None,
    code_challenge: str | None = None,
) -> str:
    """Build AuthKit or enterprise SSO authorization URL.

    Prefer organization_id for SSO routing. Provider buttons are not used by the
    email-first flow; AuthKit still brokers Google Workspace / passwords when no
    enterprise connection exists.
    """
    client = _client()
    kwargs: dict[str, Any] = {
        "redirect_uri": settings.WORKOS_REDIRECT_URI,
    }
    if state:
        kwargs["state"] = state
    if login_hint:
        kwargs["login_hint"] = login_hint
    if domain_hint:
        kwargs["domain_hint"] = domain_hint
    if code_challenge:
        kwargs["code_challenge"] = code_challenge
        kwargs["code_challenge_method"] = "S256"
    if organization_id:
        # Enterprise SSO — WorkOS selects the IdP for this organization.
        kwargs["organization_id"] = organization_id
        # AuthKit + organization_id auto-selects the org during sign-in.
        kwargs["provider"] = "authkit"
    elif provider and provider.lower() != "authkit":
        kwargs["provider"] = provider
    else:
        kwargs["provider"] = "authkit"

    return client.user_management.get_authorization_url(**kwargs)


def authenticate_with_code(code: str, *, code_verifier: str | None = None) -> dict[str, Any]:
    """Exchange auth code for WorkOS user profile (optionally with PKCE)."""
    client = _client()
    kwargs: dict[str, Any] = {
        "code": code,
    }
    if code_verifier:
        kwargs["code_verifier"] = code_verifier
    result = client.user_management.authenticate_with_code(**kwargs)
    user = result.user
    return {
        "workos_user_id": user.id,
        "email": user.email,
        "first_name": getattr(user, "first_name", None) or "",
        "last_name": getattr(user, "last_name", None) or "",
        "email_verified": bool(getattr(user, "email_verified", False)),
        "profile_picture_url": getattr(user, "profile_picture_url", None),
        "organization_id": getattr(result, "organization_id", None),
        "access_token": getattr(result, "access_token", None),
    }


def find_organization_id_by_domain(domain: str) -> str | None:
    """Look up a WorkOS organization by verified/associated email domain."""
    client = _client()
    result = client.organizations.list_organizations(domains=[domain], limit=10)
    data = getattr(result, "data", None) or []
    if not data:
        return None
    return getattr(data[0], "id", None)


def create_organization(name: str, domains: list[str] | None = None) -> str:
    client = _client()
    org = client.organizations.create_organization(
        name=name,
        domain_data=[{"domain": d, "state": "pending"} for d in (domains or [])]
        if domains
        else None,
    )
    return org.id


def send_magic_auth(email: str) -> str:
    client = _client()
    magic = client.user_management.create_magic_auth(email=email)
    return magic.id


def authenticate_magic_auth(*, email: str, code: str) -> dict[str, Any]:
    client = _client()
    result = client.user_management.authenticate_with_magic_auth(
        email=email,
        code=code,
    )
    user = result.user
    return {
        "workos_user_id": user.id,
        "email": user.email,
        "first_name": getattr(user, "first_name", None) or "",
        "last_name": getattr(user, "last_name", None) or "",
        "email_verified": True,
        "profile_picture_url": getattr(user, "profile_picture_url", None),
    }


def list_directory_users(organization_id: str) -> list[dict[str, Any]]:
    """SCIM / Directory Sync users for an org (Enterprise)."""
    client = _client()
    users = client.directory_sync.list_users(organization_id=organization_id)
    return [{"id": u.id, "email": getattr(u, "email", None)} for u in users.data]
