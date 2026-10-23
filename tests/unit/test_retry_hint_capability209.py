"""Native SQLite submission/retry and effective hint prerequisites; no model I/O."""

from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace
import socket

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401
from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.administration.router import capabilities
from app.modules.answering import service
from app.modules.answering.hint_capability import hint_capability
from app.modules.answering.models import (
    Answer,
    AnswerRequest,
    Job,
    Message,
    Snapshot,
    SessionSummary,
)
from app.modules.answering.recovery import failure_recovery, prevents_retry
from app.modules.experiment.models import ExperimentRun
from app.modules.identity.models import Role, User, Workspace, StudentProfile
from app.modules.knowledge.models import ActiveCorpus
from app.modules.learning.models import ChatSession
from app.modules.learning_state.models import (
    LearningTask,
    LearningExposure,
    AnswerPresentation,
    MemorySettings,
    PrivateAnswerDraft,
)
from app.modules.model_settings.models import (
    ActiveModelConfiguration,
    ModelConfiguration,
    ModelCredential,
)
from app.platform_core.models import OutboxEvent
from contracts.http import CapabilitiesOut
from contracts.models import ChatMessageCreate, JobOut
from generation.adapters import LLMAdapter
from generation.service import GenerationService
from generation.stage_budget_v1 import window_failure
from generation.token_counting import TokenCounter
from generation.types import GenerationRequest, ModelConfig, RequestBudget, failure


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempts = []

    def denied(*args, **kwargs):
        attempts.append("external_io")
        raise AssertionError("Retry/hint regressions allow only in-memory SQLite and local code")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(LLMAdapter, "generate", denied)
    yield
    assert attempts == []


@pytest.fixture
def scope():
    engine = create_engine("sqlite:///:memory:")
    for model in (
        Workspace,
        Role,
        User,
        StudentProfile,
        ChatSession,
        Message,
        Snapshot,
        SessionSummary,
        AnswerRequest,
        Job,
        Answer,
        MemorySettings,
        LearningTask,
        LearningExposure,
        AnswerPresentation,
        PrivateAnswerDraft,
        ActiveModelConfiguration,
        ModelConfiguration,
        ModelCredential,
        ActiveCorpus,
        ExperimentRun,
        OutboxEvent,
    ):
        model.__table__.create(engine)
    db = Session(engine, autoflush=False, expire_on_commit=False)
    db.add_all(
        [
            Workspace(id="workspace", name="Synthetic", slug="synthetic"),
            Role(id=1, name="student"),
            User(
                id="owner",
                email="owner@fixture.invalid",
                hashed_password="unused",
                role_id=1,
                workspace_id="workspace",
            ),
            ChatSession(id="chat", user_id="owner", workspace_id="workspace", title="Synthetic"),
            MemorySettings(owner_id="owner", enabled=False),
        ]
    )
    db.commit()
    value = SimpleNamespace(
        db=db,
        actor=db.get(User, "owner"),
        settings=Settings(
            _env_file=None,
            env="test",
            model_mode="mock",
            llm_provider="mock",
            llm_api_key=None,
            mock_delay_seconds=0,
            jwt_secret="synthetic-retry-hint-fixture-secret-only",
        ),
    )
    yield value
    db.close()
    engine.dispose()


def pending_request(scope, **changes):
    db = scope.db
    message = Message(
        id="message",
        session_id="chat",
        sequence=1,
        role="user",
        content="Synthetic question",
        state="queued",
    )
    req = AnswerRequest(
        id="request",
        owner_id="owner",
        route="/sessions/chat/messages",
        idempotency_key="original",
        body_hash="synthetic",
        mode="interactive_chat",
        response_schema="chat_response_v1",
        session_id="chat",
        user_message_id="message",
        command={"question": "Synthetic question", "model_config": ModelConfig().to_dict()},
        budget=RequestBudget().to_dict(),
        trace={},
        state="processing",
    )
    for key, value in changes.items():
        setattr(req, key, value)
    job = Job(
        id="job",
        request_id="request",
        owner_id="owner",
        state="running",
        stage="generating",
        execution_token="synthetic-execution",
    )
    db.add_all([message, req, job])
    db.commit()
    return req, job


