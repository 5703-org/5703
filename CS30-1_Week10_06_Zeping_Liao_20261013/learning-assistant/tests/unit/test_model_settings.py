"""Configuration lifecycle against SQLite and a real local authored HTTP server.

The local HTTP server verifies actual transport and credential isolation, not
an external provider, paid inference or model answer quality.
"""

from copy import deepcopy
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
from types import SimpleNamespace

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.db.base import Base
from app.main import create_app
from app.modules.identity.models import Role, StudentProfile, User, Workspace, LoginRateLimit
from app.modules.model_settings.models import (
    ActiveModelConfiguration,
    ModelActivation,
    ModelConfiguration,
    ModelConnectionTest,
    ModelCredential,
    ModelCompatibilityRun,
    ModelCompatibilityStage,
)
from app.modules.model_settings.service import PREFIX, resolve_active_model_config, resolve_secret
from app.modules.model_settings.secrets import decrypt, encrypt, encryption_ready

ROOT = "/api/v1/admin/model-configurations"
SECRET = "fixture-private-key-do-not-return"


@pytest.fixture
def model_runtime(tmp_path):
    settings = Settings(
        _env_file=None,
        env="test",
        database_url="sqlite:///" + str(tmp_path / "models.db"),
        model_config_encryption_key=Fernet.generate_key().decode(),
        model_config_key_file=str(tmp_path / "private/key"),
        jwt_secret="unit-test-authentication-key-only-000000",
        llm_api_key="unrelated-env-key",
    )
    app = create_app(settings)
    tables = [
        klass.__table__
        for klass in (
            Workspace,
            Role,
            User,
            StudentProfile,
            LoginRateLimit,
            ModelCredential,
            ModelConfiguration,
            ModelConnectionTest,
            ModelCompatibilityRun,
            ModelCompatibilityStage,
            ActiveModelConfiguration,
            ModelActivation,
        )
    ]
    Base.metadata.create_all(app.state.engine, tables=tables)
    db_factory = sessionmaker(bind=app.state.engine, expire_on_commit=False)
    with db_factory() as db:
        workspace = Workspace(name="A", slug="a")
        other_workspace = Workspace(name="B", slug="b")
        admin = Role(name="admin", description="Admin")
        student = Role(name="student", description="Student")
        db.add_all([workspace, other_workspace, admin, student])
        db.flush()
        for email, role, target in [
            ("admin@example.com", admin, workspace),
            ("student@example.com", student, workspace),
            ("other@example.com", admin, other_workspace),
        ]:
            db.add(
                User(
                    email=email,
                    full_name=email,
                    hashed_password=hash_password("Passw0rd!"),
                    role_id=role.id,
                    workspace_id=target.id,
                )
            )
        db.commit()
    client = TestClient(app)

    def headers(email="admin@example.com"):
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd!"})
        assert response.status_code == 200
        return {"Authorization": "Bearer " + response.json()["data"]["access_token"]}

    yield SimpleNamespace(
        settings=settings,
        db=db_factory,
        client=client,
        headers=headers,
        path=tmp_path / "models.db",
    )
    client.close()
    app.state.engine.dispose()


@pytest.fixture
def probe_server():
    observed = []
    control = {"status": 200, "text": None}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            received = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            observed.append(
                {
                    "path": self.path,
                    "authorization": self.headers.get("Authorization"),
                    "body": received,
                }
            )
            from generation.probes import description
            from generation.types import ModelConfig

            schema_name = received.get("response_format", {}).get("json_schema", {}).get("name")
            tier = (
                "project"
                if schema_name in {"chat_response_teaching_v5", "joint_check_v5"}
                else "structured"
                if schema_name
                else "basic"
            )
            role = "checker" if schema_name == "joint_check_v5" else "answer"
            authored = description(ModelConfig(), tier, role)["mock_value"]
            content = (
                control["text"]
                if control["text"] is not None
                else authored
                if isinstance(authored, str)
                else json.dumps(authored)
            )
            payload = {
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
            }
            if control["status"] != 200:
                payload = {"error": {"message": SECRET}}
            self.send_response(control["status"])
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    yield SimpleNamespace(
        base_url=f"http://127.0.0.1:{server.server_port}/v1", observed=observed, control=control
    )
    server.shutdown()
    server.server_close()
    worker.join(timeout=5)


