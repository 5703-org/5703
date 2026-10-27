"""Formal startup contracts. Synthetic in-memory rows are not deployed accounts."""

from pathlib import Path
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.identity import bootstrap
from app.modules.identity.models import Workspace, Role, User, StudentProfile
from app.modules.model_settings import secrets
from app.platform_core import registry as providers
from scripts.release.formal_preflight import validate


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    for table in [Workspace.__table__, Role.__table__, User.__table__, StudentProfile.__table__]:
        table.create(engine)
    monkeypatch.setattr(bootstrap, "hash_password", lambda value: "NOT_AUTHENTICATABLE_TEST_ROW")
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_explicit_owner_creates_one_account_no_demonstration_records(db):
    owner = bootstrap.initialize_owner(
        db,
        email="owner@university.example",
        full_name="Synthetic owner",
        password="synthetic-input-only",
    )
    db.commit()
    assert db.scalar(select(func.count()).select_from(User)) == 1
    assert db.scalar(select(func.count()).select_from(StudentProfile)) == 1
    assert db.get(User, owner).role.name == "admin"
    assert db.get(User, owner).hashed_password == "NOT_AUTHENTICATABLE_TEST_ROW"
    assert set(db.scalars(select(Role.name))) == {"admin", "student"}


def test_owner_setup_does_not_commit_partial_transaction(db):
    bootstrap.initialize_owner(
        db,
        email="owner@university.example",
        full_name="Synthetic owner",
        password="synthetic-input-only",
    )
    db.rollback()
    assert db.scalar(select(func.count()).select_from(User)) == 0
    assert db.scalar(select(func.count()).select_from(Workspace)) == 0
    assert db.scalar(select(func.count()).select_from(Role)) == 0


@pytest.mark.parametrize("email", ["owner@university.example", "different@university.example"])
def test_existing_accounts_never_reset_or_duplicate(db, email):
    owner = bootstrap.initialize_owner(
        db,
        email="owner@university.example",
        full_name="Synthetic owner",
        password="synthetic-input-only",
    )
    db.commit()
    before = (
        db.get(User, owner).hashed_password,
        db.get(User, owner).version,
        db.get(User, owner).token_version,
    )
    with pytest.raises(AppError, match="Accounts already exist"):
        bootstrap.initialize_owner(
            db, email=email, full_name="New name", password="new-synthetic-input"
        )
    db.rollback()
    assert before == (
        db.get(User, owner).hashed_password,
        db.get(User, owner).version,
        db.get(User, owner).token_version,
    )
    assert db.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize(
    "changes",
    [{"email": "invalid"}, {"full_name": " "}, {"password": "short"}, {"password": "x" * 129}],
)
def test_bad_bootstrap_input_does_not_create_rows_or_echo_password(db, changes):
    values = {
        "email": "owner@university.example",
        "full_name": "Synthetic owner",
        "password": "synthetic-input-only",
    }
    values.update(changes)
    with pytest.raises(AppError) as error:
        bootstrap.initialize_owner(db, **values)
    assert values["password"] not in str(error.value)
    assert db.scalar(select(func.count()).select_from(User)) == 0
    assert db.scalar(select(func.count()).select_from(Workspace)) == 0


def test_inactive_workspace_is_not_reenabled(db):
    db.add(Workspace(name="Synthetic", slug="default", status="inactive"))
    db.commit()
    with pytest.raises(AppError, match="workspace is not active"):
        bootstrap.initialize_owner(
            db,
            email="owner@university.example",
            full_name="Synthetic owner",
            password="synthetic-input-only",
        )
    assert db.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize("env", ["dev", "test", "demo", "production"])
def test_encryption_readiness_never_creates_a_missing_key(tmp_path, env, monkeypatch):
    path = tmp_path / "absent" / "key"
    settings = SimpleNamespace(
        model_config_encryption_key=None, model_config_key_file=str(path), env=env
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Readiness must not modify permissions")

    monkeypatch.setattr(secrets, "_restrict_windows", forbidden)
    assert secrets.encryption_ready(settings) is False
    assert not path.parent.exists()


def test_registry_names_real_implementations_without_inventing_health(monkeypatch):
    isolated = providers.ProviderRegistry()
    monkeypatch.setattr(providers, "registry", isolated)
    providers.register_builtin_providers()
    providers.register_builtin_providers()
    rows = isolated.list()
    assert len(rows) == 3
    assert {r["capability_type"] for r in rows} == {"parser", "retriever", "generator"}
    assert not any("mock" in r["provider_id"] for r in rows)
    assert all(r["healthy"] is False and r["health_status"] == "not_probed" for r in rows)


@pytest.mark.parametrize(
    "model,base", [("", None), ("named-model", None), ("", "https://invalid.example/v1")]
)
def test_live_configuration_missing_model_or_endpoint_is_unavailable_before_dispatch(model, base):
    from app.modules.answering.service import model_config

    settings = Settings(
        _env_file=None,
        env="test",
        model_mode="live",
        llm_provider="openai_compatible",
        llm_model=model,
        llm_api_base=base,
    )
    with pytest.raises(AppError) as error:
        model_config(settings)
    assert error.value.code == "MODEL_UNAVAILABLE"


def test_formal_launcher_contains_no_implicit_provisioning_or_demo_mode():
    source = (Path(__file__).resolve().parents[2] / "scripts/release/start_local.ps1").read_text(
        encoding="utf-8"
    )
    for forbidden in [
        "MODEL_MODE=mock",
        "LLM_PROVIDER=mock",
        "[guid]::NewGuid",
        "SetAccessControl",
        "icacls",
        "Get-PortableInitialPassword",
        "seed-demo",
    ]:
        assert forbidden not in source
    assert "scripts.release.formal_preflight" in source and "--owner-id" in source


@pytest.mark.parametrize("env", ["dev", "test", "demo"])
def test_formal_preflight_rejects_development_profile(env):
    with pytest.raises(ValueError, match="non-development"):
        validate(Settings(_env_file=None, env=env))
