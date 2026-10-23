"""Actual prompt assembly through checked failure and durable retry consumption."""

from copy import deepcopy
from dataclasses import replace
import json

import pytest
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job, Message
from app.modules.answering.recovery import failure_recovery
from contracts.models import JobOut
from generation.parser import ResponseValidationError
from generation.prompt_builder import build_messages
from generation.service import GenerationService
from generation.token_counting import TokenCounter
from generation.types import GenerationRequest, ModelConfig
from tests.unit.test_retry_hint_capability209 import (
    no_external_io as no_external_io,
    pending_request,
    scope as scope,
)


def initial_request():
    return GenerationRequest(
        request_id="actual-prompt-overflow",
        mode="interactive_chat",
        condition="E1",
        question=chr(0x1F9EC) * 4000,
        answer_mode="general_knowledge",
        config=ModelConfig(window_tokens=8192, tokenizer_provider="estimate"),
        enhancement_version="learning_enhancement_v1",
        reliability_policy="evidence_reliability_v5",
        teaching_context={"teaching_mode": "direct", "help_level": 0, "turn_role": "user_question"},
        verification_mode="fast",
    )


def actual_pipeline_outcome(request):
    events = []
    output = GenerationService(api_key=None, checker_api_key=None).generate(
        request, on_attempt=events.append
    )
    assert events == [] and output.attempts == []
    assert output.budget["consumed_calls"] == 0
    return output


def test_actual_prompt_builder_to_checked_preserves_computed_initial_overflow():
    request = initial_request()
    _, _, measured, _ = build_messages(
        replace(request, config=replace(request.config, window_tokens=1_000_000))
    )
    original = deepcopy(request)
    with pytest.raises(ResponseValidationError) as raised:
        build_messages(request)
    assert raised.value.code == "CONTEXT_LIMIT"
    output = actual_pipeline_outcome(request)
    details = output.error["details"]
    assert details["stage"] == "generation"
    assert details["input_reserved_tokens"] == measured["input_reserved_tokens"]
    assert details["output_reserved_tokens"] == measured["output_reserved_tokens"] == 1024
    assert details["window_tokens"] == 8192
    assert details["total_reserved_tokens"] == measured["total_reserved_tokens"]
    assert details["overflow_tokens"] == measured["total_reserved_tokens"] - 8192
    assert details["blocked_attempt_request_submitted"] is False
    assert details["provenance"] == "initial_prompt_assembly_v1"
    assert details["counter_source"] == "unicode_character_estimate_v1"
    assert details["whole_request_is_estimate"] is True
    assert request == original
    assert request.question not in json.dumps(output.error, ensure_ascii=False)


def assert_durable_retry_rejection(scope, request, output):
    req, job = pending_request(
        scope,
        command={
            "question": request.question,
            "model_config": request.config.to_dict(),
            "requested_check_answer": False,
        },
    )
    scope.db.get(Message, "message").content = request.question
    command, budget = deepcopy(req.command), deepcopy(req.budget)
    service.fail_job(scope.db, job, output.error)
    scope.db.commit()
    scope.db.expire_all()
    req, job = scope.db.get(AnswerRequest, "request"), scope.db.get(Job, "job")
    assert job.error["details"]["recovery"] == req.trace["failure_recovery"]
    assert req.trace["failure_recovery"]["reason"] == "frozen_context_limit"
    assert not service.can_retry(scope.db, req)
    assert not JobOut.model_validate(service.job_out(scope.db, job)).can_retry
    for identity in ("first-identical-retry", "second-identical-retry"):
        with pytest.raises(AppError, match="RETRY_NOT_ALLOWED"):
            service.retry(scope.db, scope.actor, req.id, identity)
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 1
    assert req.command == command and req.budget == budget


def test_actual_pipeline_failure_persists_and_native_retry_consumer_rejects_it(scope):
    request = initial_request()
    assert_durable_retry_rejection(scope, request, actual_pipeline_outcome(request))


def test_native_4000_dna_default_limits_use_verified_offline_counter_and_durable_rejection(scope):
    # The focused runner supplies the existing released public cache read-only.
    # Do not fall back to a different count while claiming the native shape.
    request = replace(initial_request(), config=ModelConfig())
    counter = TokenCounter(request.config).report()
    assert counter["source"] == "tiktoken" and counter["name"] == "cl100k_base"
    assert len(request.question) == 4000 and len(request.question.encode("utf-16-le")) // 2 == 8000
    output = actual_pipeline_outcome(request)
    details = output.error["details"]
    assert details["window_tokens"] == 16384 and details["output_reserved_tokens"] == 1024
    assert details["input_reserved_tokens"] + 1024 > 16384
    assert details["counter_source"] == "tiktoken" and details["counter_is_estimate"] is True
    assert_durable_retry_rejection(scope, request, output)