def body(base_url=None, secret=SECRET):
    value = {
        "name": "Authored transport fixture",
        "preset": "custom",
        "config": {
            "provider": "openai_compatible" if base_url else "mock",
            "model": "authored-fixture",
            "base_url": base_url,
            "timeout_seconds": 2,
        },
        "api_key": secret,
    }
    if secret is None:
        value.pop("api_key")
    return value


def saved(runtime, payload, path=ROOT):
    response = runtime.client.post(path, headers=runtime.headers(), json=payload)
    assert response.status_code == 201, response.text
    assert SECRET not in response.text
    return response.json()["data"]


def probe_result(runtime, row, role="answer", tier="all", key=None):
    response = runtime.client.post(
        f"{ROOT}/{row['id']}/test",
        headers={**runtime.headers(), **({"Idempotency-Key": key} if key else {})},
        json={"role": role, "tier": tier},
    )
    assert response.status_code == 200, response.text
    assert SECRET not in response.text
    return response.json()["data"]


def activate(runtime, row, test, version=0):
    checker = probe_result(runtime, row, role="checker")
    return runtime.client.post(
        f"{ROOT}/{row['id']}/activate",
        headers=runtime.headers(),
        json={
            "test_id": test["id"],
            "checker_test_id": checker["id"],
            "expected_active_version": version,
        },
    )


def test_admin_only_and_workspace_scope(model_runtime):
    runtime = model_runtime
    assert runtime.client.get(ROOT).status_code == 401
    assert (
        runtime.client.get(ROOT, headers=runtime.headers("student@example.com")).status_code == 403
    )
    row = saved(runtime, body(secret=None))
    other = runtime.headers("other@example.com")
    assert runtime.client.get(ROOT, headers=other).json()["data"]["items"] == []
    for suffix in ("", "/test", "/versions"):
        method = runtime.client.get if not suffix else runtime.client.post
        args = {"headers": other}
        if suffix == "/versions":
            args["json"] = body(secret=None)
        assert method(f"{ROOT}/{row['id']}{suffix}", **args).status_code == 404


def test_save_test_activate_actual_http_and_frozen_secret(model_runtime, probe_server):
    runtime = model_runtime
    first = saved(runtime, body(probe_server.base_url))
    assert first["has_api_key"] and first["api_key_masked"] == "********"
    assert first["latest_test"] is None and not first["active"]
    assert probe_server.observed == []
    with runtime.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        assert resolve_active_model_config(db, runtime.settings, actor.workspace_id) is None
        original = db.get(ModelConfiguration, first["id"])
        original_credential = original.credential_id
        ciphertext = db.get(ModelCredential, original_credential).ciphertext
        assert ciphertext != SECRET and SECRET not in ciphertext
    first_test = probe_result(runtime, first)
    assert first_test["status"] == "passed" and first_test["model_mode"] == "live"
    assert first_test["usage"]["total_tokens"] == 36
    assert len(probe_server.observed) == 3
    assert probe_server.observed[0]["authorization"] == "Bearer " + SECRET
    assert activate(runtime, first, first_test).status_code == 200
    assert activate(runtime, first, first_test).status_code == 409
    with runtime.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        frozen = resolve_active_model_config(db, runtime.settings, actor.workspace_id)
        assert frozen.configuration_id == PREFIX + first["id"]
        assert SECRET not in json.dumps(frozen.to_dict())
    second = saved(
        runtime, body(probe_server.base_url, secret=None), f"{ROOT}/{first['id']}/versions"
    )
    with runtime.db() as db:
        assert db.get(ModelConfiguration, second["id"]).credential_id == original_credential
    rotated = saved(
        runtime,
        body(probe_server.base_url, secret="replacement-fixture-key"),
        f"{ROOT}/{second['id']}/versions",
    )
    rotated_test = probe_result(runtime, rotated)
    assert activate(runtime, rotated, rotated_test, version=1).status_code == 200
    with runtime.db() as db:
        assert resolve_secret(db, runtime.settings, frozen.configuration_id) == SECRET
        assert (
            resolve_secret(db, runtime.settings, PREFIX + rotated["id"])
            == "replacement-fixture-key"
        )
    assert SECRET.encode() not in runtime.path.read_bytes()


