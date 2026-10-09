"""Authored transport and strict-schema regressions, not semantic quality scores."""

from copy import deepcopy
from dataclasses import replace
import json

import pytest
from pydantic import ValidationError

from contracts.models import ChatMessageCreate, ChatResponseV1
from generation import GenerationService, ModelConfig, RequestBudget
from generation.adapters import chat_value
from generation.reliability_v5 import TeachingDraftV5
from generation.parser import parse_response, ResponseValidationError
from generation.response_field_contract_v2 import (
    ANSWER_EXAMPLE,
    REFUSAL_EXAMPLE,
    POLICY,
    instructions,
    validate,
)
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer
from test_teaching_contracts_v4 import empty


def run(values, request=None, calls=4):
    adapter = Script(values)
    result = GenerationService(adapter).generate(
        request or req(provider_output_policy=POLICY), RequestBudget(max_calls=calls)
    )
    return result, adapter


def invalid_answer():
    return {**answer(), "refusal_reason": "INSUFFICIENT_EVIDENCE"}


def test_examples_match_real_teaching_and_public_schema_without_transforming_results():
    for example in (ANSWER_EXAMPLE, REFUSAL_EXAMPLE):
        assert TeachingDraftV5.model_validate(example).model_dump() == example
        base = {
            k: v
            for k, v in example.items()
            if k not in {"tutor_question", "learner_attempt_evaluation"}
        }
        assert ChatResponseV1.model_validate(base).model_dump() == base
        assert (
            parse_response(
                json.dumps(base),
                mode="interactive_chat",
                condition="E1",
                evidence_ids=[],
                allow_uncited_teaching_draft=True,
            )
            == base
        )
        assert json.dumps(base, separators=(",", ":")) in instructions(
            include_teaching_fields=False
        )


@pytest.mark.parametrize("kind", ["answer", "clarification", "social"])
def test_non_refusal_with_refusal_reason_remains_invalid(kind):
    value = deepcopy(ANSWER_EXAMPLE)
    value.update(response_type=kind, refusal_reason="INSUFFICIENT_EVIDENCE")
    with pytest.raises(ValidationError, match="Only refusals have refusal_reason"):
        TeachingDraftV5.model_validate(value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("citations", ["ev_001"]),
        ("confidence", 0.5),
        ("short_answer", "A proposed result"),
        ("follow_up_questions", ["Continue?"]),
    ],
)
def test_refusal_field_invariants_are_not_relaxed(field, value):
    draft = {**REFUSAL_EXAMPLE, field: value}
    with pytest.raises(ValidationError, match="Refusal fields are inconsistent"):
        TeachingDraftV5.model_validate(draft)


def test_invalid_answer_repaired_with_examples_then_mandatory_independent_check():
    invalid = invalid_answer()
    out, adapter = run([invalid, answer(), checker])
    assert out.succeeded, out.error
    assert out.response == answer()
    assert [row["stage"] for row in out.attempts] == [
        "generation",
        "generation_format_repair",
        "joint_check",
    ]
    assert out.budget["consumed_calls"] == len(adapter.calls) == 3
    assert out.budget["format_repairs"] == 1
    assert instructions() in adapter.calls[0][0][0]["content"]
    assert instructions() in adapter.calls[1][0][-1]["content"]
    assert out.checks[-1]["accepted"] is True
    assert out.attribution["claims"][0]["support"]["human_rating"] is None


def test_repeated_invalid_output_keeps_actual_failure_and_never_calls_checker():
    invalid = invalid_answer()
    out, adapter = run([invalid, invalid])
    assert out.response is None and out.error["code"] == "SCHEMA_VALIDATION"
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert not out.checks and not out.delivered_projection


def test_two_call_budget_reserves_final_check_and_never_repairs_without_allowance():
    out, adapter = run([invalid_answer()], calls=2)
    assert out.response is None and out.error["code"] == "SCHEMA_VALIDATION"
    assert len(adapter.calls) == out.budget["consumed_calls"] == 1
    assert not out.checks


