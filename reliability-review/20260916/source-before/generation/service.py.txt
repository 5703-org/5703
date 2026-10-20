"""Shared runtime generation, one retry owner and persistent-budget callbacks."""

from __future__ import annotations
from dataclasses import asdict, replace
import time
from typing import Callable
from pydantic import ValidationError

from conversation.query import prepare_query
from .token_counting import TokenCounter
from .adapters import LLMAdapter, _UNSET, chat_value, redact
from .parser import ResponseValidationError, parse_response
from .prompt_builder import build_messages, response_schema
from .types import GenerationRequest, GenerationOutcome, RequestBudget, failure


class GenerationService:
    def __init__(
        self, adapter=None, sleep: Callable[[float], None] = time.sleep, *, api_key=_UNSET
    ):
        self.api_key = api_key
        self.adapter = adapter
        self.sleep = sleep

    def generate(
        self,
        request: GenerationRequest,
        budget: RequestBudget | None = None,
        on_attempt: Callable | None = None,
    ) -> GenerationOutcome:
        budget = budget if budget is not None else RequestBudget()
        started = time.monotonic()
        last_accounted = started

        def account_time():
            nonlocal last_accounted
            now = time.monotonic()
            budget.active_seconds += now - last_accounted
            last_accounted = now

        output = GenerationOutcome(
            provider=request.config.provider,
            model=request.config.model,
            model_mode="mock" if request.config.provider == "mock" else "live",
        )
        try:
            request.config.validate()
            if request.mode == "interactive_chat" and request.prepared_query is None:
                request = replace(
                    request,
                    prepared_query=prepare_query(
                        request.question, request.history, request.summary
                    ).model_dump(),
                )
            counter = TokenCounter(request.config)
            messages, selected, report, effective = build_messages(request, counter)
        except (ValueError, ValidationError) as exc:
            output.error = failure(getattr(exc, "code", "CONFIGURATION_ERROR"), redact(str(exc)))
            output.budget = budget.to_dict()
            return output
        output.messages, output.evidence, output.token_budget = messages, [], report
        report["selected_count"] = len(selected)
        report["selected_evidence_ids"] = [e["evidence_id"] for e in selected]
        report["submitted_count"] = 0
        report["submitted_evidence_ids"] = []
        report["submitted_chunk_ids"] = []
        schema = response_schema(request.mode)
        schema_name = "mcq_response_v1" if request.mode == "benchmark_mcq" else "chat_response_v1"
        config = replace(request.config, max_tokens=report["output_reserved_tokens"])
        adapter = self.adapter or LLMAdapter(config, api_key=self.api_key)
        context = {
            "request_id": request.request_id,
            "mode": effective.mode,
            "condition": effective.condition,
            "question": effective.question,
            "question_id": effective.question_id,
            "options": effective.options,
            "evidence": selected,
            "history": effective.history,
            "summary": effective.summary,
            "profile": effective.profile,
            "prepared_query": effective.prepared_query,
        }
        # Clear factual no-evidence requests need no external call; social and ambiguity are separate.
        intent = (effective.prepared_query or {}).get("intent", "factual")
        if (
            request.mode != "benchmark_mcq"
            and request.condition != "E0"
            and not selected
            and intent not in {"social", "clarification"}
        ):
            output.response = chat_value(
                "refusal",
                "No available textbook passage supports this question. Try a topic in the current corpus or make the question more specific.",
                reason="NO_EVIDENCE",
            )
            output.response_origin = "programmatic_no_evidence"
            account_time()
            output.budget = budget.to_dict()
            output.timing = {
                "generation_ms": 0,
                "total_ms": int((time.monotonic() - started) * 1000),
            }
            return output
        provider_adjustment = 0
        native_count = config.provider in {"anthropic", "gemini"} and config.tokenizer_provider in {
            "auto",
            "provider",
        }
        if (
            config.tokenizer_provider == "provider"
            and not native_count
            and config.token_count_fallback == "error"
        ):
            output.error = failure(
                "TOKENIZER_UNAVAILABLE", "This protocol has no configured native token counter"
            )
            output.budget = budget.to_dict()
            return output
        if native_count:
            account_time()
            try:
                budget.reserve()
            except ValueError:
                output.error = failure(
                    "BUDGET_EXHAUSTED", "No call budget remains for provider token counting"
                )
                output.budget = budget.to_dict()
                return output
            count_id = f"{request.request_id}:attempt:{budget.consumed_calls}"
            if on_attempt:
                on_attempt(
                    {
                        "phase": "start",
                        "attempt_id": count_id,
                        "stage": "token_count",
                        "budget": budget.to_dict(),
                        "messages": messages,
                        "schema": schema_name,
                    }
                )
            account_time()
            if budget.remaining_seconds <= 0:
                output.error = failure("BUDGET_EXHAUSTED", "No time remains for token counting")
                output.budget = budget.to_dict()
                return output
            counted = adapter.count_tokens(
                messages,
                response_schema=schema,
                response_schema_name=schema_name,
                timeout_seconds=min(config.timeout_seconds, budget.remaining_seconds),
            )
            account_time()
            record = {
                "attempt_id": count_id,
                "stage": "token_count",
                "provider": counted.provider,
                "model": counted.model,
                "provider_request_id": counted.provider_request_id,
                "finish_reason": counted.finish_reason,
                "usage": {
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "reasoning_tokens": None,
                    "cost": None,
                },
                "latency_ms": counted.latency_ms,
                "error": counted.error,
                "counted_input_tokens": counted.usage.get("input_tokens"),
            }
            output.attempts.append(record)
            if on_attempt:
                on_attempt(
                    {"phase": "finish", **record, "budget": budget.to_dict(), "raw_text": ""}
                )
            if counted.error:
                report["provider_count_error"] = counted.error["code"]
                if (
                    config.token_count_fallback == "error"
                    or counted.error.get("details", {}).get("http_status") in {401, 403}
                    or counted.error["code"] == "CONFIGURATION_ERROR"
                ):
                    output.error = counted.error
                    output.budget = budget.to_dict()
                    return output
                report["token_counting"]["fallback_reason"] = (
                    "provider_count_failed_explicit_estimate_fallback"
                )
            else:
                actual_input = counted.usage["input_tokens"]
                provider_adjustment = max(0, actual_input - (report["input_reserved_tokens"] - 128))
                report["provider_input_tokens"] = actual_input
                report["counter"] = config.provider + "_count_tokens"
                report["token_counting"]["provider_count_source"] = report["counter"]
                report["token_counting"]["provider_count_is_estimate"] = True
                report["total_reserved_tokens"] = (
                    actual_input + report["output_reserved_tokens"] + 128
                )
                if report["total_reserved_tokens"] > config.window_tokens:
                    output.error = failure(
                        "CONTEXT_LIMIT",
                        "Provider count plus output reservation exceeds the configured window",
                    )
                    output.budget = budget.to_dict()
                    return output
        stage, current_messages, attempt_usage = "generation", messages, []
        account_time()
        while True:
            account_time()
            try:
                budget.reserve()
            except ValueError:
                output.error = failure(
                    "BUDGET_EXHAUSTED",
                    "The logical request has exhausted its call or active-time allowance",
                )
                break
            attempt_id = f"{request.request_id}:attempt:{budget.consumed_calls}"
            begin = time.monotonic()
            event = {
                "phase": "start",
                "attempt_id": attempt_id,
                "stage": stage,
                "budget": budget.to_dict(),
                "messages": current_messages,
                "schema": schema_name,
            }
            if on_attempt:
                on_attempt(event)
            account_time()
            if budget.remaining_seconds <= 0:
                output.error = failure(
                    "BUDGET_EXHAUSTED", "No active execution time remains for the reserved call"
                )
                break
            result = adapter.generate(
                current_messages,
                response_schema=schema,
                response_schema_name=schema_name,
                request_context=context,
                timeout_seconds=min(config.timeout_seconds, budget.remaining_seconds),
            )
            if result.request_submitted is not False:
                output.evidence = selected
                report["submitted_count"] = len(selected)
                report["submitted_evidence_ids"] = [e["evidence_id"] for e in selected]
                report["submitted_chunk_ids"] = [e["chunk_id"] for e in selected]
                report["submission_scope"] = (
                    "generation_transport_invoked; provider acceptance is unknown on network failure"
                )
            elapsed = time.monotonic() - begin
            account_time()
            attempt_usage.append(result.usage)
            record = {
                "attempt_id": attempt_id,
                "stage": stage,
                "provider": result.provider,
                "model": result.model,
                "provider_request_id": result.provider_request_id,
                "finish_reason": result.finish_reason,
                "usage": result.usage,
                "latency_ms": result.latency_ms,
                "error": result.error,
            }
            output.provider, output.model = result.provider, result.model
            validation_error = None
            if result.error is None and result.finish_reason == "length":
                result.error = failure(
                    "OUTPUT_TRUNCATED", "Provider output reached its token limit"
                )
            if result.error is None and not isinstance(result.raw_text, str):
                result.error = failure("PROVIDER_RESPONSE_ERROR", "Provider text is invalid")
            if result.error is None:
                try:
                    output.response = parse_response(
                        result.raw_text,
                        mode=request.mode,
                        condition=request.condition,
                        evidence_ids=[e["evidence_id"] for e in selected],
                        question_id=request.question_id,
                        options=request.options,
                    )
                except ResponseValidationError as exc:
                    validation_error = failure(exc.code, str(exc))
            account_time()
            if budget.active_seconds > budget.max_active_seconds:
                output.response = None
                result.error = failure(
                    "BUDGET_EXHAUSTED",
                    "Provider completion arrived after the request's active execution allowance",
                )
            record["error"] = result.error or validation_error
            output.attempts.append(record)
            if on_attempt:
                on_attempt(
                    {
                        "phase": "finish",
                        **record,
                        "budget": budget.to_dict(),
                        "raw_text": result.raw_text,
                    }
                )
            if output.response is not None:
                break
            if result.error:
                output.error = result.error
                if (
                    result.error.get("retryable")
                    and budget.transient_retries < 2
                    and budget.consumed_calls < budget.max_calls
                ):
                    delay = result.error.get("details", {}).get("retry_after_seconds")
                    delay = (
                        min(60.0, float(delay))
                        if delay is not None
                        else min(2.0, 0.25 * (2**budget.transient_retries))
                    )
                    if delay >= budget.remaining_seconds:
                        break
                    budget.transient_retries += 1
                    pause = time.monotonic()
                    self.sleep(delay)
                    account_time()
                    stage = "transient_retry"
                    continue
                break
            output.error = validation_error
            if (
                budget.format_repairs >= 1
                or budget.consumed_calls >= budget.max_calls
                or budget.remaining_seconds <= 0
            ):
                break
            budget.format_repairs += 1
            citation_field = "explanation" if request.mode == "benchmark_mcq" else "answer_text"
            citation_rules = (
                f"Every citation must appear as [ev_NNN] in {citation_field}, and every such marker must be in citations. "
                "A refusal must have citations=[] and no inline evidence markers; explain missing support without source markers. "
                "Do not invent evidence or change supported content merely to fix formatting. "
            )
            if request.mode == "benchmark_mcq" and request.condition == "E0":
                citation_rules = "The frozen E0 policy requires one option selection with no citations; do not refuse. "
            repair = {
                "role": "user",
                "content": "Correct the response to the original learner question, preserving supported meaning. Return exactly one complete JSON object, not plain prose. Validation code: "
                + validation_error["code"]
                + ". Validation detail: "
                + validation_error["message"]
                + ". Original learner question: "
                + request.question
                + ". Allowed current evidence IDs: "
                + ", ".join(e["evidence_id"] for e in selected)
                + ". "
                + citation_rules
                + "Previous untrusted output excerpt: "
                + redact(result.raw_text, 1200),
            }
            current_messages = messages + [repair]
            if (
                counter.request_input(current_messages, schema, schema_name)
                + provider_adjustment
                + report["output_reserved_tokens"]
                > config.window_tokens
            ):
                output.error = failure(
                    "CONTEXT_LIMIT", "Format repair cannot fit within the configured model window"
                )
                break
            stage = "format_repair"
        if output.response is not None:
            output.error = None
        output.usage = {
            name: (
                sum(item[name] for item in attempt_usage)
                if attempt_usage and all(item.get(name) is not None for item in attempt_usage)
                else None
            )
            for name in ("input_tokens", "output_tokens", "total_tokens", "reasoning_tokens")
        }
        output.usage.update(
            cost=None,
            usage_complete=bool(attempt_usage)
            and all(item.get("total_tokens") is not None for item in attempt_usage),
        )
        account_time()
        if budget.active_seconds > budget.max_active_seconds:
            output.response = None
            output.error = failure(
                "BUDGET_EXHAUSTED",
                "The request's active execution allowance was exceeded before completion",
            )
        output.budget = budget.to_dict()
        output.timing = {
            "generation_ms": sum(
                a["latency_ms"] for a in output.attempts if a["stage"] != "token_count"
            ),
            "total_ms": int((time.monotonic() - started) * 1000),
            "preparation_ms": 0,
            "attempts": len(output.attempts),
        }
        return output
