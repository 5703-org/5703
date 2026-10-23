"""Actual adapter/service controls with an isolated fake provider boundary."""

from dataclasses import replace
import json
import socket

import pytest

import generation
from generation import ModelConfig, RequestBudget
from generation import adapters, lossless_unit_findings_v1 as old
from generation import single_selection_findings_v2 as new
from generation.checked import generate_checked
from generation.reliability_v4 import compact_schema
from generation.source_relations_v2 import ReliableUnitCheck
from test_enhancement_generation import Script, answer
from test_full_checker_encoding_integration82 import BODY, full_judgment, packet
from test_lossless_output_integration84 import fixture_request, vertex_config

from backend.app.core import config as config_module


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("The fake provider fixture cannot use any network or DNS")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


class FakeResponse:
    status = 200
    headers = {"x-request-id": "authored-adapter87"}

    def __init__(self, raw):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return json.dumps(
            {
                "choices": [{"message": {"content": self.raw}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 20, "total_tokens": 40},
            }
        ).encode("utf-8")


def execute(monkeypatch, policy, negative=False, corrupt=False):
    request = fixture_request(policy, checker_config=vertex_config())
    teacher = Script([answer(BODY, short_answer=None)])
    captured = []
    wire_codec = new if policy == new.VERSION else old if policy == old.VERSION else None

    def fake_provider(envelope, timeout):
        body = json.loads(envelope.data)
        authored = full_judgment(body["messages"])
        if negative:
            authored["claims"][0]["units"][0].update(
                status="unsupported",
                fragment_ids=[],
                relation_preserved=False,
                conditions_preserved=False,
                reason="Authored missing negated/quantified condition.",
            )
        if wire_codec is not None:
            context = wire_codec.build_context(packet(body["messages"]))
            wire = wire_codec.encode_full(authored, context)
            if corrupt:
                wire["claims"][0]["units"][0]["relpath"] = "unexpected"
            raw = wire_codec.canonical(wire)
        else:
            raw = json.dumps(authored)
        captured.append({"body": body, "authored": authored, "raw": raw})
        return FakeResponse(raw)

    monkeypatch.setattr(adapters, "open_provider", fake_provider)
    checker = adapters.LLMAdapter(request.checker_config, api_key="synthetic-authored-test-only")
    original_generate = checker.generate

    def observed_generate(*args, **kwargs):
        result = original_generate(*args, **kwargs)
        captured[-1]["result"] = result
        captured[-1]["original_messages"] = args[0]
        captured[-1]["response_schema"] = kwargs["response_schema"]
        captured[-1]["response_schema_name"] = kwargs["response_schema_name"]
        return result

    checker.generate = observed_generate
    outcome = generation.GenerationService(adapter=teacher, checker_adapter=checker).generate(
        request, RequestBudget(max_calls=2)
    )
    return outcome, teacher, captured


@pytest.mark.parametrize("policy", [None, old.VERSION, new.VERSION])
@pytest.mark.parametrize("negative", [False, True])
def test_actual_adapter_compiles_and_hydrates_before_original_service_gates(
    monkeypatch, policy, negative
):
    outcome, teacher, captured = execute(monkeypatch, policy, negative)
    assert len(teacher.calls) == len(captured) == 1
    assert outcome.budget["consumed_calls"] == 2
    assert outcome.succeeded is (not negative), outcome.error
    if negative:
        assert outcome.error["code"] == "SEMANTIC_CHECK_FAILED"
        assert outcome.response is None
        unit = outcome.checks[0]["source_relation_assessment"]["claims"][0]["obligations"][0]
        assert unit["status"] == "unsupported"
        assert unit["fragment_ids"] == []
        assert unit["conditions_preserved"] is unit["relation_preserved"] is False
    body = captured[0]["body"]
    assert body["response_format"] == {"type": "json_object"}
    assert body["provider"]["only"] == ["google-vertex/global"]
    assert body["model"] == "google/gemini-3.5-flash-lite"
    assert body["messages"][-1] == captured[0]["original_messages"][-1]
    assert captured[0]["response_schema"] == compact_schema(ReliableUnitCheck)
    assert captured[0]["response_schema_name"] == (
        new.PROVIDER_SCHEMA_NAME
        if policy == new.VERSION
        else old.PROVIDER_SCHEMA_NAME
        if policy == old.VERSION
        else "joint_check_source_relations_v2"
    )
    assert outcome.checks[0]["typed_judgment_raw_aliases"] == captured[0]["authored"]
    if policy is not None:
        diagnostic = captured[0]["result"].diagnostic["checker_transport"]
        assert diagnostic["version"] == policy
        assert diagnostic["source_entailment_certified"] is False
        assert diagnostic["original_full_validators_required"] is True
        assert (
            diagnostic["canonical_schema_sha256"]
            == old.build_context(packet(body["messages"])).canonical_schema_sha256
        )
        assert diagnostic["hydrated_full_v2_sha256"] == old.digest(captured[0]["authored"])
        assert "decode_failure" not in diagnostic
    teacher_system = "\n".join(m["content"] for m in teacher.calls[0][0] if m["role"] == "system")
    assert ("set optional short_answer to null" in teacher_system) is (policy is not None)
    if policy == new.VERSION:
        matched = next(m["content"] for m in body["messages"] if m["role"] == "system")
        assert "Return the single_selection_findings_v2 schema" in matched
        assert "Return the lossless_unit_findings_v1 schema" not in matched
        embedded = json.loads(matched.rsplit("Match this JSON schema: ", 1)[1])
        assert embedded == new.wire_schema(new.build_context(packet(body["messages"])))


def test_real_adapter_rejects_unknown_wire_and_retains_raw(monkeypatch):
    outcome, teacher, captured = execute(monkeypatch, new.VERSION, corrupt=True)
    assert outcome.error["code"] == "CHECKER_TRANSPORT_INVALID"
    assert outcome.response is None and not outcome.delivered_projection
    result = captured[0]["result"]
    assert result.diagnostic["stage"] == "decode"
    diagnostic = result.diagnostic["checker_transport"]
    assert diagnostic["hydrated_full_v2_sha256"] is None
    assert diagnostic["decode_failure"]["category"] == "LOSSLESS_OUTPUT_INVALID"
    assert result.raw_text == result.transport_raw_text == captured[0]["raw"]


def test_settings_admits_explicit_new_policy_and_preserves_default_and_fences():
    settings = config_module.Settings(_env_file=None)
    assert settings.chat_checker_output_policy is None
    values = {
        "_env_file": None,
        "chat_source_relation_policy": "source_relation_contract_v2",
        "chat_joint_checker_policy": "typed_joint_v5",
    }
    assert (
        config_module.Settings(
            **values, chat_checker_output_policy=new.VERSION
        ).chat_checker_output_policy
        == new.VERSION
    )
    assert (
        config_module.Settings(
            **values, chat_checker_output_policy=old.VERSION
        ).chat_checker_output_policy
        == old.VERSION
    )
    for invalid in (
        {"chat_source_relation_policy": "off"},
        {"chat_checker_schema_policy": "textbook_checker_schema_research_v1"},
    ):
        with pytest.raises(ValueError):
            config_module.Settings(**{**values, **invalid}, chat_checker_output_policy=new.VERSION)


@pytest.mark.parametrize("fault", ["e0", "foreign_policy", "research_unchecked", "prompt_mode"])
def test_both_service_entries_reject_incompatible_v2_before_any_provider(monkeypatch, fault):
    request = fixture_request(new.VERSION)
    if fault == "e0":
        request = replace(request, condition="E0")
    elif fault == "foreign_policy":
        request = replace(request, checker_output_policy="unknown_future_output")
    elif fault == "prompt_mode":
        request = replace(request, checker_config=ModelConfig(structured_output_mode="prompt"))
    scripted = Script([])
    service = generation.GenerationService(adapter=scripted, checker_adapter=scripted)
    outcome = (
        generate_checked(service, request, RequestBudget(max_calls=2), research_unchecked=True)
        if fault == "research_unchecked"
        else service.generate(request, RequestBudget(max_calls=2))
    )
    assert outcome.error["code"] == "CHECKER_OUTPUT_POLICY_INCOMPATIBLE"
    assert outcome.budget["consumed_calls"] == 0
    assert scripted.calls == []


@pytest.mark.parametrize("policy", [old.VERSION, new.VERSION, "unknown_future_output"])
def test_service_entry_guard_preserved_before_downstream_checked_dispatch(monkeypatch, policy):
    def denied(*args, **kwargs):
        raise AssertionError("Incompatible output policy must stop at the service entry guard")

    monkeypatch.setattr(generation.checked, "generate_checked", denied)
    scripted = Script([])
    request = fixture_request(policy, condition="E0")
    outcome = generation.GenerationService(adapter=scripted, checker_adapter=scripted).generate(
        request, RequestBudget(max_calls=2)
    )
    assert outcome.error["code"] == "CHECKER_OUTPUT_POLICY_INCOMPATIBLE"
    assert outcome.budget["consumed_calls"] == 0 and scripted.calls == []