def test_invalid_and_failed_probe_cannot_activate_and_no_secret_leak(
    model_runtime, probe_server, caplog
):
    runtime = model_runtime
    row = saved(runtime, body(probe_server.base_url))
    good = probe_result(runtime, row)
    probe_server.control["status"] = 401
    failed = probe_result(runtime, row)
    assert failed["status"] == "failed"
    assert failed["diagnostic_code"] == "PROVIDER_AUTH_ERROR"
    assert activate(runtime, row, good).status_code == 409
    assert activate(runtime, row, failed).status_code == 409
    assert (
        len(probe_server.observed) == 6
    )  # three good stages, three explicitly requested failing suites
    probe_server.control.update(status=200, text='{"ok":true,"secret":"' + SECRET + '"}')
    malformed = probe_result(runtime, row)
    assert malformed["diagnostic_code"] == "PROVIDER_PROBE_INVALID"
    all_public = runtime.client.get(ROOT, headers=runtime.headers()).text
    assert SECRET not in all_public and SECRET not in caplog.text
    with runtime.db() as db:
        records = db.scalars(select(ModelConnectionTest)).all()
        assert SECRET not in json.dumps(
            [{"code": r.diagnostic_code, "message": r.message, "usage": r.usage} for r in records]
        )


def test_key_destination_change_requires_explicit_action_and_clear_never_inherits_env(
    model_runtime, probe_server
):
    runtime = model_runtime
    row = saved(runtime, body(probe_server.base_url))
    changed = body("http://127.0.0.1:9999/v1", secret=None)
    url = f"{ROOT}/{row['id']}/versions"
    assert runtime.client.post(url, json=changed, headers=runtime.headers()).status_code == 422
    changed["clear_api_key"] = True
    clear = saved(runtime, changed, url)
    assert not clear["has_api_key"]
    with runtime.db() as db:
        assert resolve_secret(db, runtime.settings, PREFIX + clear["id"]) is None
        assert (
            resolve_secret(db, runtime.settings, "legacy-env-configuration") == "unrelated-env-key"
        )
        with pytest.raises(AppError, match="frozen model configuration"):
            resolve_secret(db, runtime.settings, PREFIX + "missing")


def test_successor_conflict_immutability_and_explicit_environment_revert(model_runtime):
    runtime = model_runtime
    row = saved(runtime, body(secret=None))
    check = probe_result(runtime, row)
    assert check["diagnostic_code"] == "MOCK_OK" and check["model_mode"] == "mock"
    assert activate(runtime, row, check).status_code == 200
    saved(runtime, body(secret=None), f"{ROOT}/{row['id']}/versions")
    assert (
        runtime.client.post(
            f"{ROOT}/{row['id']}/versions", headers=runtime.headers(), json=body(secret=None)
        ).status_code
        == 409
    )
    with runtime.db() as db:
        db.get(ModelConfiguration, row["id"]).name = "overwrite"
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()
    response = runtime.client.post(
        ROOT + "/use-environment", headers=runtime.headers(), json={"expected_active_version": 1}
    )
    assert response.status_code == 200
    assert response.json()["data"]["source"] == "environment"
    with runtime.db() as db:
        assert len(db.scalars(select(ModelActivation)).all()) == 2
        assert db.get(ModelConfiguration, row["id"]).name != "overwrite"


@pytest.mark.parametrize(
    "base",
    [
        "https://user:private-value@example.com/v1",
        "https://example.com/v1?api_key=private-value",
        "https://example.com/v1#private-value",
        "file:///private-value",
    ],
)
def test_base_url_never_accepts_inline_credentials(model_runtime, base):
    response = model_runtime.client.post(ROOT, headers=model_runtime.headers(), json=body(base))
    assert response.status_code == 422
    assert "private-value" not in response.text and SECRET not in response.text


def test_bootstrap_key_is_atomic_and_not_created_in_production(tmp_path):
    settings = Settings(
        _env_file=None,
        env="test",
        model_config_key_file=str(tmp_path / "private/key"),
        model_config_encryption_key=None,
    )
    assert encryption_ready(settings)
    encrypted = encrypt(settings, SECRET)
    original = Path(settings.model_config_key_file).read_bytes()
    assert decrypt(settings, encrypted) == SECRET
    assert encrypt(settings, "another-key") != encrypted
    assert Path(settings.model_config_key_file).read_bytes() == original
    assert SECRET not in original.decode()
    if os.name != "nt":
        assert Path(settings.model_config_key_file).stat().st_mode & 0o077 == 0
    missing = Settings(
        _env_file=None,
        env="production",
        jwt_secret="production-example-key-at-least-thirty-two-characters",
        model_config_key_file=str(tmp_path / "missing/key"),
        model_config_encryption_key=None,
    )
    with pytest.raises(AppError):
        encrypt(missing, SECRET)
    assert not Path(missing.model_config_key_file).exists()
    wrong = settings.model_copy(
        update={"model_config_encryption_key": Fernet.generate_key().decode()}
    )
    with pytest.raises(AppError):
        decrypt(wrong, encrypted)


