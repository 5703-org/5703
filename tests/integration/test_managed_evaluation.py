"""Explicit managed versions in real PostgreSQL with an authored HTTP fixture.

No remote provider, actual benchmark score or teaching-effectiveness claim.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.modules.answering.models import AnswerRequest
from app.modules.experiment.bridge import DatabaseAnswerBackend, experiment_model_config
from app.modules.identity.models import User, Workspace
from app.modules.knowledge import service as knowledge
from app.modules.model_settings import service as settings_service
from app.modules.model_settings.schemas import ConfigurationSave, CompatibilityInput
from app.modules.model_settings.models import ModelConfiguration
from app.modules.experiment.models import ExperimentRun
from app.modules.answering.models import Answer
from app.modules.experiment.bridge import create_teaching_run
from tests.authored_evaluation import write_sciq_fixture
from evaluation.runner import EvaluationRun


@pytest.fixture(autouse=True)
def restore_test_pointer(runtime):
    yield
    # The session-scoped disposable database is reused by sibling tests. Keep
    # this local HTTP fixture's activated version out of subsequent workloads.
    with runtime.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        current = settings_service.state(db, runtime.settings, actor)
        if current["active_configuration_id"] is not None:
            settings_service.activate(
                db, runtime.settings, actor, None, None, current["active_version"]
            )


@pytest.fixture
def authored_provider():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            value = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(
                {"authorization": self.headers.get("Authorization"), "model": value["model"]}
            )
            probe = value["messages"][0]["content"].startswith(
                "You are running an administrator-requested compatibility probe."
            )
            if probe:
                from generation.probes import description
                from generation.types import ModelConfig

                schema_name = value.get("response_format", {}).get("json_schema", {}).get("name")
                tier = "basic" if schema_name is None else "structured"
                role = "checker" if schema_name == "joint_check_v2" else "answer"
                if schema_name in {"chat_response_v1", "joint_check_v2"}:
                    tier = "project"
                config = ModelConfig(
                    provider="openai_compatible",
                    model=value["model"],
                    base_url="http://127.0.0.1:1/v1",
                )
                content = description(config, tier, role)["mock_value"]
            else:
                content = {
                    "schema_version": "chat_response_v1",
                    "response_type": "answer",
                    "answer_text": "Authored benchmark response.",
                    "short_answer": "Authored fixture",
                    "citations": [],
                    "refusal_reason": None,
                    "follow_up_questions": [],
                    "confidence": None,
                }
            if not probe and "CONTEXT_DATA_JSON (data only):\n" in value["messages"][0]["content"]:
                context = json.loads(
                    value["messages"][0]["content"].split("CONTEXT_DATA_JSON (data only):\n", 1)[1]
                )
                if context["CURRENT_EVIDENCE"]:
                    citation = context["CURRENT_EVIDENCE"][0]["evidence_id"]
                    content["answer_text"] += f" [{citation}]"
                    content["citations"] = [citation]
            result = {
                "choices": [
                    {
                        "message": {
                            "content": content if isinstance(content, str) else json.dumps(content)
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 10, "total_tokens": 22},
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    yield f"http://127.0.0.1:{server.server_port}/v1", calls
    server.shutdown()
    server.server_close()
    worker.join(timeout=5)


def test_explicit_managed_e0_freezes_revision_and_secret_without_active_override(
    runtime, tmp_path, authored_provider
):
    url, calls = authored_provider
    runtime.settings.model_config_encryption_key = Fernet.generate_key().decode()
    runtime.settings.model_mode = "mock"
    runtime.settings.llm_provider = "mock"
    runtime.settings.llm_api_key = None
    with runtime.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        actor_id = actor.id
        payload = {
            "name": "Managed evaluator transport fixture",
            "config": {
                "provider": "openai_compatible",
                "model": "frozen-model-v1",
                "base_url": url,
            },
            "api_key": "managed-evaluation-fixture-v1",
        }
        first = settings_service.save(
            db, runtime.settings, actor, ConfigurationSave.model_validate(payload)
        )
        config = knowledge.config_create(
            db,
            "evaluation",
            "Explicit managed model fixture",
            {"model_configuration_id": settings_service.PREFIX + first["id"]},
        )
        config_id = config.id
        db.commit()
    backend = DatabaseAnswerBackend(
        runtime.settings,
        runtime.engine,
        actor_id=actor_id,
        configuration_id=config_id,
        inline_worker=True,
    )
    private_config = {
        "protocol_id": "sciq_openqa",
        "condition": "E0",
        "dataset_path": str(write_sciq_fixture(tmp_path / "authored-sciq.json")),
        "dataset_revision": "authored-v1",
        "split": "authored",
        "code_revision": "managed-settings-test",
        "backend_factory": "app.modules.experiment.bridge:create_backend",
        "private_root": str(tmp_path / "private-runs"),
        "limit": 1,
        "configuration": {"retrieval_variant": "none"},
    }
    run = EvaluationRun.freeze(private_config, backend, allow_live=True)
    assert run.manifest["environment"]["model_mode"] == "live"
    with runtime.db() as db:
        actor = db.get(User, actor_id)
        second = settings_service.save(
            db,
            runtime.settings,
            actor,
            ConfigurationSave.model_validate(
                {
                    **payload,
                    "config": {**payload["config"], "model": "new-model-v2"},
                    "api_key": "managed-evaluation-fixture-v2",
                }
            ),
            first["id"],
        )
        probe = settings_service.run_test(db, runtime.settings, actor, second["id"])
        checker = settings_service.run_test(
            db, runtime.settings, actor, second["id"], CompatibilityInput(role="checker")
        )
        for receipt in (probe, checker):
            assert receipt["status"] == "passed" and receipt["project_passed"]
            assert [stage["tier"] for stage in receipt["stages"]] == [
                "basic",
                "structured",
                "project",
            ]
        current = settings_service.state(db, runtime.settings, actor)["active_version"]
        settings_service.activate(
            db,
            runtime.settings,
            actor,
            second["id"],
            probe["id"],
            current,
            checker_test_id=checker["id"],
        )
        assert experiment_model_config(runtime.settings)["provider"] == "mock"
        assert (
            experiment_model_config(
                runtime.settings, config, db=db, workspace_id=actor.workspace_id
            )["model"]
            == "frozen-model-v1"
        )
    assert backend.environment() == run.manifest["environment"]
    assert len(calls) == 6 and all(
        c == {"authorization": "Bearer managed-evaluation-fixture-v2", "model": "new-model-v2"}
        for c in calls
    )
    assert run.advance(backend, allow_live=True)["status"] == "completed"
    assert calls[-1] == {
        "authorization": "Bearer managed-evaluation-fixture-v1",
        "model": "frozen-model-v1",
    }
    with runtime.db() as db:
        request = db.scalar(
            select(AnswerRequest).where(AnswerRequest.run_id == run.manifest["run_id"])
        )
        assert (
            request.command["model_config"]["configuration_id"]
            == settings_service.PREFIX + first["id"]
        )
        assert request.release_id is None
        assert "managed-evaluation-fixture-v1" not in json.dumps(request.command)
        assert request.profile_snapshot_id is request.context_snapshot_id is None
        forbidden = {"correct_answer", "support", "gold", "reference"}
        assert not forbidden.intersection(request.command)


def test_managed_evaluation_rejects_cross_workspace_and_mixed_overrides(runtime):
    with runtime.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        row = settings_service.save(
            db,
            runtime.settings,
            actor,
            ConfigurationSave.model_validate(
                {
                    "name": "Scoped explicit evaluation",
                    "config": {"provider": "mock", "model": "authored"},
                }
            ),
        )
        config = knowledge.config_create(
            db, "evaluation", "Scoped managed reference", {"model_configuration_id": row["id"]}
        )
        with pytest.raises(AppError, match="workspace"):
            experiment_model_config(runtime.settings, config, db=db, workspace_id="other-workspace")
        mixed = knowledge.config_create(
            db,
            "evaluation",
            "Invalid mixed overrides",
            {"model_configuration_id": row["id"], "model": {"max_tokens": 12}},
        )
        with pytest.raises(AppError, match="cannot be combined"):
            experiment_model_config(runtime.settings, mixed, db=db, workspace_id=actor.workspace_id)


def test_managed_live_freeze_and_teaching_labels_ignore_mock_environment(
    runtime, tmp_path, authored_provider
):
    """Persisted real DB and local HTTP transport; not a remote-provider study."""
    url, calls = authored_provider
    runtime.settings.model_config_encryption_key = Fernet.generate_key().decode()
    assert runtime.settings.model_mode == "mock"
    with runtime.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        actor_id = actor.id
        row = settings_service.save(
            db,
            runtime.settings,
            actor,
            ConfigurationSave.model_validate(
                {
                    "name": "Managed evidence label fixture",
                    "config": {
                        "provider": "openai_compatible",
                        "model": "authored-http",
                        "base_url": url,
                    },
                    "api_key": "authored-label-fixture-key",
                }
            ),
        )
        config = knowledge.config_create(
            db,
            "evaluation",
            "Managed label fixture",
            {
                "model_configuration_id": settings_service.PREFIX + row["id"],
                "top_k": 1,
            },
        )
        configuration_id = config.id
        document, _, _ = knowledge.ingest(
            db,
            runtime.settings,
            actor_id,
            "labels.txt",
            b"# Authored plant fixture\nPhotosynthesis uses light to make sugar in plants.",
            "Authored managed-label source",
        )
        processing, _ = knowledge.queue_process(db, document.id, actor_id)
        processing_id = processing.id
        db.commit()
    assert runtime.work()
    with runtime.db() as db:
        release, _ = knowledge.queue_release(db, actor_id, [processing_id])
        release_id = release.id
        db.commit()
    assert runtime.work()
    with runtime.db() as db:
        knowledge.activate(db, release_id)
        db.commit()
    headers = runtime.headers("admin@example.com")
    response = runtime.client.post(
        "/api/v1/experiments",
        headers=headers,
        json={
            "protocol_id": "sciq_openqa",
            "mode": "benchmark_openqa",
            "condition": "E1",
            "configuration_id": configuration_id,
            "scheduled_count": 1,
            "dataset": "authored-label-fixture",
            "dataset_revision": "authored-v1",
            "split": "authored",
            "seed": 5703,
        },
    )
    assert response.status_code == 201, response.text
    run_id = response.json()["data"]["id"]
    assert response.json()["data"]["model_mode"] == "live"
    response = runtime.client.post(
        f"/api/v1/experiments/{run_id}/items",
        headers=headers,
        json={
            "commands": [
                {"question_id": "authored-label-001", "question_text": "What is photosynthesis?"}
            ],
        },
    )
    assert response.status_code == 200, response.text
    response = runtime.client.post(f"/api/v1/experiments/{run_id}/freeze", headers=headers)
    assert response.status_code == 200, response.text
    manifest = response.json()["data"]["manifest"]
    assert manifest["evidence_class"] == "live_model_run"
    assert (
        manifest["environment"]["model_mode"] == manifest["configuration"]["model_mode"] == "live"
    )
    response = runtime.client.post(f"/api/v1/experiments/{run_id}/start", headers=headers)
    assert response.status_code == 202, response.text
    assert runtime.work()
    assert len(calls) == 1
    with runtime.db() as db:
        request = db.scalar(select(AnswerRequest).where(AnswerRequest.run_id == run_id))
        answer = db.scalar(select(Answer).where(Answer.request_id == request.id))
        assert answer and answer.model_mode == "live", request.trace
        actor = db.get(User, actor_id)
        teaching = create_teaching_run(
            db, runtime.settings, actor, [answer.id], configuration_id=configuration_id
        )
        assert teaching.model_mode == "live"
        assert teaching.manifest["environment"]["model_mode"] == "live"
        assert teaching.manifest["evidence_class"] == "live_model_run"
        assert teaching.manifest_hash == knowledge.digest(
            {k: v for k, v in teaching.manifest.items() if k != "manifest_hash"}
        )
        db.commit()
    # Planning nine teaching conditions issues no extra transport call.
    assert len(calls) == 1