def test_schema_repair_cannot_override_final_unsupported_judgment():
    def unsupported(messages):
        value = checker(messages, body_ok=False)
        value["claims"][0]["status"] = "unsupported"
        return value

    out, adapter = run([invalid_answer(), answer(), unsupported], calls=3)
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(adapter.calls) == 3 and not out.delivered_projection


def test_new_examples_do_not_change_legacy_strict_or_once_prompts_and_empty_paths():
    outputs = []
    for policy in ("strict_v1", "json_example_once_v1"):
        out, adapter = run([answer(), checker], req(provider_output_policy=policy))
        assert out.succeeded
        assert "JOINT RESPONSE FIELD CONTRACT V2" not in adapter.calls[0][0][0]["content"]
        outputs.append((out.response, adapter.calls[0][0], adapter.calls[1][1]["response_schema"]))
    assert outputs[0] == outputs[1]
    strict, adapter = run([empty()], req(provider_output_policy="strict_v1"))
    assert strict.error["code"] == "EMPTY_RESPONSE" and len(adapter.calls) == 1
    once, adapter = run(
        [empty(), answer(), checker], req(provider_output_policy="json_example_once_v1")
    )
    assert once.succeeded and len(adapter.calls) == 3
    new, adapter = run([empty()])
    assert new.error["code"] == "EMPTY_RESPONSE" and len(adapter.calls) == 1


def test_unenhanced_chat_initial_and_format_repair_use_public_field_examples():
    request = req(provider_output_policy=POLICY, enhancement_version=None)
    out, adapter = run([invalid_answer(), answer()], request)
    assert out.succeeded and out.response == answer()
    assert len(adapter.calls) == 2
    text = instructions(include_teaching_fields=False)
    assert text in adapter.calls[0][0][0]["content"]
    assert text in adapter.calls[1][0][-1]["content"]
    assert out.token_budget["provider_output_policy"] == POLICY


def test_legacy_generation_new_prompt_is_counted_before_model_and_window_checked():
    request = req(
        provider_output_policy=POLICY,
        enhancement_version=None,
        config=ModelConfig(window_tokens=1100, max_tokens=128),
    )
    out, adapter = run([], request)
    assert out.error["code"] == "CONTEXT_LIMIT" and not adapter.calls
    assert out.budget["consumed_calls"] == 0


@pytest.mark.parametrize("bad", ["unknown", None, 1, True, {}])
def test_unknown_or_invalid_policy_fails_before_model_call(bad):
    out, adapter = run([], req(provider_output_policy=bad))
    assert out.error["code"] == "UNKNOWN_PROVIDER_OUTPUT_POLICY"
    assert not adapter.calls and out.budget["consumed_calls"] == 0
    with pytest.raises(ValueError, match="UNKNOWN_PROVIDER_OUTPUT_POLICY"):
        validate(bad)


def test_explicit_new_policy_is_not_an_e0_e1_benchmark_change():
    out, adapter = run([], req(provider_output_policy=POLICY, mode="benchmark_openqa"))
    assert out.error["code"] == "PROVIDER_OUTPUT_POLICY_INCOMPATIBLE"
    assert not adapter.calls
    assert req().provider_output_policy == "strict_v1"


def test_partial_supported_answer_is_an_answer_without_refusal_enum():
    value = {
        **ANSWER_EXAMPLE,
        "answer_text": "The provided material supports one part; the second requested point remains unresolved.",
    }
    assert TeachingDraftV5.model_validate(value).response_type == "answer"
    assert value["refusal_reason"] is None
    with pytest.raises(ValidationError):
        ChatMessageCreate.model_validate({"content": "Hello", "provider_output_policy": POLICY})


def test_refusal_marker_mismatch_still_fails_actual_request_dependent_parser():
    value = {
        k: v
        for k, v in REFUSAL_EXAMPLE.items()
        if k not in {"tutor_question", "learner_attempt_evaluation"}
    }
    value["answer_text"] += " [ev_001]"
    with pytest.raises(ResponseValidationError) as caught:
        parse_response(
            json.dumps(value), mode="interactive_chat", condition="E1", evidence_ids=["ev_001"]
        )
    assert caught.value.code == "CITATION_MARKER_MISMATCH"
