"""Safe failure classification and recovery copy; synthetic data, no provider I/O."""

from copy import deepcopy
import socket

import pytest

from app.core.errors import safe_message_for
from app.modules.answering.diagnostics import failure_classification_projection
from app.modules.answering import diagnostics, service
from app.modules.answering.models import Answer, Attempt, Evidence
from generation.adapters import LLMAdapter
from generation.types import failure
from sqlalchemy import func, select
from test_retry_hint_capability209 import pending_request
from test_retry_hint_capability209 import scope as scope


@pytest.fixture(autouse=True)
def no_network_or_provider(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Failure diagnostics controls permit only local synthetic data")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(LLMAdapter, "generate", denied)


def test_output_validation_projects_only_known_type_code_and_stage():
    error = {
        "code": "ENHANCEMENT_VALIDATION_ERROR",
        "message": "PRIVATE_PROMPT",
        "details": {
            "error_type": "ValueError",
            "validation_code": "ASSERTION_CITATIONS_MISMATCH",
            "stage": "generation",
            "raw_response": "PRIVATE_DRAFT",
            "api_key": "PRIVATE_KEY",
        },
    }
    before = deepcopy(error)
    result = failure_classification_projection(error).model_dump()
    assert result == {
        "version": "safe_failure_classification_v1",
        "category": "output_validation",
        "stage": "generation",
        "error_type": "ValueError",
        "validation_code": "ASSERTION_CITATIONS_MISMATCH",
    }
    assert "PRIVATE" not in str(result) and error == before


def test_unknown_validation_tokens_and_exception_types_are_not_public_identifiers():
    result = failure_classification_projection(
        {
            "code": "ENHANCEMENT_VALIDATION_ERROR",
            "details": {
                "error_type": "PRIVATE_SECRET",
                "validation_code": "PRIVATE_UPPERCASE_SECRET",
                "stage": "PRIVATE_PROMPT",
                "checker_trace": "PRIVATE_CHECKER",
            },
        }
    ).model_dump()
    assert result["category"] == "output_validation"
    assert result["error_type"] is result["validation_code"] is result["stage"] is None
    assert "PRIVATE" not in str(result)


def test_allowlisted_saved_failure_stage_is_used_without_inventing_terminal_stage():
    error = {"code": "ENHANCEMENT_VALIDATION_ERROR", "details": {}}
    assert failure_classification_projection(error, saved_stage="generation").stage == "generation"
    assert failure_classification_projection(error, saved_stage="failed").stage is None
    assert failure_classification_projection(error, saved_stage=["PRIVATE"]).stage is None


def test_saved_invalid_http200_response_stays_unpublished_and_safely_inspectable(scope):
    Attempt.__table__.create(scope.db.get_bind())
    Evidence.__table__.create(scope.db.get_bind())
    req, job = pending_request(scope)
    req.command = {**req.command, "reliability_policy": "evidence_reliability_v5"}
    job.stage = "generation"
    error = failure(
        "ENHANCEMENT_VALIDATION_ERROR",
        "PRIVATE_PROVIDER_ECHO",
        retryable=False,
        error_type="ValueError",
        validation_code="ASSERTION_CITATIONS_MISMATCH",
        raw_response="PRIVATE_FAILED_ANSWER",
        checker_trace="PRIVATE_CHECKER",
    )
    scope.db.add(
        Attempt(
            job_id=job.id,
            sequence=1,
            payload={
                "stage": "generation",
                "error": error,
                "diagnostic": {"stage": "completed", "http_status": 200, "request_submitted": True},
            },
        )
    )
    service.fail_job(scope.db, job, error)
    scope.db.commit()
    before = deepcopy((req.command, req.trace, job.error))
    detail = diagnostics.failure_detail(scope.db, scope.actor, req.id)
    assert detail.failure_classification.category == "output_validation"
    assert detail.failure_classification.stage == "generation"
    assert detail.failure_classification.validation_code == "ASSERTION_CITATIONS_MISMATCH"
    assert detail.attempts[0].provider_diagnostic.http_status == 200
    assert detail.answer_text is None and service.job_out(scope.db, job)["answer_id"] is None
    assert scope.db.scalar(select(func.count()).select_from(Answer)) == 0
    assert not service.can_retry(scope.db, req)
    assert "PRIVATE" not in detail.model_dump_json()
    assert (req.command, req.trace, job.error) == before


@pytest.mark.parametrize("malformed", [[], {}, True, 123])
def test_malformed_saved_detail_values_are_withheld(malformed):
    result = failure_classification_projection(
        {
            "code": "ENHANCEMENT_VALIDATION_ERROR",
            "details": {"stage": malformed, "error_type": malformed, "validation_code": malformed},
        }
    )
    assert result.stage is result.error_type is result.validation_code is None


@pytest.mark.parametrize(
    ("code", "category"),
    [
        ("CONTEXT_LIMIT", "context_budget"),
        ("SEMANTIC_CHECK_FAILED", "evidence_check"),
        ("CHECKER_INCONSISTENT", "checker_contract"),
        ("SEMANTIC_CHECK_UNAVAILABLE", "checker_unavailable"),
        ("PROVIDER_TIMEOUT", "provider_timeout"),
        ("PROVIDER_NETWORK_ERROR", "provider_connection"),
        ("PROVIDER_HTTP_ERROR", "provider_rejection"),
        ("MODEL_UNAVAILABLE", "configuration"),
        ("BUDGET_EXHAUSTED", "budget_exhausted"),
        ("SAVED_UNKNOWN_FAILURE", "unclassified"),
    ],
)
def test_classification_does_not_invent_recovery_eligibility(code, category):
    value = failure_classification_projection({"code": code, "details": {"retryable": True}})
    assert value.category == category
    assert "retryable" not in value.model_dump() and "action" not in value.model_dump()


@pytest.mark.parametrize("value", [None, {}, {"message": "PRIVATE"}, []])
def test_missing_error_has_no_invented_classification(value):
    assert failure_classification_projection(value) is None


@pytest.mark.parametrize(
    "code",
    [
        "SEMANTIC_CHECK_FAILED",
        "SEMANTIC_CHECK_UNAVAILABLE",
        "CHECKER_INCONSISTENT",
        "PROVIDER_NETWORK_ERROR",
        "RETRY_NOT_ALLOWED",
    ],
)
def test_catalog_does_not_offer_unconditional_retry_or_blind_send(code):
    message = safe_message_for(code).lower()
    assert "retry" not in message and "send a new" not in message


def test_enhancement_validation_has_specific_safe_guidance():
    message = safe_message_for("ENHANCEMENT_VALIDATION_ERROR")
    assert "source mapping" in message.lower()
    assert "unexpected" not in message.lower()
