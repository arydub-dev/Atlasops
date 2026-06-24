"""Shared FastAPI dependencies: authentication and role-based access control."""
from __future__ import annotations

from collections.abc import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models import User
from app.models.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=True
)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise _CREDENTIALS_ERROR
    user_id = payload.get("sub")
    if user_id is None:
        raise _CREDENTIALS_ERROR
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user


def require_roles(*roles: UserRole):
    """Dependency factory enforcing that the current user holds one of `roles`."""
    allowed: Iterable[UserRole] = roles

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role == UserRole.ADMIN:
            return user  # admins bypass granular checks
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation",
            )
        return user

    return _checker
