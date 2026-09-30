"""Auth, session, and organization schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    avatar_url: str | None = None
    is_active: bool
    is_platform_admin: bool = False
    created_at: datetime


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    user_id: UUID
    role_slug: str
    status: str
    organization_name: str | None = None
    organization_slug: str | None = None


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    status: str
    plan: str
    owner_user_id: UUID | None = None
    trial_ends_at: datetime | None = None
    settings: dict = Field(default_factory=dict)
    branding: dict = Field(default_factory=dict)
    created_at: datetime


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    settings: dict | None = None
    branding: dict | None = None


class MeResponse(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]
    current_organization: OrganizationOut | None = None
    current_membership: MembershipOut | None = None


class SwitchOrgRequest(BaseModel):
    organization_id: UUID


class DevLoginRequest(BaseModel):
    email: EmailStr
    full_name: str = "Dev User"


class LoginRedirectResponse(BaseModel):
    authorization_url: str
    provider: str
    mode: str = "authkit"
    message: str | None = None


class ContinueLoginRequest(BaseModel):
    email: EmailStr
    remember_device: bool = False
    invite_token: str | None = None
    return_path: str | None = None


class ContinueLoginResponse(BaseModel):
    authorization_url: str
    mode: str  # sso | authkit
    domain: str
    message: str


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_label: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    device_trusted: bool = False
    is_current: bool = False
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    organization_id: UUID | None = None
    user_email: str | None = None
    user_id: UUID | None = None


class AuthSettingsOut(BaseModel):
    allowed_email_domains: list[str] = Field(default_factory=list)
    workos_organization_id: str | None = None
    sso_configured: bool = False
    mfa_required: bool = False  # future


class AuthSettingsUpdate(BaseModel):
    allowed_email_domains: list[str] | None = None


class LoginHistoryItem(BaseModel):
    id: UUID
    user_id: UUID | None = None
    user_email: str | None = None
    action: str
    detail: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class InvitationCreate(BaseModel):
    email: EmailStr
    role_slug: str = "viewer"


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role_slug: str
    status: str
    expires_at: datetime
    created_at: datetime


class InvitationCreated(InvitationOut):
    """Returned once on create — includes the raw invite token for the share link."""

    token: str
    invite_url: str


class InvitationPreview(BaseModel):
    email: EmailStr
    organization_name: str
    role_slug: str
    expires_at: datetime
    status: str


class MemberUpdate(BaseModel):
    role_slug: str | None = None
    status: str | None = None  # active | suspended
    suspended_reason: str | None = None


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    email: str
    full_name: str
    role_slug: str
    status: str
    created_at: datetime


class TransferOwnershipRequest(BaseModel):
    new_owner_user_id: UUID


class ApiTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class ApiTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    token_prefix: str
    scopes: list
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class ApiTokenCreated(ApiTokenOut):
    """Returned once on create — includes the raw token."""

    token: str


class WebhookCreate(BaseModel):
    url: str = Field(min_length=8, max_length=1000)
    events: list[str] = Field(default_factory=list)
    secret: str | None = None


class WebhookUpdate(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None
    secret: str | None = None


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    events: list
    is_active: bool
    failure_count: int
    created_at: datetime