def save_checker(scope, config):
    row = ModelConfiguration(
        id="checker",
        workspace_id="workspace",
        group_id="checker-group",
        revision=1,
        name="Synthetic independent checker",
        preset="custom",
        public_config=config.to_dict(),
        config_hash="synthetic",
        created_by="owner",
    )
    answer = ModelConfiguration(
        id="answer",
        workspace_id="workspace",
        group_id="answer-group",
        revision=1,
        name="Synthetic mock answer",
        preset="mock",
        public_config=ModelConfig().to_dict(),
        config_hash="synthetic",
        created_by="owner",
    )
    scope.db.add_all(
        [
            row,
            answer,
            ActiveModelConfiguration(
                workspace_id="workspace",
                configuration_id="answer",
                checker_configuration_id="checker",
                version=1,
            ),
        ]
    )
    scope.db.commit()


def test_initial_context_failure_persists_recovery_and_rejects_retry_without_a_new_job(scope):
    req, job = pending_request(scope)
    command = deepcopy(req.command)
    budget = deepcopy(req.budget)
    error = window_failure("generation", ModelConfig(), 16636)
    service.fail_job(scope.db, job, error)
    scope.db.commit()
    scope.db.expire_all()
    req = scope.db.get(AnswerRequest, "request")
    job = scope.db.get(Job, "job")
    assert job.error["details"]["retryable"] is False
    recovery = job.error["details"]["recovery"]
    assert recovery == req.trace["failure_recovery"]
    assert recovery["reason"] == "frozen_context_limit"
    assert recovery["new_request_required"] and recovery["retryable"] is False
    assert not service.can_retry(scope.db, req)
    assert not JobOut.model_validate(service.job_out(scope.db, job)).can_retry
    for key in ("retry-1", "retry-2", "retry-3"):
        with pytest.raises(AppError, match="RETRY_NOT_ALLOWED"):
            service.retry(scope.db, scope.actor, req.id, key)
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 1
    assert req.command == command and req.budget == budget
    assert error["details"].get("recovery") is None


def test_legacy_numeric_context_failure_is_read_without_mutating_old_records(scope):
    req, job = pending_request(scope)
    req.state = "error"
    job.state = "failed"
    error = window_failure("generation", ModelConfig(), 16636)
    error.pop("retryable")
    error["details"].pop("diagnostic_version")
    job.error = error
    scope.db.commit()
    old_command, old_error, old_trace = (
        deepcopy(req.command),
        deepcopy(job.error),
        deepcopy(req.trace),
    )
    assert not service.can_retry(scope.db, req)
    assert req.command == old_command and req.trace == old_trace and job.error == old_error


@pytest.mark.parametrize(
    "code",
    [
        "PROVIDER_TIMEOUT",
        "PROVIDER_NETWORK_ERROR",
        "PROVIDER_RATE_LIMITED",
    ],
)
def test_transient_retry_stays_bounded_idempotent_and_preserves_frozen_settings(scope, code):
    req, job = pending_request(scope, budget=RequestBudget(consumed_calls=1).to_dict())
    command, budget = deepcopy(req.command), deepcopy(req.budget)
    service.fail_job(scope.db, job, failure(code, "Synthetic transient failure", retryable=True))
    scope.db.commit()
    assert service.can_retry(scope.db, req)
    result = service.retry(scope.db, scope.actor, req.id, "retry-once")
    assert result == service.retry(scope.db, scope.actor, req.id, "retry-once")
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 2
    assert req.command == command and req.budget == budget
    assert not service.can_retry(scope.db, req)  # The new job is already active.


