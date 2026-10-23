"""Ordinary checker and bounded manual recovery contracts; no external calls."""

from copy import deepcopy
from pathlib import Path
import socket

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job
from app.modules.answering.recovery import failure_recovery
from contracts.models import ChatMessageCreate
from generation import checker_claim_spans_v1 as checker
from generation.adapters import LLMAdapter
from generation.types import RequestBudget, failure
from test_retry_hint_capability209 import pending_request
from test_retry_hint_capability209 import scope as scope


@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    attempted = []

    def denied(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("Continuation tests allow only in-memory SQLite")

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(LLMAdapter, "_call", denied)
    root = Path(__file__).parents[2].resolve()
    assert Path(service.__file__).resolve().is_relative_to(root)
    yield
    assert not attempted


def test_actual_default_on_freezes_original_checker_without_disabling_verification(scope):
    body = ChatMessageCreate(content="Explain diffusion.", check_answer=True)
    receipt = service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "ordinary")
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    assert Settings.model_fields["chat_checker_claim_policy"].default is None
    assert req.command["checker_claim_policy"] is None
    assert req.command["joint_checker_policy"] == "typed_joint_v5"
    assert req.command["check_requested"] is True
    assert req.command["requested_check_answer"] is True
    assert req.command["verification_mode"] == "verified"
    assert req.command["checker_config"] is not None
    assert req.command["repair_policy"] == "claim_patch_repair_v3"
    assert checker.validate_request(type("Frozen", (), {"checker_claim_policy": None})()) is False
    frozen = deepcopy(req.command)
    scope.settings.chat_checker_claim_policy = "asserted_support_anchors_v3"
    assert (
        service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "ordinary")
        == receipt
    )
    assert req.command == frozen
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 1


def test_actual_off_choice_stays_fast_and_does_not_create_a_checker(scope):
    body = ChatMessageCreate(content="Explain diffusion.", check_answer=False)
    receipt = service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "off")
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    assert req.command["verification_mode"] == "fast"
    assert req.command["check_requested"] is False
    assert req.command["requested_check_answer"] is False
    assert req.command["checker_config"] is None
    assert req.command["checker_claim_policy"] is None


@pytest.mark.parametrize("code", ["CHECKER_INCONSISTENT", "ENHANCEMENT_VALIDATION_ERROR"])
def test_saved_explicit_false_rejects_manual_retry_without_claiming_fixed_input(scope, code):
    req, job = pending_request(scope)
    error = failure(code, "Synthetic rejected output", retryable=False)
    before = deepcopy(error)
    service.fail_job(scope.db, job, error)
    scope.db.commit()
    frozen, budget = deepcopy(req.command), deepcopy(req.budget)
    assert job.error["details"]["retryable"] is False
    assert req.trace["failure_recovery"]["reason"] == "non_retryable_failure"
    assert req.trace["failure_recovery"]["new_request_required"] is False
    assert not service.can_retry(scope.db, req)
    assert service.job_out(scope.db, job)["can_retry"] is False
    with pytest.raises(AppError, match="RETRY_NOT_ALLOWED"):
        service.retry(scope.db, scope.actor, req.id, "blocked")
    assert req.command == frozen and req.budget == budget and error == before
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 1


def test_old_false_with_unclassified_recovery_is_projected_without_history_mutation(scope):
    req, job = pending_request(scope)
    req.state, job.state = "error", "failed"
    job.error = {
        "code": "CHECKER_INCONSISTENT",
        "message": "Saved old failure",
        "details": {"retryable": False},
    }
    req.trace = {
        "failure_recovery": failure_recovery(
            {"code": "CHECKER_INCONSISTENT", "details": {}}, req.command
        )
    }
    assert req.trace["failure_recovery"]["retryable"] is None
    scope.db.commit()
    before = deepcopy((req.command, req.trace, job.error))
    assert service.job_out(scope.db, job)["can_retry"] is False
    assert not service.can_retry(scope.db, req)
    assert (req.command, req.trace, job.error) == before


def test_explicit_positive_legacy_flag_keeps_budget_and_session_eligibility(scope):
    req, job = pending_request(scope)
    error = {"code": "SAVED_UNKNOWN_FAILURE", "message": "Synthetic", "details": {}}
    error["retryable"] = True
    service.fail_job(scope.db, job, error)
    scope.db.commit()
    assert service.can_retry(scope.db, req)
    assert req.trace["failure_recovery"]["retryable"] is True
    req.budget = RequestBudget(consumed_calls=4).to_dict()
    scope.db.commit()
    assert not service.can_retry(scope.db, req)
    req.budget = RequestBudget().to_dict()
    scope.db.get(service.ChatSession, "chat").status = "archived"
    scope.db.commit()
    assert not service.can_retry(scope.db, req)


def test_conflicting_explicit_false_is_not_overwritten_by_transient_true(scope):
    req, job = pending_request(scope)
    error = {
        "code": "PROVIDER_TIMEOUT",
        "message": "Synthetic conflict",
        "retryable": True,
        "details": {"retryable": False},
    }
    service.fail_job(scope.db, job, error)
    scope.db.commit()
    assert job.error["details"]["retryable"] is False
    assert req.trace["failure_recovery"]["retryable"] is False
    assert not service.can_retry(scope.db, req)


def test_unknown_falsey_legacy_values_are_not_invented_boolean_denials():
    for value in (None, 0, "false"):
        recovery = failure_recovery(
            {"code": "SAVED_UNKNOWN_FAILURE", "details": {"retryable": value}}, {}
        )
        assert recovery["retryable"] is None and not recovery["new_request_required"]
