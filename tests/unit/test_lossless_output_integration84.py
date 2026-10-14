"""Real service/transport gates with authored in-memory checker judgments.

These free fixtures measure structural preservation, not model accuracy, RAG
quality, or end-to-end answer latency. The runner selects the candidate module
overlay; this file does not modify package paths or contact a provider.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import socket

import pytest

from generation import GenerationService, ModelConfig, RequestBudget
from generation import lossless_unit_findings_v1 as codec
from generation import providers
from generation import checked
from generation.checked import generate_checked
from generation.types import ProviderResult, failure
from test_enhancement_generation import Script, answer
from test_full_checker_encoding_integration82 import BODY, full_judgment, packet, request_fixture


TEACHING = {
    "teaching_mode": "direct",
    "turn_role": "user_question",
    "current_problem": "What does photosynthesis use?",
}
SHORT_ANSWER_INSTRUCTION = "set optional short_answer to null"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("The authored integration fixture cannot open a socket")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture(autouse=True)
def same_audit_clock(monkeypatch):
    # Only the audit timestamp is fixed; every transport and publication gate
    # remains real, and attribution can be compared without deleting fields.
    class FixtureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2026, 10, 11, 0, 0, tzinfo=timezone.utc)
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    monkeypatch.setattr(checked, "datetime", FixtureClock)


def fixture_request(policy=codec.VERSION, **changes):
    values = {"checker_output_policy": policy, "teaching_context": deepcopy(TEACHING)}
    values.update(changes)
    return request_fixture(**values)


def vertex_config(**changes):
    values = {
        "provider": "openai_compatible",
        "model": "google/gemini-3.5-flash-lite",
        "base_url": "https://openrouter.ai/api/v1",
        "openrouter_route_profile": "gemini35_google_vertex_v1",
        "temperature": None,
        "reasoning_effort": None,
        "structured_output_mode": "json_object",
        "window_tokens": 65536,
        "tokenizer_provider": "estimate",
        "configuration_id": "authored-checker84-json-object",
    }
    values.update(changes)
    return ModelConfig(**values)


def projected_route_config():
    return vertex_config(
        model="anthropic/claude-haiku-5.5",
        openrouter_route_profile="haiku55_google_vertex_low_v1",
        structured_output_mode="json_schema",
    )


class TransportScript(Script):
    """Use production wire preparation and hydration around authored full output."""

    def __init__(self, values, request, mutate_wire=None):
        super().__init__(values)
        self.request = request
        self.mutate_wire = mutate_wire
        self.records = []

    def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        schema = kwargs["response_schema"]
        name = kwargs["response_schema_name"]
        config = (
            self.request.checker_config or self.request.config
            if name.startswith("joint_check")
            else self.request.config
        )
        transport = providers.prepare_checker_transport(config, messages, schema, name)
        wire_payload = providers.payload(config, messages, schema, name)
        value = next(self.values)
        if callable(value):
            value = value(messages)
        authored = deepcopy(value) if not isinstance(value, ProviderResult) else None
        wire = None
        if isinstance(value, ProviderResult):
            result = value
        else:
            if transport is not None:
                wire = codec.encode_full(value, transport["prepared"].context)
                if self.mutate_wire is not None:
                    self.mutate_wire(wire)
                raw = codec.canonical(wire)
            else:
                raw = json.dumps(value, ensure_ascii=False)
            result = ProviderResult(
                raw_text=raw,
                finish_reason="stop",
                provider="scripted_fixture",
                model="scripted_fixture",
                request_submitted=True,
            )
        provider_raw = result.raw_text
        result = providers.hydrate_checker_transport(result, transport)
        self.records.append(
            {
                "transport": transport,
                "payload": wire_payload,
                "authored": authored,
                "wire": wire,
                "provider_raw": provider_raw,
                "result": result,
            }
        )
        return result


def run(policy=codec.VERSION, callback=full_judgment, mutate_wire=None, **changes):
    request = fixture_request(policy, **changes)
    adapter = TransportScript([answer(BODY, short_answer=None), callback], request, mutate_wire)
    outcome = GenerationService(adapter=adapter, checker_adapter=adapter).generate(
        request, RequestBudget(max_calls=2)
    )
    return outcome, adapter


def assert_round_trip_metadata(record):
    transport, result = record["transport"], record["result"]
    diagnostic = result.diagnostic["checker_transport"]
    for key, value in transport["prepared"].context.descriptor().items():
        assert diagnostic[key] == value
    assert (
        diagnostic["raw_compact_sha256"]
        == hashlib.sha256(record["provider_raw"].encode("utf-8")).hexdigest()
    )
    assert result.transport_raw_text == record["provider_raw"]
    assert json.loads(result.raw_text) == record["authored"]
    assert diagnostic["hydrated_full_v2_sha256"] == codec.digest(record["authored"])
    assert diagnostic["source_entailment_certified"] is False
    assert diagnostic["original_full_validators_required"] is True
    assert "decode_failure" not in diagnostic


def assert_original_gates_equal(old, new, old_adapter, new_adapter):
    assert old.succeeded and new.succeeded, (old.error, new.error)
    assert old.response == new.response
    assert old.delivered_projection == new.delivered_projection
    compared_attributions = []
    for outcome, adapter in zip((old, new), (old_adapter, new_adapter), strict=True):
        systems = [message for message in adapter.calls[1][0] if message["role"] == "system"]
        assert len(systems) == 1
        actual_rubric_hash = hashlib.sha256(systems[0]["content"].encode("utf-8")).hexdigest()
        assert outcome.checks[0]["rubric_hash"] == actual_rubric_hash
        attribution = deepcopy(outcome.attribution)
        for claim in attribution["claims"]:
            assert claim["support"].pop("rubric_hash") == actual_rubric_hash
        compared_attributions.append(attribution)
    assert compared_attributions[0] == compared_attributions[1]
    assert old.budget["consumed_calls"] == new.budget["consumed_calls"] == 2
    for key in (
        "typed_judgment_raw_aliases",
        "actual_citation_bindings",
        "source_relation_assessment",
        "semantic_sufficiency",
    ):
        assert old.checks[0][key] == new.checks[0][key]
    assert old.checks[0]["accepted"] is new.checks[0]["accepted"] is True
    assert (
        old.checks[0]["checker_inconsistencies"] == new.checks[0]["checker_inconsistencies"] == []
    )


@pytest.mark.parametrize("mode", ["json_schema", "json_object"])
def test_opt_in_preserves_complete_response_and_every_original_gate(mode):
    config = ModelConfig(
        window_tokens=65536, tokenizer_provider="estimate", structured_output_mode=mode
    )
    old, old_adapter = run(None, config=config)
    new, new_adapter = run(config=config)
    assert_original_gates_equal(old, new, old_adapter, new_adapter)
    assert len(old_adapter.calls) == len(new_adapter.calls) == 2
    old_messages, old_kwargs = old_adapter.calls[1]
    new_messages, new_kwargs = new_adapter.calls[1]
    assert packet(old_messages) == packet(new_messages)
    assert old_kwargs["response_schema"] == new_kwargs["response_schema"]
    assert old_kwargs["response_schema_name"] == "joint_check_source_relations_v2"
    assert new_kwargs["response_schema_name"] == codec.PROVIDER_SCHEMA_NAME
    assert old_adapter.records[1]["transport"] is None
    assert "checker_transport" not in old_adapter.records[1]["result"].diagnostic
    record = new_adapter.records[1]
    assert_round_trip_metadata(record)
    assert record["transport"]["name"] == codec.VERSION
    assert record["payload"]["messages"][-1] == new_messages[-1]
    if mode == "json_schema":
        actual = record["payload"]["response_format"]["json_schema"]
        assert actual["name"] == codec.VERSION and actual["strict"] is True
        assert actual["schema"] == record["transport"]["schema"]
    else:
        assert record["payload"]["response_format"] == {"type": "json_object"}
        system = next(m["content"] for m in record["payload"]["messages"] if m["role"] == "system")
        assert (
            json.loads(system.rsplit("Match this JSON schema: ", 1)[1])
            == record["transport"]["schema"]
        )
    old_teacher = "\n".join(m["content"] for m in old_adapter.calls[0][0] if m["role"] == "system")
    new_teacher = "\n".join(m["content"] for m in new_adapter.calls[0][0] if m["role"] == "system")
    assert SHORT_ANSWER_INSTRUCTION not in old_teacher
    assert SHORT_ANSWER_INSTRUCTION in new_teacher


def test_vertex_json_object_sends_actual_projection_schema_and_hydrates_original_gates():
    checker_config = vertex_config()
    old, old_adapter = run(None, checker_config=checker_config)
    new, adapter = run(checker_config=checker_config)
    assert_original_gates_equal(old, new, old_adapter, adapter)
    record = adapter.records[1]
    assert_round_trip_metadata(record)
    body = record["payload"]
    assert body["model"] == checker_config.model
    assert body["provider"]["only"] == ["google-vertex/global"]
    assert body["reasoning"] == {"effort": "low"}
    assert body["response_format"] == {"type": "json_object"}
    system = next(m["content"] for m in body["messages"] if m["role"] == "system")
    assert (
        json.loads(system.rsplit("Match this JSON schema: ", 1)[1]) == record["transport"]["schema"]
    )
    assert body["messages"][-1] == adapter.calls[1][0][-1]


@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_negative_units_remain_negative_without_filled_sources_or_publication(status):
    reason = "Authored missing-condition fixture; preserve this exact reason."

    def negative(messages):
        full = full_judgment(messages)
        full["claims"][0]["units"][0].update(status=status, fragment_ids=[], reason=reason)
        assert full["claims"][0]["status"] == "supported" and full["body_ok"] is True
        return full

    old, _ = run(None, negative)
    new, adapter = run(callback=negative)
    assert len(adapter.calls) == new.budget["consumed_calls"] == 2
    assert new.error["code"] == old.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert new.response is None and not new.delivered_projection
    assert new.checks[0]["accepted"] is False
    assert (
        new.checks[0]["source_relation_assessment"] == old.checks[0]["source_relation_assessment"]
    )
    unit = new.checks[0]["source_relation_assessment"]["claims"][0]["obligations"][0]
    assert unit["status"] == status and unit["reason"] == reason
    assert unit["fragment_ids"] == [] and unit["source_quotes"] == []
    assert_round_trip_metadata(adapter.records[1])


@pytest.mark.parametrize(
    "fault", ["missing_units", "foreign_claim", "foreign_unit", "foreign_source"]
)
def test_invalid_provider_wire_fails_closed_before_original_publication(fault):
    def corrupt(wire):
        row = wire["cs"][0]
        if fault == "missing_units":
            row.pop("us")
        elif fault == "foreign_claim":
            row["c"] = "C999"
        elif fault == "foreign_unit":
            row["us"][0]["u"] = "U999"
        else:
            row["us"][0]["fs"] = ["F999"]

    out, adapter = run(mutate_wire=corrupt)
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert out.error["code"] == "CHECKER_TRANSPORT_INVALID"
    assert out.response is None and not out.delivered_projection
    record = adapter.records[1]
    result = record["result"]
    diagnostic = result.diagnostic["checker_transport"]
    assert result.error["code"] == "CHECKER_TRANSPORT_INVALID"
    assert result.raw_text == result.transport_raw_text == record["provider_raw"]
    assert diagnostic["decode_failure"] == {
        "category": "LOSSLESS_OUTPUT_INVALID",
        "detail": {"category": "LOCAL_DECODE_ERROR"},
    }
    assert out.error == result.error == failure(
        "CHECKER_TRANSPORT_INVALID",
        "Short output could not preserve the complete original V2 checker contract",
    )
    assert diagnostic["hydrated_full_v2_sha256"] is None
    assert (
        diagnostic["raw_compact_sha256"]
        == hashlib.sha256(record["provider_raw"].encode("utf-8")).hexdigest()
    )


def test_existing_provider_error_is_preserved_without_decoding_or_publication():
    original = failure("SYNTHETIC_PROVIDER_FAILURE", "Authored provider error")
    failed = ProviderResult(
        raw_text="invalid fixture wire", error=deepcopy(original), request_submitted=True
    )
    out, adapter = run(callback=failed)
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert out.error == original
    assert out.response is None and not out.delivered_projection
    result = adapter.records[1]["result"]
    assert result.error == original and result.raw_text == "invalid fixture wire"
    diagnostic = result.diagnostic["checker_transport"]
    assert diagnostic["hydrated_full_v2_sha256"] is None
    assert "decode_failure" not in diagnostic


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"enhancement_version": None}, id="legacy-dispatch"),
        pytest.param({"mode": "benchmark_mcq"}, id="benchmark"),
        pytest.param({"source_relation_policy": None}, id="source-none"),
        pytest.param({"source_relation_policy": "source_relation_contract_v1"}, id="source-v1"),
        pytest.param({"source_relation_policy": "future_source_contract"}, id="foreign-source"),
        pytest.param({"joint_checker_policy": "scoped_compact_v6"}, id="compact-v6"),
        pytest.param(
            {"checker_schema_policy": "textbook_checker_schema_research_v1"}, id="research-schema"
        ),
        pytest.param(
            {"checker_output_policy": "future_output_projection"}, id="foreign-output-policy"
        ),
        pytest.param({"condition": "E0"}, id="e0"),
        pytest.param({"answer_mode": "general_knowledge"}, id="non-textbook"),
        pytest.param({"reliability_policy": "evidence_reliability_v4"}, id="reliability-v4"),
        pytest.param(
            {"teaching_context": {**TEACHING, "turn_role": "user_attempt"}}, id="learner-attempt"
        ),
        pytest.param(
            {"checker_config": ModelConfig(structured_output_mode="prompt")}, id="prompt-wire"
        ),
        pytest.param(
            {"checker_config": projected_route_config()}, id="post-bound-schema-projection"
        ),
        pytest.param(
            {
                "checker_config": vertex_config(
                    openrouter_route_profile="gemini35_google_vertex_compact_checker_v3"
                )
            },
            id="old-compact-provider-transport",
        ),
    ],
)
def test_incompatible_lanes_reject_at_service_entry_without_any_provider_call(changes):
    request = fixture_request(**changes)
    adapter = TransportScript([], request)
    out = GenerationService(adapter=adapter, checker_adapter=adapter).generate(
        request, RequestBudget(max_calls=4)
    )
    assert out.error["code"] == "CHECKER_OUTPUT_POLICY_INCOMPATIBLE"
    assert out.budget["consumed_calls"] == 0 and adapter.calls == adapter.records == []
    assert out.response is None and not out.delivered_projection and not out.attempts


def test_research_unchecked_cannot_bypass_output_policy_at_checked_entry():
    request = fixture_request()
    adapter = TransportScript([], request)
    out = generate_checked(
        GenerationService(adapter=adapter, checker_adapter=adapter),
        request,
        RequestBudget(max_calls=4),
        research_unchecked=True,
    )
    assert out.error["code"] == "CHECKER_OUTPUT_POLICY_INCOMPATIBLE"
    assert out.budget["consumed_calls"] == 0 and adapter.calls == adapter.records == []
    assert out.response is None and not out.attempts


@pytest.mark.parametrize("fault", ["basic", "schema_projection", "compact_overlap"])
def test_actual_provider_prepare_rejects_basic_projection_and_transport_overlap(fault):
    baseline, adapter = run(None)
    assert baseline.succeeded, baseline.error
    messages, kwargs = adapter.calls[1]
    config = fixture_request().config
    basic = fault == "basic"
    expected = "LOSSLESS_OUTPUT_BASIC_UNSUPPORTED"
    if fault == "schema_projection":
        config = projected_route_config()
        expected = "LOSSLESS_OUTPUT_SCHEMA_PROJECTION_UNSUPPORTED"
    elif fault == "compact_overlap":
        config = vertex_config(openrouter_route_profile="gemini35_google_vertex_compact_checker_v3")
        expected = "LOSSLESS_OUTPUT_TRANSPORT_OVERLAP"
    with pytest.raises(ValueError, match=f"^{expected}$"):
        providers.prepare_checker_transport(
            config,
            messages,
            kwargs["response_schema"],
            codec.PROVIDER_SCHEMA_NAME,
            basic=basic,
        )
