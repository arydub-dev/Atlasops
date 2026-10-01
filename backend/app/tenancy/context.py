"""Request-scoped tenant / identity context (contextvars)."""
from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import FrozenSet
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Resolved on every authenticated request."""

    organization_id: UUID
    user_id: UUID
    membership_id: UUID
    permissions: FrozenSet[str] = field(default_factory=frozenset)
    role_slug: str = "viewer"
    request_id: str = ""
    is_platform_admin: bool = False


_tenant_ctx: ContextVar[TenantContext | None] = ContextVar("tenant_ctx", default=None)


def get_tenant() -> TenantContext:
    ctx = _tenant_ctx.get()
    if ctx is None:
        raise RuntimeError("Tenant context is not set for this request")
    return ctx


def get_tenant_or_none() -> TenantContext | None:
    return _tenant_ctx.get()


def set_tenant(ctx: TenantContext) -> Token:
    return _tenant_ctx.set(ctx)


def reset_tenant(token: Token) -> None:
    _tenant_ctx.reset(token)


def require_org_id() -> UUID:
    return get_tenant().organization_id
