"""Password hashing and JWT helpers (Spec C03, C04).

pbkdf2_sha256 is pure-python so the skeleton runs anywhere; swap to bcrypt
or argon2 in production without changing call sites.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import Settings
from app.core.exceptions import AppError

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    subject: str, settings: Settings, expires_minutes: int | None = None, token_version: int = 1
) -> str:
    minutes = expires_minutes or settings.access_token_expire_minutes
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        "ver": token_version,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, settings: Settings) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise AppError("TOKEN_INVALID", internal=f"jwt decode failed: {exc}") from exc
