"""Login throttles persist and do not reveal attempted identities."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.identity.login_limits import check_allowed, record_failure, record_success
from app.modules.identity.models import LoginRateLimit
from app.modules.identity import repository, service
from app.core.security import hash_password
from types import SimpleNamespace


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    LoginRateLimit.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        jwt_secret="fixed-test-secret-012345678901234567890123",
        login_rate_max_failures=2,
        login_rate_window_seconds=60,
        login_rate_block_seconds=90,
    )


def test_pair_lockout_shared_in_database_and_expiring(db, settings):
    t0 = datetime(2026, 9, 30, tzinfo=timezone.utc)
    for _ in range(2):
        check_allowed(db, "Learner@example.org", "127.0.0.1", settings, now=t0)
        record_failure(db, "learner@example.org", "127.0.0.1", settings, now=t0)
        db.commit()
    with pytest.raises(AppError, match="LOGIN_RATE_LIMITED"):
        check_allowed(db, "LEARNER@example.org", "127.0.0.1", settings, now=t0)
    assert check_allowed(db, "other@example.org", "127.0.0.1", settings, now=t0) is None
    rows = list(db.scalars(select(LoginRateLimit)))
    assert len(rows) == 2
    assert all("learner" not in row.key_hash and "127.0.0.1" not in row.key_hash for row in rows)
    assert (
        check_allowed(
            db, "learner@example.org", "127.0.0.1", settings, now=t0 + timedelta(seconds=91)
        )
        is None
    )
    record_failure(db, "learner@example.org", "127.0.0.1", settings, now=t0 + timedelta(seconds=91))
    db.commit()
    assert (
        check_allowed(
            db, "learner@example.org", "127.0.0.1", settings, now=t0 + timedelta(seconds=91)
        )
        is None
    )


def test_success_resets_pair_without_clearing_other_host_attempts(db, settings):
    current = datetime(2026, 9, 30, tzinfo=timezone.utc)
    record_failure(db, "learner@example.org", "client", settings, now=current)
    db.commit()
    record_success(db, "learner@example.org", "client", settings)
    db.commit()
    assert len(list(db.scalars(select(LoginRateLimit)))) == 1
    assert check_allowed(db, "learner@example.org", "client", settings, now=current) is None


def test_unknown_wrong_password_and_deactivated_user_share_bad_credentials(monkeypatch):
    active = SimpleNamespace(hashed_password=hash_password("known-secret"), status="active")
    disabled = SimpleNamespace(hashed_password=hash_password("known-secret"), status="deactivated")
    for candidate, supplied in ((None, "anything"), (active, "wrong"), (disabled, "known-secret")):
        monkeypatch.setattr(repository, "get_user_by_email", lambda _db, _email: candidate)
        with pytest.raises(AppError) as error:
            service.authenticate(object(), "someone@example.org", supplied)
        assert error.value.code == "BAD_CREDENTIALS"
