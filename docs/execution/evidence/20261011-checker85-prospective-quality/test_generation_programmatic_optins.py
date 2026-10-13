"""Exercise ordinary GenerationService entry with immutable checker opt-ins
and zero provider calls.
"""

from dataclasses import asdict, replace
import socket

import pytest

from generation import GenerationService, ModelConfig, RequestBudget
from generation.joint_policy import VERSION as ENHANCEMENT_VERSION
from generation.types import GenerationRequest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("PROGRAMMATIC_REGRESSION_NETWORK_FORBIDDEN")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


class NoAdapterCalls:
    def __init__(self):
        self.calls = []

    def generate(self, *args, **kwargs):
        self.calls.append("generate")
        raise AssertionError("PROGRAMMATIC_REGRESSION_GENERATION_FORBIDDEN")

    def count_tokens(self, *args, **kwargs):
        self.calls.append("count_tokens")
        raise AssertionError("PROGRAMMATIC_REGRESSION_TOKEN_COUNT_FORBIDDEN")


def original_request(*, clarification):
    config = ModelConfig(
        provider="mock", structured_output_mode="json_object",
        tokenizer_provider="estimate", window_tokens=65536,
    )
    return GenerationRequest(
        request_id="synthetic-programmatic-optins85",
        question="What does the fixture process use?", mode="interactive_chat", condition="E1",
        answer_mode="textbook", enhancement_version=ENHANCEMENT_VERSION,
        source_relation_policy="source_relation_contract_v2",
        reliability_policy="evidence_reliability_v5", joint_checker_policy="typed_joint_v5",
        checker_payload_policy="lossless_full_checker_tables_v2",
        checker_output_policy="lossless_unit_findings_v1",
        config=config, checker_config=replace(config, configuration_id="synthetic-checker"),
        teaching_context={"teaching_mode": "direct", "turn_role": "user_question"},
        prepared_query={
            "intent": "clarification" if clarification else "factual",
            "needs_clarification": clarification,
        },
    )


def run_without_adapter_calls(original):
    before = asdict(original)
    adapter, budget, attempt_events = NoAdapterCalls(), RequestBudget(max_calls=2), []
    service = GenerationService(adapter=adapter, checker_adapter=adapter)
    result = service.generate(original, budget, on_attempt=attempt_events.append)
    assert adapter.calls == [] and attempt_events == []
    assert budget.consumed_calls == 0 and result.attempts == []
    assert asdict(original) == before
    return result


def test_checked_clarification_with_both_optins_remains_zero_call():
    original = original_request(clarification=True)
    result = run_without_adapter_calls(original)
    assert result.succeeded
    assert result.response_origin == "programmatic_ambiguity_clarification"
    assert original.checker_output_policy == "lossless_unit_findings_v1"
    assert original.checker_payload_policy == "lossless_full_checker_tables_v2"


def test_checked_factual_no_evidence_with_both_optins_remains_zero_call():
    original = original_request(clarification=False)
    result = run_without_adapter_calls(original)
    assert result.succeeded
    assert result.response_origin == "programmatic_no_evidence"
    assert original.checker_output_policy == "lossless_unit_findings_v1"
    assert original.checker_payload_policy == "lossless_full_checker_tables_v2"


def test_invalid_original_lossless_optin_still_rejects_before_adapter():
    original = replace(
        original_request(clarification=True),
        teaching_context={"teaching_mode": "direct", "turn_role": "unknown"},
    )
    result = run_without_adapter_calls(original)
    assert result.response is None
    assert result.error["code"] == "CHECKER_OUTPUT_POLICY_INCOMPATIBLE"
