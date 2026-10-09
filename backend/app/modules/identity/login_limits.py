"""Database-backed login throttling shared by every API process."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, bindparam, delete, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.identity.models import LoginRateLimit


def _keys(email: str, remote_host: str, secret: str) -> tuple[str, str]:
    account = email.strip().casefold()
    host = remote_host.strip().casefold()[:128] or "unknown"

    def keyed(value: str) -> str:
        return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()

    return keyed(f"login-pair:{host}:{account}"), keyed(f"login-ip:{host}")


def _utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def check_allowed(
    db: Session, email: str, remote_host: str, settings: Settings, *, now: datetime | None = None
) -> None:
    current = now or datetime.now(timezone.utc)
    pair, host = _keys(email, remote_host, settings.jwt_secret)
    limits = db.scalars(select(LoginRateLimit).where(LoginRateLimit.key_hash.in_((pair, host))))
    if any(item.blocked_until and _utc(item.blocked_until) > current for item in limits):
        raise AppError("LOGIN_RATE_LIMITED")


_FAILURE_UPSERT = text(
    """
    INSERT INTO auth_login_limits (key_hash, window_start, failure_count, blocked_until)
    VALUES (:key_hash, :now, 1, CASE WHEN :limit <= 1 THEN :until ELSE NULL END)
    ON CONFLICT (key_hash) DO UPDATE SET
        window_start = CASE
            WHEN auth_login_limits.window_start < :cutoff THEN :now
            ELSE auth_login_limits.window_start END,
        failure_count = CASE
            WHEN auth_login_limits.window_start < :cutoff THEN 1
            ELSE auth_login_limits.failure_count + 1 END,
        blocked_until = CASE
            WHEN auth_login_limits.blocked_until > :now THEN auth_login_limits.blocked_until
            WHEN auth_login_limits.window_start < :cutoff THEN NULL
            WHEN auth_login_limits.failure_count + 1 >= :limit THEN :until
            ELSE NULL END
    """
).bindparams(
    bindparam("now", type_=DateTime(timezone=True)),
    bindparam("cutoff", type_=DateTime(timezone=True)),
    bindparam("until", type_=DateTime(timezone=True)),
)


def record_failure(
    db: Session, email: str, remote_host: str, settings: Settings, *, now: datetime | None = None
) -> None:
    current = now or datetime.now(timezone.utc)
    pair, host = _keys(email, remote_host, settings.jwt_secret)
    cutoff = current - timedelta(seconds=settings.login_rate_window_seconds)
    blocked_until = current + timedelta(seconds=settings.login_rate_block_seconds)
    for key_hash, limit in ((pair, settings.login_rate_max_failures), (host, 30)):
        db.execute(
            _FAILURE_UPSERT,
            {
                "key_hash": key_hash,
                "now": current,
                "cutoff": cutoff,
                "until": blocked_until,
                "limit": limit,
            },
        )
    # A bounded rolling cleanup prevents indefinitely retaining attempted pairs.
    if int(pair[:2], 16) == 0:
        db.execute(
            delete(LoginRateLimit).where(
                LoginRateLimit.window_start
                < current - timedelta(days=2, seconds=settings.login_rate_block_seconds),
                (LoginRateLimit.blocked_until.is_(None)) | (LoginRateLimit.blocked_until < current),
            )
        )


def record_success(db: Session, email: str, remote_host: str, settings: Settings) -> None:
    pair, _ = _keys(email, remote_host, settings.jwt_secret)
    db.execute(delete(LoginRateLimit).where(LoginRateLimit.key_hash == pair))
