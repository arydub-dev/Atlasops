"""Restricted shared demo access; no signup, identity creation, or administrator access."""
import hashlib
from sqlalchemy import select
from app.core.config import settings
from app.models import Membership, Organization, User
from app.models.enums import MembershipStatus, OrgStatus

PREFIX = "private-demo:"


def session_label():
    return PREFIX + hashlib.sha256(settings.DEMO_LOGIN_PASSWORD_HASH.encode()).hexdigest()


def allowed(db, user_id, org_id):
    if not settings.DEMO_LOGIN_PASSWORD_HASH or str(user_id) != settings.DEMO_LOGIN_USER_ID or str(org_id) != settings.DEMO_LOGIN_ORG_ID:
        return False
    user = db.get(User, user_id)
    org = db.get(Organization, org_id)
    memberships = db.scalars(select(Membership).where(Membership.user_id == user_id,
        Membership.status == MembershipStatus.ACTIVE)).all()
    return bool(user and user.is_active and not user.is_platform_admin and not user.workos_user_id
        and org and not org.deleted_at and org.status not in {OrgStatus.DELETED, OrgStatus.SUSPENDED}
        and (org.settings or {}).get("private_demo") is True
        and len(memberships) == 1 and memberships[0].organization_id == org_id
        and memberships[0].role_slug in {"viewer", "demo_operator"} and not memberships[0].custom_permissions
        and org.owner_user_id != user.id)