def test_bare_context_error_with_untrusted_text_does_not_gain_numeric_proof(monkeypatch):
    from generation import checked

    def bare(*args, **kwargs):
        raise ResponseValidationError(
            "CONTEXT_LIMIT", "untrusted secret text: input=999999 window=1"
        )

    monkeypatch.setattr(checked, "build_messages", bare)
    request = initial_request()
    output = actual_pipeline_outcome(request)
    assert output.error["code"] == "CONTEXT_LIMIT"
    assert "untrusted secret" not in json.dumps(output.error)
    assert "input_reserved_tokens" not in output.error["details"]
    recovery = failure_recovery(output.error, {"model_config": request.config.to_dict()})
    assert recovery["reason"] == "non_retryable_failure" and recovery["retryable"] is False
    assert recovery["new_request_required"] is False
    assert recovery["provenance"] == "structured_retryable_flag"


@pytest.mark.parametrize("mode,reserved", [("benchmark_openqa", 1024), ("benchmark_mcq", 768)])
def test_actual_builder_keeps_clamped_benchmark_output_reservation(mode, reserved):
    request = GenerationRequest(
        request_id="benchmark-output-clamp",
        mode=mode,
        condition="E0",
        question="Synthetic question",
        options={key: key for key in "ABCD"} if mode == "benchmark_mcq" else None,
        config=ModelConfig(max_tokens=4096, window_tokens=64, tokenizer_provider="estimate"),
    )
    with pytest.raises(ResponseValidationError) as raised:
        build_messages(request)
    result = raised.value.to_failure(request.config, before_dispatch=True)
    assert result["details"]["output_reserved_tokens"] == reserved
    assert request.config.max_tokens == 4096 and request.config.window_tokens == 64


@pytest.mark.parametrize(
    "values",
    [
        (True, 1024, 8192),
        (-1, 1024, 8192),
        (9000, False, 8192),
        (9000, 0, 8192),
        (9000, 1024, 16384),
        (9000, 2048, 8192),
        (1, 1024, 8192),
    ],
)
def test_invalid_or_different_budget_diagnostics_cannot_prove_a_frozen_failure(values):
    from generation.prompt_builder import InitialPromptWindowError

    request = initial_request()
    error = InitialPromptWindowError(
        *values, {"source": "synthetic private value", "api_key": "secret"}
    )
    result = error.to_failure(request.config, before_dispatch=True)
    assert result["details"] == {}
    assert "secret" not in json.dumps(result)
    recovery = failure_recovery(result, {"model_config": request.config.to_dict()})
    assert recovery["retryable"] is False and recovery["reason"] == "non_retryable_failure"
    assert recovery["new_request_required"] is False


def test_typed_error_after_attempt_reservation_is_not_promoted_to_initial_frozen_proof():
    from generation.prompt_builder import InitialPromptWindowError

    calls, events = [], []

    class SyntheticAdapter:
        def generate(self, *args, **kwargs):
            calls.append("local synthetic adapter")
            raise InitialPromptWindowError(20000, 1024, 16384, {"source": "tiktoken"})

    request = replace(
        initial_request(),
        question="What is DNA?",
        config=ModelConfig(tokenizer_provider="estimate"),
    )
    output = GenerationService(
        adapter=SyntheticAdapter(), api_key=None, checker_api_key=None
    ).generate(
        request,
        on_attempt=events.append,
    )
    assert calls == ["local synthetic adapter"] and events[0]["phase"] == "start"
    assert output.budget["consumed_calls"] == 1
    assert output.error["code"] == "CONTEXT_LIMIT" and output.error["details"] == {}
    recovery = failure_recovery(output.error, {"model_config": request.config.to_dict()})
    assert recovery["retryable"] is False and recovery["reason"] == "non_retryable_failure"
    assert recovery["new_request_required"] is False


def test_ordinary_prompt_within_window_still_builds_without_count_or_default_changes():
    request = replace(
        initial_request(),
        question="What is photosynthesis?",
        config=ModelConfig(tokenizer_provider="estimate"),
    )
    messages, selected, report, effective = build_messages(request)
    assert messages[-1]["content"] == request.question and selected == []
    assert report["total_reserved_tokens"] <= request.config.window_tokens == 16384
    assert effective.config == request.config
