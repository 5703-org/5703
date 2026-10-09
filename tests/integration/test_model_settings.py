"""Real PostgreSQL locking and immutable model-version lifecycle."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import select
from app.core.exceptions import AppError
from app.modules.identity.models import User
from app.modules.model_settings.models import ModelConfiguration, ModelConnectionTest
from app.modules.model_settings.schemas import ConfigurationSave
from app.modules.model_settings import service


def test_model_configuration_parallel_successor_is_single_revision(runtime):
    headers = runtime.headers("admin@example.com")
    payload = {
        "name": "PostgreSQL concurrency fixture",
        "config": {"provider": "mock", "model": "authored-extractive-v1"},
    }
    response = runtime.client.post(
        "/api/v1/admin/model-configurations", headers=headers, json=payload
    )
    assert response.status_code == 201, response.text
    original = response.json()["data"]
    with runtime.db() as db:
        actor_id = db.scalar(select(User.id).where(User.email == "admin@example.com"))
    barrier = Barrier(2)

    def save_successor():
        with runtime.db() as db:
            actor = db.get(User, actor_id)
            barrier.wait(timeout=10)
            try:
                result = service.save(
                    db,
                    runtime.settings,
                    actor,
                    ConfigurationSave.model_validate(payload),
                    original["id"],
                )
                return "saved", result["revision"]
            except AppError as error:
                db.rollback()
                return error.code, None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(save_successor) for _ in range(2)]
        outcomes = [future.result(timeout=30) for future in futures]
    assert sorted(outcome[0] for outcome in outcomes) == ["CONFLICT", "saved"]
    with runtime.db() as db:
        versions = db.scalars(
            select(ModelConfiguration)
            .where(ModelConfiguration.group_id == original["group_id"])
            .order_by(ModelConfiguration.revision)
        ).all()
        assert [row.revision for row in versions] == [1, 2]
        assert versions[0].public_config == versions[1].public_config
        assert versions[1].previous_id == versions[0].id


def test_model_configuration_parallel_first_activation_is_single_pointer(runtime):
    headers = runtime.headers("admin@example.com")
    payload = {
        "name": "PostgreSQL active pointer fixture",
        "config": {"provider": "mock", "model": "authored-extractive-v1"},
    }
    original = runtime.client.post(
        "/api/v1/admin/model-configurations", headers=headers, json=payload
    ).json()["data"]
    probe = runtime.client.post(
        f"/api/v1/admin/model-configurations/{original['id']}/test", headers=headers
    ).json()["data"]
    assert probe["status"] == "passed" and probe["model_mode"] == "mock"
    checker = runtime.client.post(
        f"/api/v1/admin/model-configurations/{original['id']}/test",
        headers=headers,
        json={"role": "checker"},
    ).json()["data"]
    current = runtime.client.get("/api/v1/admin/model-configurations", headers=headers).json()[
        "data"
    ]["active_version"]
    with runtime.db() as db:
        actor_id = db.scalar(select(User.id).where(User.email == "admin@example.com"))
    barrier = Barrier(2)

    def activate():
        with runtime.db() as db:
            actor = db.get(User, actor_id)
            barrier.wait(timeout=10)
            try:
                result = service.activate(
                    db,
                    runtime.settings,
                    actor,
                    original["id"],
                    probe["id"],
                    current,
                    checker_test_id=checker["id"],
                )
                return "activated", result["active_version"]
            except AppError as error:
                db.rollback()
                return error.code, None

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(activate) for _ in range(2)]
        outcomes = [future.result(timeout=30) for future in futures]
    assert sorted(outcome[0] for outcome in outcomes) == ["CONFLICT", "activated"]
    final = runtime.client.get("/api/v1/admin/model-configurations", headers=headers).json()["data"]
    assert final["active_version"] == current + 1
    assert final["active_configuration_id"] == original["id"]


def test_capabilities_uses_workspace_managed_mode_and_reverts_to_environment(runtime, monkeypatch):
    """Readiness projection with an explicit stubbed probe, not live connectivity."""
    from generation import probes
    from generation.types import ProviderResult

    monkeypatch.setattr(
        probes,
        "run",
        lambda prepared, **kwargs: ProviderResult(
            raw_text="",
            provider=prepared["config"].provider,
            model=prepared["config"].model,
            diagnostic={"stage": "completed", "message": "Explicit local test injection"},
        ),
    )
    runtime.settings.model_mode = "mock"
    runtime.settings.llm_provider = "mock"
    headers = runtime.headers("admin@example.com")
    before = runtime.client.get("/api/v1/capabilities", headers=runtime.headers()).json()["data"]
    assert before["model_mode"] == "mock"
    payload = {
        "name": "Capabilities projection fixture",
        "config": {
            "provider": "local",
            "model": "authored-projection-only",
            "base_url": "http://127.0.0.1:9999/v1",
        },
    }
    original = runtime.client.post(
        "/api/v1/admin/model-configurations", headers=headers, json=payload
    ).json()["data"]
    probe = runtime.client.post(
        f"/api/v1/admin/model-configurations/{original['id']}/test", headers=headers
    ).json()["data"]
    checker = runtime.client.post(
        f"/api/v1/admin/model-configurations/{original['id']}/test",
        headers=headers,
        json={"role": "checker"},
    ).json()["data"]
    current = runtime.client.get("/api/v1/admin/model-configurations", headers=headers).json()[
        "data"
    ]["active_version"]
    activated = runtime.client.post(
        f"/api/v1/admin/model-configurations/{original['id']}/activate",
        headers=headers,
        json={
            "test_id": probe["id"],
            "checker_test_id": checker["id"],
            "expected_active_version": current,
        },
    )
    assert activated.status_code == 200
    response = runtime.client.get("/api/v1/capabilities", headers=runtime.headers())
    assert response.status_code == 200
    assert response.json()["data"]["model_mode"] == "live"
    assert "9999" not in response.text and "authored-projection-only" not in response.text
    assert "credential" not in response.json()["data"]
    reverted = runtime.client.post(
        "/api/v1/admin/model-configurations/use-environment",
        headers=headers,
        json={"expected_active_version": current + 1},
    )
    assert reverted.status_code == 200
    assert (
        runtime.client.get("/api/v1/capabilities", headers=runtime.headers()).json()["data"][
            "model_mode"
        ]
        == "mock"
    )


def test_started_suite_receipt_precedes_transport_and_prevents_duplicate_calls(
    runtime, monkeypatch
):
    from threading import Event
    from generation import probes
    from generation.types import ProviderResult
    from app.modules.model_settings.schemas import CompatibilityInput
    from app.modules.model_settings.models import ModelCompatibilityStage

    started, release = Event(), Event()
    calls = []

    def transport(prepared, **kwargs):
        calls.append(prepared["metadata"]["tier"])
        if len(calls) == 1:
            started.set()
            assert release.wait(timeout=15)
        return ProviderResult(diagnostic={"stage": "completed", "request_submitted": True})

    monkeypatch.setattr(probes, "run", transport)
    headers = runtime.headers("admin@example.com")
    row = runtime.client.post(
        "/api/v1/admin/model-configurations",
        headers=headers,
        json={
            "name": "Authored concurrency fixture",
            "config": {
                "provider": "local",
                "model": "fixture",
                "base_url": "http://127.0.0.1:1/v1",
            },
        },
    ).json()["data"]
    with runtime.db() as db:
        actor_id = db.scalar(select(User.id).where(User.email == "admin@example.com"))

    def execute():
        with runtime.db() as db:
            return service.run_test(
                db,
                runtime.settings,
                db.get(User, actor_id),
                row["id"],
                CompatibilityInput(),
                "one-exact-suite",
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(execute)
        assert started.wait(timeout=15)
        try:
            with runtime.db() as db:
                actor = db.get(User, actor_id)
                same = service.run_test(
                    db, runtime.settings, actor, row["id"], CompatibilityInput(), "one-exact-suite"
                )
                assert same["status"] == "running"
                stage = db.scalar(
                    select(ModelCompatibilityStage).where(
                        ModelCompatibilityStage.run_id == same["id"]
                    )
                )
                assert (
                    stage.status == "started" and stage.metadata_json["transport_reserved"] is True
                )
                try:
                    service.run_test(
                        db,
                        runtime.settings,
                        actor,
                        row["id"],
                        CompatibilityInput(),
                        "different-suite",
                    )
                    assert False, "Concurrent suite must be rejected"
                except AppError as error:
                    assert error.code == "CONFLICT"
                db.rollback()
        finally:
            release.set()
        result = future.result(timeout=20)
    assert result["status"] == "passed"
    assert calls == ["basic", "structured", "project"]