@pytest.mark.parametrize("stage", ["joint_check", "generation_format_repair", "semantic_repair"])
def test_generated_stage_limit_is_not_misrepresented_as_fixed_initial_input(scope, stage):
    req, job = pending_request(scope)
    service.fail_job(scope.db, job, window_failure(stage, ModelConfig(), 16636))
    scope.db.commit()
    assert req.trace["failure_recovery"]["retryable"] is False
    assert req.trace["failure_recovery"]["reason"] == "non_retryable_failure"
    assert req.trace["failure_recovery"]["new_request_required"] is False
    assert not service.can_retry(scope.db, req)


@pytest.mark.parametrize(
    "change",
    [
        {"stage": "unknown"},
        {"input_reserved_tokens": 1},
        {"window_tokens": 32768},
        {"input_reserved_tokens": True},
        {"blocked_attempt_request_submitted": True},
    ],
)
def test_incomplete_or_different_budget_proof_does_not_fabricate_a_permanent_failure(change):
    error = window_failure("generation", ModelConfig(), 16636)
    error["details"].update(change)
    recovery = failure_recovery(error, {"model_config": ModelConfig().to_dict()})
    assert recovery["retryable"] is False and recovery["reason"] == "non_retryable_failure"
    assert recovery["new_request_required"] is False


def test_recovery_provenance_is_bound_to_the_original_command():
    command = {"model_config": ModelConfig().to_dict(), "question": "Synthetic"}
    recovery = failure_recovery(window_failure("generation", ModelConfig(), 16636), command)
    revised = deepcopy(command)
    revised["model_config"]["window_tokens"] = 32768
    assert prevents_retry(recovery, command)
    assert not prevents_retry(recovery, revised)
    assert command["model_config"]["window_tokens"] == 16384


def test_no_unstructured_context_message_is_parsed_as_proof():
    error = failure("CONTEXT_LIMIT", "Transient timeout text is not a numeric budget proof")
    recovery = failure_recovery(error, {"model_config": ModelConfig().to_dict()})
    assert recovery["reason"] == "non_retryable_failure" and not recovery["new_request_required"]


def test_mock_checker_capability_and_native_explicit_hint_rejection_create_no_work(scope):
    status = hint_capability(scope.db, scope.settings, "workspace")
    assert status["hint_ready"] is False and "demo checker" in status["hint_unavailable_reason"]
    body = ChatMessageCreate(
        content="Synthetic new problem",
        teaching_mode="hint",
        task_action="new",
        answer_mode="general_knowledge",
        check_answer=False,
    )
    with pytest.raises(AppError, match="semantic checker"):
        service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "unsupported")
    for model in (Message, Snapshot, LearningTask, AnswerRequest, Job):
        assert scope.db.scalar(select(func.count()).select_from(model)) == 0
    assert body.check_answer is False


def test_effective_independent_checker_can_support_hints_with_mock_answer(scope):
    checker = ModelConfig(
        provider="local", model="synthetic-local-checker", base_url="http://127.0.0.1:19999/v1"
    )
    save_checker(scope, checker)
    status = hint_capability(scope.db, scope.settings, "workspace")
    assert status == {"hint_ready": True, "hint_unavailable_reason": None}
    body = ChatMessageCreate(
        content="Synthetic new problem",
        teaching_mode="hint",
        task_action="new",
        answer_mode="general_knowledge",
        check_answer=False,
    )
    receipt = service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "hint-ready")
    request = scope.db.get(AnswerRequest, receipt["request_id"])
    assert request.command["requested_check_answer"] is False
    assert request.command["verification_mode"] == "verified"
    assert request.command["verification_policy"] == "mandatory_teaching_or_protocol_v1"
    assert request.command["checker_config"]["configuration_id"] == "model-settings:checker"
    assert request.command["model_config"]["provider"] == "mock"
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 1


@pytest.mark.parametrize(
    "checker",
    [
        ModelConfig(
            provider="openai", model="synthetic-checker", base_url="https://example.invalid/v1"
        ),
        ModelConfig(provider="local", model="synthetic-checker", base_url="http://192.168.1.1/v1"),
        ModelConfig(
            provider="local",
            model="synthetic-checker",
            base_url="http://127.0.0.1/v1",
            max_tokens=4096,
            window_tokens=2048,
            capability_version="unsupported",
        ),
    ],
)
def test_missing_checker_credentials_or_invalid_prerequisites_are_unavailable(scope, checker):
    save_checker(scope, checker)
    status = hint_capability(scope.db, scope.settings, "workspace")
    assert not status["hint_ready"] and status["hint_unavailable_reason"]


