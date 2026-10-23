"""Native authentication/logout with isolated durable SQLite and synthetic tokens."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from threading import Barrier

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import create_engine, event, func, inspect, select
from sqlalchemy.orm import sessionmaker

import app.db.models  # noqa: F401
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, register_exception_handlers
from app.core.security import hash_password
from app.db.session import get_db
from app.modules.identity import router, sessions
from app.modules.identity.models import LoginRateLimit, RevokedSession, Role, User, Workspace


def application(factory, settings):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router.router, prefix="/api/v1")

    def database():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
def auth(tmp_path):
    engine = create_engine("sqlite:///" + (tmp_path / "synthetic-auth.sqlite").as_posix())

    @event.listens_for(engine, "connect")
    def enforce_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    for model in (Workspace, Role, User, LoginRateLimit, RevokedSession):
        model.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        db.add(Workspace(id="workspace", name="Synthetic", slug="synthetic"))
        db.add(Role(id=1, name="student"))
        db.flush()
        db.add(
            User(
                id="owner",
                email="owner@example.com",
                hashed_password=hash_password("Passw0rd!"),
                role_id=1,
                workspace_id="workspace",
            )
        )
        db.commit()
    settings = Settings(
        _env_file=None,
        env="test",
        database_url=str(engine.url),
        model_mode="mock",
        llm_provider="mock",
        llm_api_key=None,
        jwt_secret="synthetic-session-secret-at-least-thirty-two-characters",
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
    )
    with TestClient(application(factory, settings), raise_server_exceptions=False) as client:
        yield client, factory, settings
    engine.dispose()


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "owner@example.com",
            "password": "Passw0rd!",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def headers(token):
    return {"Authorization": "Bearer " + token}


def signed(settings, **changes):
    now = datetime.now(timezone.utc)
    payload = {"sub": "owner", "iat": now, "exp": now + timedelta(minutes=20), "ver": 1}
    payload.update(changes)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_native_login_logout_replay_idempotence_and_other_device_survives(auth):
    client, factory, settings = auth
    first, second = login(client), login(client)
    first_payload = jwt.decode(first, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    second_payload = jwt.decode(second, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    distinct = first != second and first_payload["jti"] != second_payload["jti"]
    assert distinct
    assert client.get("/api/v1/users/me", headers=headers(first)).status_code == 200
    for _ in range(2):
        logged_out = client.post("/api/v1/auth/logout", headers=headers(first))
        assert logged_out.status_code == 200
        assert logged_out.json()["data"] == {"logged_out": True, "session_revoked": True}
    assert client.get("/api/v1/users/me", headers=headers(first)).status_code == 401
    assert client.get("/api/v1/users/me", headers=headers(second)).status_code == 200
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(RevokedSession)) == 1
        row = db.scalar(select(RevokedSession))
        assert len(row.identity_hash) == 64
        assert row.user_id == "owner"
        user = db.get(User, "owner")
        assert (user.version, user.token_version) == (1, 1)
    # A separately created API instance consults the same durable revocation.
    with TestClient(application(factory, settings)) as restarted:
        assert restarted.get("/api/v1/users/me", headers=headers(first)).status_code == 401
        assert restarted.get("/api/v1/users/me", headers=headers(second)).status_code == 200


def test_same_clock_token_issuance_still_has_distinct_session_identity(auth, monkeypatch):
    from app.core import security

    _, _, settings = auth
    fixed = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)

    class FrozenDateTime:
        @classmethod
        def now(cls, tz):
            return fixed

    monkeypatch.setattr(security, "datetime", FrozenDateTime)
    first, second = (
        security.create_access_token("owner", settings),
        security.create_access_token("owner", settings),
    )
    # Decode without checking this intentionally frozen development timestamp.
    a = jwt.decode(
        first,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"verify_exp": False},
    )
    b = jwt.decode(
        second,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"verify_exp": False},
    )
    distinct = first != second and a["jti"] != b["jti"]
    assert distinct
    assert a["iat"] == b["iat"] and a["exp"] == b["exp"]


def test_legacy_no_jti_token_is_preserved_until_its_exact_logout(auth):
    client, factory, settings = auth
    legacy = signed(settings)
    newer = login(client)
    assert client.get("/api/v1/users/me", headers=headers(legacy)).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers(legacy)).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers(legacy)).status_code == 200
    assert client.get("/api/v1/users/me", headers=headers(legacy)).status_code == 401
    assert client.get("/api/v1/users/me", headers=headers(newer)).status_code == 200
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(RevokedSession)) == 1
        assert db.get(User, "owner").token_version == 1


@pytest.mark.parametrize(
    "case", ["expired", "malformed", "missing_expiry", "wrong_account_version", "missing_user"]
)
def test_invalid_tokens_do_not_create_revocations(auth, case):
    client, factory, settings = auth
    if case == "expired":
        token = signed(settings, exp=datetime.now(timezone.utc) - timedelta(seconds=1))
    elif case == "malformed":
        token = "synthetic-not-a-jwt"
    elif case == "missing_expiry":
        token = jwt.encode(
            {"sub": "owner", "ver": 1}, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
    elif case == "wrong_account_version":
        token = signed(settings, ver=99)
    else:
        token = signed(settings, sub="missing")
    assert client.post("/api/v1/auth/logout", headers=headers(token)).status_code == 401
    assert client.get("/api/v1/users/me", headers=headers(token)).status_code == 401
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(RevokedSession)) == 0


def test_missing_bearer_and_deactivated_account_cannot_revoke(auth):
    client, factory, _ = auth
    token = login(client)
    assert client.post("/api/v1/auth/logout").status_code == 401
    with factory() as db:
        db.get(User, "owner").status = "deactivated"
        db.commit()
    assert client.post("/api/v1/auth/logout", headers=headers(token)).status_code == 403
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(RevokedSession)) == 0


def test_signature_and_account_checks_precede_revocation_identity_lookup(auth):
    _, factory, settings = auth
    token = signed(settings, ver=999)
    with factory() as db:
        # A table error would otherwise occur if the invalid token reached the
        # revocation lookup. Authentication must reject the account version first.
        RevokedSession.__table__.drop(db.bind)
        with pytest.raises(AppError) as failure:
            sessions.authenticate(db, token, settings)
        assert failure.value.code == "TOKEN_INVALID"


def test_concurrent_duplicate_logout_commits_one_revocation_without_global_change(auth):
    client, factory, settings = auth
    token = login(client)
    ready = Barrier(2)

    def logout_once():
        with factory() as db:
            current = sessions.authenticate(db, token, settings, allow_revoked=True)
            ready.wait(timeout=5)
            sessions.revoke(db, current)
            return True

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(logout_once) for _ in range(2)]
        assert all(future.result(timeout=10) for future in futures)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(RevokedSession)) == 1
        assert (db.get(User, "owner").version, db.get(User, "owner").token_version) == (1, 1)
    assert client.get("/api/v1/users/me", headers=headers(token)).status_code == 401


def test_failed_revocation_commit_rolls_back_the_native_insert_and_never_reports_success(auth):
    client, factory, _ = auth
    token = login(client)

    def unavailable(db):
        raise RuntimeError("Synthetic durable commit failure")

    event.listen(factory, "before_commit", unavailable)
    try:
        response = client.post("/api/v1/auth/logout", headers=headers(token))
    finally:
        event.remove(factory, "before_commit", unavailable)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert client.get("/api/v1/users/me", headers=headers(token)).status_code == 200
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(RevokedSession)) == 0


def test_additive_migration_preserves_existing_account_and_creates_expiry_index(tmp_path):
    engine = create_engine("sqlite:///" + (tmp_path / "migration.sqlite").as_posix())
    for model in (Workspace, Role, User):
        model.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(
            Workspace.__table__.insert().values(id="w", name="Original", slug="original", version=1)
        )
        connection.execute(Role.__table__.insert().values(id=1, name="student"))
        connection.execute(
            User.__table__.insert().values(
                id="owner",
                email="owner@example.com",
                hashed_password="original-synthetic-hash",
                role_id=1,
                workspace_id="w",
                version=7,
                token_version=3,
            )
        )
        migration_path = (
            Path(__file__).parents[2]
            / "backend/alembic/versions/fa1b6d3298ef_current_session_logout.py"
        )
        spec = importlib.util.spec_from_file_location("logout_migration209", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        row = connection.execute(select(User.__table__).where(User.id == "owner")).mappings().one()
        assert (row["version"], row["token_version"], row["hashed_password"]) == (
            7,
            3,
            "original-synthetic-hash",
        )
        indices = {
            item["name"] for item in inspect(connection).get_indexes("auth_revoked_sessions")
        }
        assert "ix_auth_revoked_sessions_expires_at" in indices
        assert "ix_auth_revoked_sessions_user_id" in indices
        assert connection.scalar(select(func.count()).select_from(RevokedSession)) == 0
    engine.dispose()