def test_accounts_are_scoped_and_reset_revokes_existing_login(model_runtime):
    runtime = model_runtime
    admin = runtime.headers()
    listed = runtime.client.get("/api/v1/admin/users", headers=admin).json()["data"]
    assert {row["email"] for row in listed} == {"admin@example.com", "student@example.com"}
    with runtime.db() as db:
        other = db.scalar(select(User).where(User.email == "other@example.com"))
        other_id, other_version = other.id, other.version
    assert (
        runtime.client.patch(
            f"/api/v1/admin/users/{other_id}",
            headers=admin,
            json={"version": other_version, "status": "deactivated"},
        ).status_code
        == 404
    )
    student = next(row for row in listed if row["email"] == "student@example.com")
    old_login = runtime.headers("student@example.com")
    response = runtime.client.patch(
        f"/api/v1/admin/users/{student['id']}",
        headers=admin,
        json={"version": student["version"], "password": "new-test-password-123"},
    )
    assert response.status_code == 200 and "new-test-password" not in response.text
    assert runtime.client.get("/api/v1/users/me", headers=old_login).status_code == 401
    assert (
        runtime.client.post(
            "/api/v1/auth/login",
            json={"email": student["email"], "password": "new-test-password-123"},
        ).status_code
        == 200
    )
    administrator = next(row for row in listed if row["email"] == "admin@example.com")
    assert (
        runtime.client.patch(
            f"/api/v1/admin/users/{administrator['id']}",
            headers=admin,
            json={"version": administrator["version"], "status": "deactivated"},
        ).status_code
        == 409
    )


def test_three_tiers_role_gate_and_idempotency(model_runtime, probe_server):
    runtime = model_runtime
    row = saved(runtime, body(probe_server.base_url))
    basic = probe_result(runtime, row, tier="basic", key="basic-once")
    assert basic["status"] == "passed" and not basic["project_passed"]
    assert len(probe_server.observed) == 1
    assert probe_result(runtime, row, tier="basic", key="basic-once")["id"] == basic["id"]
    assert len(probe_server.observed) == 1
    conflict = runtime.client.post(
        f"{ROOT}/{row['id']}/test",
        headers={**runtime.headers(), "Idempotency-Key": "basic-once"},
        json={"tier": "all"},
    )
    assert conflict.status_code == 409
    checker = probe_result(runtime, row, role="checker")
    denied = runtime.client.post(
        f"{ROOT}/{row['id']}/activate",
        headers=runtime.headers(),
        json={
            "test_id": basic["id"],
            "checker_test_id": checker["id"],
            "expected_active_version": 0,
        },
    )
    assert denied.status_code == 409
    answer = probe_result(runtime, row)
    assert [item["tier"] for item in answer["stages"]] == ["basic", "structured", "project"]
    assert answer["budget"]["reserved_attempts"] == 3
    assert all(
        item["metadata"]["configuration_id"] == PREFIX + row["id"] for item in answer["stages"]
    )
    activated = runtime.client.post(
        f"{ROOT}/{row['id']}/activate",
        headers=runtime.headers(),
        json={
            "test_id": answer["id"],
            "checker_test_id": checker["id"],
            "expected_active_version": 0,
        },
    )
    assert activated.status_code == 200
    history = runtime.client.get(f"{ROOT}/{row['id']}/tests", headers=runtime.headers()).json()[
        "data"
    ]
    assert len(history) == 3 and all(
        item["test_version"] == "provider_probe_v4" for item in history
    )
    with runtime.db() as db:
        stage = db.scalar(
            select(ModelCompatibilityStage).where(ModelCompatibilityStage.run_id == answer["id"])
        )
        stage.result_json = {"forged": True}
        with pytest.raises(ValueError, match="immutable"):
            db.commit()