def test_native_ordinary_check_off_does_not_require_or_enable_checker(scope):
    body = ChatMessageCreate(
        content="Synthetic ordinary question",
        teaching_mode="direct",
        task_action="new",
        answer_mode="general_knowledge",
        check_answer=False,
    )
    receipt = service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "ordinary")
    request = scope.db.get(AnswerRequest, receipt["request_id"])
    assert request.command["verification_mode"] == "fast"
    assert request.command["requested_check_answer"] is False
    assert request.command["check_requested"] is False
    assert request.command["checker_config"] is None


def test_actual_capabilities_projection_includes_independent_hint_status(scope):
    result = capabilities(
        flags=SimpleNamespace(as_dict=lambda: {}),
        actor=scope.actor,
        db=scope.db,
        settings=scope.settings,
    )
    status = CapabilitiesOut.model_validate(result["data"])
    assert not status.hint_ready and status.hint_unavailable_reason
    assert status.model_mode == "mock"
    assert "No active corpus" in status.missing_reasons["chat"][0]


def test_capability_change_is_rechecked_at_native_submission(scope):
    checker = ModelConfig(
        provider="local", model="synthetic-checker", base_url="http://127.0.0.1/v1"
    )
    save_checker(scope, checker)
    assert hint_capability(scope.db, scope.settings, "workspace")["hint_ready"]
    pointer = scope.db.get(ActiveModelConfiguration, "workspace")
    pointer.checker_configuration_id = "answer"  # A new effective mock checker.
    scope.db.commit()
    body = ChatMessageCreate(
        content="Synthetic new problem",
        teaching_mode="hint",
        task_action="new",
        answer_mode="general_knowledge",
        check_answer=False,
    )
    with pytest.raises(AppError, match="semantic checker"):
        service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "changed")
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 0
    assert scope.db.scalar(select(func.count()).select_from(AnswerRequest)) == 0


def test_native_long_question_generation_failure_and_new_config_use_new_request(scope):
    body = ChatMessageCreate(
        content="\u4e2d" * 4000,
        teaching_mode="direct",
        task_action="new",
        answer_mode="general_knowledge",
        check_answer=False,
    )
    receipt = service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "old-window")
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    job = scope.db.get(Job, receipt["job_id"])
    original = deepcopy(req.command)
    names = {field.name for field in fields(GenerationRequest)}
    inputs = {key: value for key, value in req.command.items() if key in names}
    inputs.update(
        request_id=req.id, mode=req.mode, config=ModelConfig.from_dict(req.command["model_config"])
    )
    result = GenerationService().generate(GenerationRequest(**inputs), RequestBudget())
    assert result.error["code"] == "CONTEXT_LIMIT", result.error
    assert result.budget["consumed_calls"] == 0
    assert result.error["details"]["stage"] == "generation"
    service.fail_job(scope.db, job, result.error)
    scope.db.commit()
    assert not service.can_retry(scope.db, req)
    scope.settings.model_window_tokens = 32768
    with pytest.raises(AppError, match="RETRY_NOT_ALLOWED"):
        service.retry(scope.db, scope.actor, req.id, "same-frozen-input")
    fresh = service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "new-window")
    fresh_req = scope.db.get(AnswerRequest, fresh["request_id"])
    assert fresh_req.command["model_config"]["window_tokens"] == 32768
    assert req.command == original and req.command["model_config"]["window_tokens"] == 16384


