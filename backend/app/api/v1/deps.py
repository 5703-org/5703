"""Shared dependencies (Spec A05, C05, C06).

The current user ALWAYS comes from the verified token - never from a
user_id in the request body.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.feature_flags import FeatureFlags, build_flags
from app.core.security import decode_token
from app.db.session import get_db
from app.modules.identity import repository
from app.modules.identity.models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        raise AppError("UNAUTHORIZED", detail="Missing bearer token.")
    payload = decode_token(credentials.credentials, settings)
    user = repository.get_user(db, payload.get("sub", ""))
    if user is None or payload.get("ver") != user.token_version:
        raise AppError("TOKEN_INVALID")
    if user.status != "active":
        raise AppError("FORBIDDEN", detail="Account is deactivated.")
    return user


def require_roles(*roles: str) -> Callable:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role.name not in roles:
            raise AppError("FORBIDDEN", detail=f"Requires role: {', '.join(roles)}.")
        return user

    return checker


def get_flags(settings: Settings = Depends(get_settings)) -> FeatureFlags:
    return build_flags(settings)