def test_uncertain_started_probe_is_not_replayed(model_runtime, monkeypatch):
    from generation import probes

    runtime = model_runtime
    row = saved(runtime, body("http://127.0.0.1:1/v1"))
    calls = []

    def interrupted(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("private transport exception")

    monkeypatch.setattr(probes, "run", interrupted)
    first = probe_result(runtime, row, key="uncertain-once")
    assert first["status"] == "uncertain"
    assert [stage["status"] for stage in first["stages"]] == ["uncertain", "not_run", "not_run"]
    assert first["budget"]["reserved_attempts"] == 1
    assert probe_result(runtime, row, key="uncertain-once")["id"] == first["id"]
    assert len(calls) == 1
    assert "private transport" not in json.dumps(first)


def test_distinct_checker_config_is_frozen_and_workspace_scoped(model_runtime):
    from app.modules.model_settings.service import resolve_active_checker_model_config

    runtime = model_runtime
    answer_row = saved(runtime, body(secret=None))
    checker_body = body(secret=None)
    checker_body["config"]["model"] = "separate-checker-fixture"
    checker_row = saved(runtime, checker_body)
    answer = probe_result(runtime, answer_row)
    checker = probe_result(runtime, checker_row, role="checker")
    result = runtime.client.post(
        f"{ROOT}/{answer_row['id']}/activate",
        headers=runtime.headers(),
        json={
            "test_id": answer["id"],
            "checker_configuration_id": checker_row["id"],
            "checker_test_id": checker["id"],
            "expected_active_version": 0,
        },
    )
    assert result.status_code == 200
    assert result.json()["data"]["active_checker_configuration_id"] == checker_row["id"]
    with runtime.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        frozen = resolve_active_checker_model_config(db, runtime.settings, actor.workspace_id)
        assert frozen.configuration_id == PREFIX + checker_row["id"]
        assert frozen.max_tokens == 4096 and frozen.model == "separate-checker-fixture"


@pytest.mark.parametrize("fingerprint", ["schema_hash", "prompt_hash"])
def test_legacy_or_changed_schema_receipt_cannot_enable_new_activation(
    model_runtime, monkeypatch, fingerprint
):
    from generation import probes

    runtime = model_runtime
    row = saved(runtime, body(secret=None))
    with runtime.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        legacy = ModelConnectionTest(
            configuration_id=row["id"],
            status="passed",
            diagnostic_code="MOCK_OK",
            message="Historical one-call test",
            latency_ms=0,
            usage={},
            tested_by=actor.id,
        )
        db.add(legacy)
        db.commit()
        legacy_id = legacy.id
    checker = probe_result(runtime, row, role="checker")
    rejected = runtime.client.post(
        f"{ROOT}/{row['id']}/activate",
        headers=runtime.headers(),
        json={"test_id": legacy_id, "checker_test_id": checker["id"], "expected_active_version": 0},
    )
    assert rejected.status_code == 409
    answer = probe_result(runtime, row)
    original = probes.description

    def changed(*args, **kwargs):
        value = original(*args, **kwargs)
        value["metadata"][fingerprint] = "f" * 64
        return value

    monkeypatch.setattr(probes, "description", changed)
    rejected = runtime.client.post(
        f"{ROOT}/{row['id']}/activate",
        headers=runtime.headers(),
        json={
            "test_id": answer["id"],
            "checker_test_id": checker["id"],
            "expected_active_version": 0,
        },
    )
    assert rejected.status_code == 409
    assert "schema" in rejected.text
    history = runtime.client.get(f"{ROOT}/{row['id']}/tests", headers=runtime.headers()).json()[
        "data"
    ]
    historical = next(item for item in history if item["id"] == legacy_id)
    assert historical["test_version"] == "legacy_connection_v1" and not historical["project_passed"]


def test_model_profile_is_a_declaration_and_preflight_failure_has_no_hidden_transport(
    model_runtime, probe_server
):
    runtime = model_runtime
    payload = body(probe_server.base_url)
    payload["config"].update(provider="openai", model="gpt-5.6-luna", temperature=0)
    row = saved(runtime, payload)
    assert row["config"]["capabilities"]["temperature"] is False
    result = probe_result(runtime, row)
    assert [stage["status"] for stage in result["stages"]] == ["passed", "failed", "not_run"]
    assert result["stages"][1]["diagnostic_code"] == "CONFIGURATION_ERROR"
    assert len(probe_server.observed) == 1
    profile = runtime.client.post(
        ROOT + "/capability-profile", headers=runtime.headers(), json=row["config"]
    ).json()["data"]
    assert not profile["observed_compatibility"]
    assert profile["suggested_options"]["temperature"] is None
    assert profile["suggested_options"]["reasoning_effort"] == "low"