def test_implicit_hint_is_rejected_before_enqueue_and_transaction_rollback_preserves_input(scope):
    body = ChatMessageCreate(
        content="Give me a hint for this synthetic problem",
        task_action="new",
        answer_mode="general_knowledge",
        check_answer=False,
    )
    with pytest.raises(AppError, match="semantic checker"):
        service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "implicit-hint")
    for model in (AnswerRequest, Job):
        assert scope.db.scalar(select(func.count()).select_from(model)) == 0
    scope.db.rollback()
    for model in (Message, Snapshot, LearningTask):
        assert scope.db.scalar(select(func.count()).select_from(model)) == 0
    assert body.check_answer is False and body.content.startswith("Give me a hint")


def test_checker_without_any_input_window_is_unavailable_even_for_legacy_capabilities(scope):
    checker = ModelConfig(
        provider="local",
        model="synthetic-checker",
        base_url="http://127.0.0.1/v1",
        window_tokens=2048,
    )
    save_checker(scope, checker)
    assert not hint_capability(scope.db, scope.settings, "workspace")["hint_ready"]


def test_unavailable_required_local_checker_tokenizer_is_not_ready(scope):
    absent = Path(__file__).parent / "unavailable-tokenizer209"
    assert not absent.exists()
    checker = ModelConfig(
        provider="local",
        model="synthetic-checker",
        base_url="http://127.0.0.1/v1",
        tokenizer_provider="huggingface",
        tokenizer_local_path=str(absent),
        token_count_fallback="error",
    )
    save_checker(scope, checker)
    status = hint_capability(scope.db, scope.settings, "workspace")
    assert not status["hint_ready"] and status["hint_unavailable_reason"]


def test_environment_local_checker_retains_optional_transport_credentials(scope):
    scope.settings.model_mode = "live"
    scope.settings.llm_provider = "local"
    scope.settings.llm_model = "synthetic-local-checker"
    scope.settings.llm_api_base = "http://127.0.0.1:19999/v1"
    assert scope.settings.llm_api_key is None
    status = hint_capability(scope.db, scope.settings, "workspace")
    assert status == {"hint_ready": True, "hint_unavailable_reason": None}


def test_unsupported_required_provider_counter_rejects_hint_before_any_work(scope):
    checker = ModelConfig(
        provider="local",
        model="synthetic-local-checker",
        base_url="http://127.0.0.1:19999/v1",
        tokenizer_provider="provider",
        token_count_fallback="error",
        max_tokens=4096,
    )
    # Constructor success is only an estimate; checked.invoke would reject it.
    assert TokenCounter(checker).report()["is_estimate"]
    save_checker(scope, checker)
    status = hint_capability(scope.db, scope.settings, "workspace")
    assert not status["hint_ready"] and status["hint_unavailable_reason"]
    body = ChatMessageCreate(
        content="Synthetic new problem",
        teaching_mode="hint",
        task_action="new",
        answer_mode="general_knowledge",
        check_answer=False,
    )
    with pytest.raises(AppError, match="semantic checker"):
        service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "bad-counter")
    for model in (Message, Snapshot, LearningTask, AnswerRequest, Job):
        assert scope.db.scalar(select(func.count()).select_from(model)) == 0


def test_unsupported_native_counter_retains_explicit_estimate_fallback(scope):
    checker = ModelConfig(
        provider="local",
        model="synthetic-local-checker",
        base_url="http://127.0.0.1:19999/v1",
        tokenizer_provider="provider",
        token_count_fallback="estimate",
        max_tokens=4096,
    )
    save_checker(scope, checker)
    assert hint_capability(scope.db, scope.settings, "workspace")["hint_ready"]


@pytest.mark.parametrize("provider", ["anthropic", "gemini"])
def test_supported_native_counter_protocol_is_not_falsely_disabled(scope, provider):
    checker = ModelConfig(
        provider=provider,
        model="synthetic-native-checker",
        base_url="https://example.invalid/v1",
        tokenizer_provider="provider",
        token_count_fallback="error",
        max_tokens=4096,
    )
    scope.settings.llm_api_key = "synthetic-credential-not-a-real-key"
    status = hint_capability(
        scope.db,
        scope.settings,
        "workspace",
        answer_config=ModelConfig(),
        checker_config=checker,
    )
    assert status == {"hint_ready": True, "hint_unavailable_reason": None}
