"""Positive recovery proof over saved synthetic requests, without provider I/O."""

from copy import deepcopy
import socket

import pytest
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.modules.answering import service
from app.modules.answering.models import Attempt, Job
from app.modules.answering.recovery import command_hash
from generation.adapters import LLMAdapter
from generation.stage_budget_v1 import window_failure
from generation.types import ModelConfig
from generation.types import RequestBudget, failure
from test_retry_hint_capability209 import pending_request
from test_retry_hint_capability209 import scope as scope


@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Positive retry controls allow only local synthetic data")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(LLMAdapter, "generate", denied)


@pytest.mark.parametrize("code", ["SAVED_UNKNOWN_FAILURE", "INTERNAL_ERROR", "WORKER_INTERRUPTED"])
def test_unknown_failure_with_remaining_budget_does_not_gain_retry(scope, code):
    req, job = pending_request(scope)
    service.fail_job(scope.db, job, {"code": code, "message": "Synthetic", "details": {}})
    scope.db.commit()
    before = deepcopy((req.command, req.trace, req.budget, job.error))
    assert req.budget["consumed_calls"] < req.budget["max_calls"]
    assert not service.can_retry(scope.db, req)
    assert service.job_out(scope.db, job)["can_retry"] is False
    with pytest.raises(AppError, match="RETRY_NOT_ALLOWED"):
        service.retry(scope.db, scope.actor, req.id, "no-positive-proof")
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 1
    assert (req.command, req.trace, req.budget, job.error) == before


@pytest.mark.parametrize("marker", ["uncertain", "uncertain_external_execution"])
@pytest.mark.parametrize(
    "code", ["PROVIDER_TIMEOUT", "PROVIDER_NETWORK_ERROR", "PROVIDER_HTTP_ERROR"]
)
def test_uncertain_provider_outcome_overrides_explicit_positive_and_transient_code(
    scope, marker, code
):
    req, job = pending_request(scope, budget=RequestBudget(consumed_calls=1).to_dict())
    service.fail_job(
        scope.db, job, failure(code, "Synthetic uncertainty", retryable=True, **{marker: True})
    )
    scope.db.commit()
    assert not service.can_retry(scope.db, req)
    assert req.trace["failure_recovery"]["reason"] == "uncertain_provider_outcome"
    assert req.trace["failure_recovery"]["new_request_required"] is False
    with pytest.raises(AppError, match="RETRY_NOT_ALLOWED"):
        service.retry(scope.db, scope.actor, req.id, "do-not-duplicate")


@pytest.mark.parametrize(
    "error",
    [
        {"code": "PROVIDER_RATE_LIMITED", "message": "Synthetic known transient", "details": {}},
        failure("PROVIDER_HTTP_ERROR", "Synthetic429 receipt", retryable=True, http_status=429),
        failure("PROVIDER_HTTP_ERROR", "Synthetic503 receipt", retryable=True, http_status=503),
        failure("SAVED_UNKNOWN_FAILURE", "Explicit recoverable outcome", retryable=True),
    ],
)
def test_positive_contract_remains_bounded_idempotent_and_immutable(scope, error):
    req, job = pending_request(scope, budget=RequestBudget(consumed_calls=1).to_dict())
    service.fail_job(scope.db, job, error)
    scope.db.commit()
    before = deepcopy((req.command, req.budget))
    assert req.trace["failure_recovery"]["command_sha256"] == command_hash(req.command)
    assert service.can_retry(scope.db, req)
    receipt = service.retry(scope.db, scope.actor, req.id, "one-retry")
    assert service.retry(scope.db, scope.actor, req.id, "one-retry") == receipt
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 2
    assert not service.can_retry(scope.db, req)
    assert (req.command, req.budget) == before


def test_changed_command_cannot_rebind_previous_positive_recovery(scope):
    req, job = pending_request(scope)
    service.fail_job(
        scope.db,
        job,
        failure("PROVIDER_HTTP_ERROR", "Synthetic429", retryable=True, http_status=429),
    )
    scope.db.commit()
    req.command = {**req.command, "question": "Changed frozen inputs"}
    scope.db.commit()
    assert not service.can_retry(scope.db, req)


def test_proven_initial_overflow_overrides_conflicting_positive_flag(scope):
    req, job = pending_request(scope)
    error = window_failure("generation", ModelConfig(), 20000)
    error["retryable"] = True
    service.fail_job(scope.db, job, error)
    scope.db.commit()
    assert not service.can_retry(scope.db, req)
    assert req.trace["failure_recovery"]["reason"] == "frozen_context_limit"
    assert req.trace["failure_recovery"]["new_request_required"] is True


@pytest.mark.parametrize(
    "error",
    [
        None,
        {"code": "SAVED_UNKNOWN_FAILURE", "details": {}},
        failure("PROVIDER_TIMEOUT", "Legacy uncertain", retryable=True, uncertain=True),
    ],
)
def test_older_positive_trace_does_not_override_missing_or_unclassified_latest_failure(
    scope, error
):
    req, job = pending_request(scope)
    service.fail_job(
        scope.db,
        job,
        failure("PROVIDER_HTTP_ERROR", "Synthetic429", retryable=True, http_status=429),
    )
    job.error = error
    scope.db.commit()
    assert not service.can_retry(scope.db, req)


def test_unclassified_legacy_cancelled_request_is_not_recoverable_from_budget_alone(scope):
    req, job = pending_request(scope)
    req.state, job.state, job.stage, job.execution_token = (
        "cancelled",
        "cancelled",
        "cancelled",
        None,
    )
    scope.db.commit()
    assert not service.can_retry(scope.db, req)


@pytest.mark.parametrize("state", ["queued", "running"])
def test_cancellation_records_safe_positive_only_before_any_provider_work(scope, state):
    Attempt.__table__.create(scope.db.get_bind())
    req, job = pending_request(scope)
    req.state = job.state = state
    job.stage = "queued" if state == "queued" else "generation"
    service.cancel_job(scope.db, job)
    scope.db.commit()
    assert service.can_retry(scope.db, req) is (state == "queued")
    assert job.error["details"]["retryable"] is (state == "queued")
    assert req.trace["failure_recovery"]["command_sha256"] == command_hash(req.command)


def test_queued_cancellation_with_existing_attempt_is_not_mislabeled_predispatch(scope):
    Attempt.__table__.create(scope.db.get_bind())
    req, job = pending_request(scope)
    req.state = job.state = "queued"
    scope.db.add(
        Attempt(job_id=job.id, sequence=1, payload={"phase": "start", "stage": "generation"})
    )
    scope.db.flush()
    service.cancel_job(scope.db, job)
    scope.db.commit()
    assert not service.can_retry(scope.db, req)


@pytest.mark.parametrize("previous_work", ["budget", "worker_attempt"])
def test_queued_cancellation_requires_both_unused_budget_and_never_started_job(
    scope, previous_work
):
    Attempt.__table__.create(scope.db.get_bind())
    req, job = pending_request(scope)
    req.state = job.state = "queued"
    if previous_work == "budget":
        req.budget = RequestBudget(consumed_calls=1).to_dict()
    else:
        job.attempts = 1
    service.cancel_job(scope.db, job)
    scope.db.commit()
    assert not service.can_retry(scope.db, req)
    assert job.error["details"]["retryable"] is False
