"""Independent frozen-base C0/C1/C2 workload without learner-message effects."""

from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
import time

from contracts.models import TeachingStudyResponseV1, EvidenceSnapshot
from generation.adapters import LLMAdapter
from generation.parser import parse_teaching, ResponseValidationError
from generation.prompt_builder import PROMPTS
from generation.types import ModelConfig, RequestBudget, failure
from generation.token_counting import TokenCounter
from .compiler import compile_profile, COMPILER_VERSION


class TeachingStudyService:
    def __init__(self, adapter=None):
        self.adapter = adapter

    def generate(
        self,
        *,
        run_id: str,
        item_id: str,
        condition: str,
        target_level: str,
        base_answer: dict,
        evidence: list[dict],
        config: ModelConfig | None = None,
        budget: RequestBudget | None = None,
        on_attempt=None,
    ):
        config, budget = config or ModelConfig(), budget or RequestBudget()
        preparation_started = time.monotonic()
        if condition not in {"C0", "C1", "C2"} or target_level not in {
            "beginner",
            "intermediate",
            "advanced",
        }:
            raise ValueError("Invalid teaching study condition or target")
        if not base_answer.get("answer_text") or base_answer.get("response_type") != "answer":
            raise ValueError("A frozen completed base answer is required")
        selected = [EvidenceSnapshot.model_validate(e).model_dump() for e in evidence]
        permitted = [e["evidence_id"] for e in selected]
        if not set(base_answer.get("citations", [])) <= set(permitted):
            raise ValueError("Base answer cites evidence outside the frozen study input")
        for passage in selected:
            if hashlib.sha256(passage["text"].encode()).hexdigest() != passage["text_hash"]:
                raise ValueError("Frozen evidence hash mismatch")
        policy = (
            None
            if condition == "C0"
            else "Learner level: " + target_level
            if condition == "C1"
            else compile_profile({"level": target_level})["policy"]
        )
        data = {"base_answer": base_answer, "evidence": selected, "presentation_policy": policy}
        messages = [
            {
                "role": "system",
                "content": (PROMPTS / "teaching_v1.txt").read_text(encoding="utf-8"),
            },
            {"role": "user", "content": json.dumps(data, sort_keys=True, ensure_ascii=False)},
        ]
        schema = TeachingStudyResponseV1.model_json_schema()
        record = {
            "run_id": run_id,
            "item_id": item_id,
            "condition": condition,
            "target_level": target_level,
            "profile_rule_version": COMPILER_VERSION,
            "state": "pending",
            "response": None,
            "error": None,
            "messages": messages,
            "evidence_ids": permitted,
            "base_hash": hashlib.sha256(
                json.dumps(base_answer, sort_keys=True).encode()
            ).hexdigest(),
            "model_mode": "mock" if config.provider == "mock" else "live",
            "budget": budget.to_dict(),
            "token_budget": {"window_tokens": config.window_tokens},
        }
        try:
            config.validate()
            if config.tokenizer_provider == "provider" and config.token_count_fallback == "error":
                raise ValueError(
                    "A provider token-count request is incompatible with this single-rewrite study policy."
                )
            counter = TokenCounter(config)
            input_tokens = counter.request_input(messages, schema, "teaching_study_response_v1")
            token_total = input_tokens + config.max_tokens
            metadata = counter.report()
            if config.tokenizer_provider == "provider":
                metadata["fallback_reason"] = "single_rewrite_policy_no_provider_count_request"
            record["token_budget"] = {
                "input_tokens": input_tokens,
                "output_reserved_tokens": config.max_tokens,
                "total_reserved_tokens": token_total,
                "window_tokens": config.window_tokens,
                "counter": metadata["source"],
                "tokenizer": metadata,
                "provider_count_calls": 0,
                "policy": "one_rewrite_call; full_serialized_payload_with_local_protocol_estimate",
            }
        except (ValueError, TypeError):
            budget.active_seconds += time.monotonic() - preparation_started
            return {
                **record,
                "state": "failed",
                "budget": budget.to_dict(),
                "error": failure(
                    "TOKENIZER_UNAVAILABLE",
                    "The frozen teaching tokenizer is unavailable or requires an extra provider count call; configure a verified local tokenizer or explicit estimate.",
                ),
            }
        budget.active_seconds += time.monotonic() - preparation_started
        record["budget"] = budget.to_dict()
        if token_total > config.window_tokens:
            return {
                **record,
                "state": "failed",
                "error": failure("CONTEXT_LIMIT", "Frozen teaching inputs exceed the model window"),
            }
        try:
            budget.reserve()
        except ValueError:
            return {
                **record,
                "state": "failed",
                "error": failure("BUDGET_EXHAUSTED", "Study item allowance exhausted"),
            }
        started = time.monotonic()
        if on_attempt:
            on_attempt(
                {
                    "phase": "start",
                    "stage": "teaching",
                    "item_id": item_id,
                    "budget": budget.to_dict(),
                }
            )
        result = (self.adapter or LLMAdapter(config)).generate(
            messages,
            response_schema=schema,
            response_schema_name="teaching_study_response_v1",
            timeout_seconds=min(config.timeout_seconds, budget.remaining_seconds),
            request_context={
                "schema": "teaching_study_response_v1",
                "base_answer": base_answer,
                "evidence": selected,
                "target_level": target_level,
                "study_condition": condition,
            },
        )
        budget.active_seconds += time.monotonic() - started
        record.update(
            state="failed",
            usage=result.usage,
            budget=budget.to_dict(),
            error=result.error,
            latency_ms=result.latency_ms,
            provider=result.provider,
            model=result.model,
        )
        if result.finish_reason == "length":
            record["error"] = failure("OUTPUT_TRUNCATED", "Study output reached the token limit")
        if budget.active_seconds > budget.max_active_seconds:
            record["error"] = failure("BUDGET_EXHAUSTED", "Study execution allowance exceeded")
        if record["error"] is None:
            try:
                record.update(
                    response=parse_teaching(result.raw_text, permitted), state="succeeded"
                )
            except ResponseValidationError as exc:
                record["error"] = failure(exc.code, str(exc))
        if on_attempt:
            on_attempt(
                {
                    "phase": "finish",
                    "stage": "teaching",
                    "item_id": item_id,
                    "budget": budget.to_dict(),
                    "usage": result.usage,
                    "error": record["error"],
                    "raw_text": result.raw_text,
                }
            )
        return record

    def matrix(
        self,
        *,
        run_id: str,
        base_answer: dict,
        evidence: list[dict],
        config: ModelConfig | None = None,
    ):
        return [
            self.generate(
                run_id=run_id,
                item_id=f"{level}-{condition}",
                condition=condition,
                target_level=level,
                base_answer=base_answer,
                evidence=evidence,
                config=config,
            )
            for level in ("beginner", "intermediate", "advanced")
            for condition in ("C0", "C1", "C2")
        ]
