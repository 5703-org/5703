"""Answer-only role grants, submission fences and migration SQL without a DB."""

from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import socket

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

import app.db.models  # noqa: F401
from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.answering import service as answering
from app.modules.answering.hint_capability import hint_capability
from app.modules.answering.models import AnswerRequest, Job
from app.modules.learning_product import service as practice
from app.modules.learning_state import memory, tasks
from app.modules.model_settings import compatibility, service
from app.modules.model_settings.activation_scope import (
    ANSWER_AND_CHECKER,
    ANSWER_ONLY,
    active_scope,
    checker_activation_status,
)
from app.modules.model_settings.models import ActiveModelConfiguration, ModelActivation
from app.modules.model_settings.schemas import ActivationInput
from contracts.models import ChatMessageCreate
from generation.adapters import LLMAdapter
from generation.types import ModelConfig


class FakeDB:
    def __init__(self, pointer):
        self.pointer = pointer
        self.added = []
        self.commits = 0

    def get(self, model, identity):
        assert model is ActiveModelConfiguration
        return self.pointer

    def add(self, row):
        self.added.append(row)

    def flush(self):
        pass

    def commit(self):
        self.commits += 1

    def scalar(self, query):
        return None


@pytest.fixture(autouse=True)
def deny_external_operations(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("These controls allow no network, provider or database connection")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(LLMAdapter, "generate", denied)
    import sqlalchemy
    import sqlalchemy.engine

    monkeypatch.setattr(sqlalchemy, "create_engine", denied)
    monkeypatch.setattr(sqlalchemy.engine.Engine, "connect", denied)


def pointer(scope=ANSWER_AND_CHECKER):
    return SimpleNamespace(
        workspace_id="workspace",
        configuration_id="old-answer",
        version=4,
        checker_configuration_id="old-checker",
        activation_scope=scope,
    )


@pytest.mark.parametrize(
    "scope,roles",
    [
        (ANSWER_ONLY, ["answer"]),
        (ANSWER_AND_CHECKER, ["answer", "checker"]),
    ],
)
def test_activation_persists_exact_role_grants_atomically(monkeypatch, scope, roles):
    db = FakeDB(pointer())
    actor = SimpleNamespace(id="actor", workspace_id="workspace")
    row = SimpleNamespace(id="answer", workspace_id="workspace")
    calls, secrets = [], []
    monkeypatch.setattr(service, "owned", lambda *args, **kwargs: row)
    monkeypatch.setattr(service, "_active_locked", lambda *args: db.pointer)
    monkeypatch.setattr(
        service, "resolve_secret", lambda db, settings, identity: secrets.append(identity)
    )
    monkeypatch.setattr(
        service, "state", lambda *args: {"activation_scope": db.pointer.activation_scope}
    )

    def require(db, config, proof, role):
        assert config is row and proof == f"{role}-proof"
        calls.append(role)

    monkeypatch.setattr(compatibility, "require_project_pass", require)
    result = service.activate(
        db,
        None,
        actor,
        "answer",
        "answer-proof",
        4,
        checker_test_id="checker-proof" if scope == ANSWER_AND_CHECKER else None,
        activation_scope=scope,
    )
    assert calls == roles
    assert len(secrets) == len(roles)
    assert db.commits == 1 and db.pointer.version == 5
    assert db.pointer.configuration_id == "answer"
    assert result["activation_scope"] == scope
    receipt = db.added[0]
    assert isinstance(receipt, ModelActivation)
    assert receipt.activation_scope == db.pointer.activation_scope == scope
    assert receipt.answer_probe_id == "answer-proof"
    assert (
        receipt.checker_configuration_id
        == db.pointer.checker_configuration_id
        == ("answer" if scope == ANSWER_AND_CHECKER else None)
    )
    assert receipt.checker_probe_id == ("checker-proof" if scope == ANSWER_AND_CHECKER else None)


@pytest.mark.parametrize(
    "changes",
    [
        {"checker_configuration_id": "checker"},
        {"checker_test_id": "checker-proof"},
        {"checker_configuration_id": ""},
        {"checker_test_id": ""},
        {"activation_scope": "invented"},
    ],
)
def test_answer_only_rejects_contradictory_or_unknown_role_selection(monkeypatch, changes):
    db = FakeDB(pointer())
    calls = []

    def denied(*args, **kwargs):
        calls.append("owned_or_proof")
        raise AssertionError("Contradictory roles must stop before ownership or proof lookup")

    monkeypatch.setattr(service, "owned", denied)
    monkeypatch.setattr(compatibility, "require_project_pass", denied)
    options = {"activation_scope": ANSWER_ONLY, **changes}
    with pytest.raises(AppError, match="explicit activation scope"):
        service.activate(db, None, SimpleNamespace(), "answer", "proof", 4, **options)
    assert db.added == [] and db.commits == 0 and db.pointer.version == 4
    assert calls == []


def test_answer_only_does_not_bypass_answer_proof_or_active_version(monkeypatch):
    db = FakeDB(pointer())
    row = SimpleNamespace(id="answer")
    monkeypatch.setattr(service, "owned", lambda *args, **kwargs: row)
    monkeypatch.setattr(service, "_active_locked", lambda *args: db.pointer)
    monkeypatch.setattr(service, "resolve_secret", lambda *args: None)

    def reject(*args):
        raise AppError("CONFLICT", "Latest exact answer project test required")

    monkeypatch.setattr(compatibility, "require_project_pass", reject)
    with pytest.raises(AppError, match="exact answer"):
        service.activate(
            db,
            None,
            SimpleNamespace(workspace_id="workspace"),
            "answer",
            "stale",
            4,
            activation_scope=ANSWER_ONLY,
        )
    monkeypatch.setattr(compatibility, "require_project_pass", lambda *args: None)
    with pytest.raises(AppError, match="active model changed"):
        service.activate(
            db,
            None,
            SimpleNamespace(workspace_id="workspace"),
            "answer",
            "proof",
            3,
            activation_scope=ANSWER_ONLY,
        )
    assert not db.added and db.commits == 0


def test_legacy_activation_request_and_selection_keep_checked_semantics():
    assert (
        ActivationInput(test_id="proof", expected_active_version=0).activation_scope
        == ANSWER_AND_CHECKER
    )
    assert active_scope(None) == active_scope(SimpleNamespace()) == ANSWER_AND_CHECKER
    assert checker_activation_status(FakeDB(None), "workspace")["checker_enabled"]
    old = pointer()
    del old.activation_scope
    assert checker_activation_status(FakeDB(old), "workspace")["checker_enabled"]


def test_answer_only_blocks_checker_and_injected_hint_fallback_before_provider():
    db = FakeDB(pointer(ANSWER_ONLY))
    config = ModelConfig(
        provider="openai_compatible", model="fixture", base_url="https://fixture.invalid/v1"
    )
    with pytest.raises(AppError) as failure:
        service.resolve_active_checker_model_config(db, None, "workspace")
    assert failure.value.code == "SEMANTIC_CHECK_UNAVAILABLE"
    assert not checker_activation_status(db, "workspace")["checker_enabled"]
    status = hint_capability(db, None, "workspace", answer_config=config, checker_config=config)
    assert status["hint_ready"] is False
    assert db.commits == 0 and not db.added


class FastPathReached(Exception):
    pass


@pytest.mark.parametrize(
    "requested_check,teaching_mode",
    [
        (False, "direct"),
        (True, "direct"),
        (None, "direct"),
        (False, "hint"),
    ],
)
def test_fresh_chat_off_continues_but_checked_or_hint_requests_reject_before_queue(
    monkeypatch, requested_check, teaching_mode
):
    db = FakeDB(pointer(ANSWER_ONLY))
    actor = SimpleNamespace(id="actor", workspace_id="workspace")
    settings = Settings(_env_file=None, env="test")
    config = ModelConfig(
        provider="openai_compatible", model="fixture", base_url="https://fixture.invalid/v1"
    )
    monkeypatch.setattr(memory, "settings_for", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        answering, "owned_session", lambda *args, **kwargs: SimpleNamespace(status="active")
    )
    monkeypatch.setattr(answering, "idempotent", lambda *args: None)
    monkeypatch.setattr(answering, "active_job", lambda *args: None)
    monkeypatch.setattr(service, "resolve_active_model_config", lambda *args: config)
    monkeypatch.setattr(answering, "TokenCounter", lambda *args: object())
    monkeypatch.setattr(answering, "history_rows", lambda *args: [])
    monkeypatch.setattr(answering.profiles, "get_or_create_profile", lambda *args: object())
    monkeypatch.setattr(
        answering.profiles, "to_profile_out", lambda *args: SimpleNamespace(model_dump=lambda: {})
    )
    monkeypatch.setattr(answering, "compile_profile", lambda *args, **kwargs: {})
    monkeypatch.setattr(answering, "create_snapshot", lambda *args: SimpleNamespace(id="snapshot"))
    monkeypatch.setattr(
        answering, "select_context", lambda *args, **kwargs: SimpleNamespace(model_dump=lambda: {})
    )
    monkeypatch.setattr(answering, "persist_summary", lambda *args: None)
    monkeypatch.setattr(
        tasks,
        "resolve_task",
        lambda *args: {
            "task_id": "task",
            "teaching_mode": teaching_mode,
            "turn_role": "user_question",
        },
    )
    monkeypatch.setattr(tasks, "recent_attempt_feedback", lambda *args: [])

    def fast(*args, **kwargs):
        raise FastPathReached

    monkeypatch.setattr(memory, "freeze_memory", fast)
    body = ChatMessageCreate(
        content="Explain an isotope.", answer_mode="general_knowledge", check_answer=requested_check
    )
    ordinary_off = requested_check is False and teaching_mode == "direct"
    with pytest.raises(FastPathReached if ordinary_off else AppError) as failure:
        answering.submit_chat(db, settings, actor, "session", body, "key")
    if not ordinary_off:
        assert failure.value.code == "SEMANTIC_CHECK_UNAVAILABLE"
    assert not any(isinstance(row, (Job, AnswerRequest)) for row in db.added)
    assert db.commits == 0


def test_answer_only_rejects_model_practice_before_attempt_or_reservation(monkeypatch):
    db = FakeDB(pointer(ANSWER_ONLY))
    actor = SimpleNamespace(id="actor", workspace_id="workspace")
    progress = SimpleNamespace(current_step=1, version=4, state="active")
    item = SimpleNamespace(public_payload={"kind": "short_answer"}, private_rubric={})
    body = SimpleNamespace(
        idempotency_key="key",
        goal_id=None,
        expected_version=4,
        response=object(),
        model_dump=lambda **kwargs: {"response": "fixture"},
    )
    monkeypatch.setattr(practice, "lock_owner", lambda *args: None)
    monkeypatch.setattr(practice, "practice_item", lambda *args: item)
    monkeypatch.setattr(practice, "get_progress", lambda *args: progress)
    monkeypatch.setattr(practice, "cas", lambda *args: None)
    monkeypatch.setattr(practice.grading, "grade", lambda *args: {"outcome": "pending_review"})
    with pytest.raises(AppError) as failure:
        practice.submit_attempt(db, actor, "item", body)
    assert failure.value.code == "SEMANTIC_CHECK_UNAVAILABLE"
    assert not db.added and not db.commits and progress.version == 4


def test_existing_idempotent_submission_retains_its_frozen_request(monkeypatch):
    db = FakeDB(pointer(ANSWER_ONLY))
    actor = SimpleNamespace(id="actor", workspace_id="workspace")
    prior = object()
    monkeypatch.setattr(memory, "settings_for", lambda *args, **kwargs: None)
    monkeypatch.setattr(answering, "owned_session", lambda *args, **kwargs: object())
    monkeypatch.setattr(answering, "idempotent", lambda *args: prior)
    monkeypatch.setattr(answering, "receipt", lambda db, record: ("frozen", record))
    assert answering.submit_chat(
        db, None, actor, "session", ChatMessageCreate(content="Original question"), "key"
    ) == ("frozen", prior)
    assert not db.added and not db.commits


def test_additive_migration_emits_checked_defaults_for_both_existing_tables():
    path = (
        Path(__file__).parents[2]
        / "backend/alembic/versions/fb2c7e43a910_answer_activation_scope.py"
    )
    spec = spec_from_file_location("answer_scope_migration", path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "fa1b6d3298ef"
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        migration.upgrade()
    sql = output.getvalue()
    for table in ("active_model_configurations", "model_activations"):
        assert (
            f"ALTER TABLE {table} ADD COLUMN activation_scope VARCHAR(24) DEFAULT 'answer_and_checker' NOT NULL"
            in sql
        )
        assert f"ALTER TABLE {table} ADD CONSTRAINT" in sql
    assert sql.count("CHECK (activation_scope IN ('answer_only', 'answer_and_checker'))") == 2
