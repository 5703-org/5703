"""Offline Haiku wire projection: real V5 contracts, synthetic transport only."""

import copy
import hashlib
import io
import json
from pathlib import Path
import socket
import sys
from types import ModuleType
from urllib.error import HTTPError

import pytest
from pydantic import ValidationError

from contracts.models import ChatResponseV1
from generation.openrouter_routes import BASE_URL, PROFILES, prepare_schema_wire
from generation.providers import payload as runtime_payload
from generation.reliability_v4 import compact_schema
from generation.reliability_v5 import ReliableCheckV5, TeachingDraftV5, assess_requirements
from generation.types import ModelConfig


HAIKU = "haiku55_google_vertex_low_v1"
LEGACY_SCHEMA_SHA = "7988037e08d52662a1b232f049776a42b6d10ad5d896f1a26c8c912b3efd79d4"
LEGACY_FIXTURE = Path(__file__).with_name("fixtures") / "haiku_actual05_checker_schema.json"
EXACT_SCHEMA_SHA = "79efe6d486558f04f3bf39f9ea6a2d3336bcc829b188e67e9257e201498789b2"
FIXTURE = Path(__file__).with_name("fixtures") / "haiku_current83_checker_schema.json"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def configured(profile=HAIKU):
    route = PROFILES[profile]
    return ModelConfig(
        provider="openai_compatible", model=route.model, base_url=BASE_URL,
        max_tokens=4096, window_tokens=10000,
        temperature=0 if route.temperature_supported else None,
        configuration_id="model-settings:synthetic-wire-only", openrouter_route_profile=profile,
    )


def payload_for(config, schema, messages=None):
    route = PROFILES[config.openrouter_route_profile]
    return {
        "model": config.model,
        "messages": copy.deepcopy(messages or [{"role": "user", "content": "Synthetic question."}]),
        "provider": {"only": [route.provider_slug], "allow_fallbacks": False, "require_parameters": True},
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "joint_check_v5", "strict": True, "schema": copy.deepcopy(schema),
        }},
    }


@pytest.fixture(autouse=True)
def deny_actual_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Tests must not open a network connection")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "socket", denied)


def test_actual_checker_schema_matches_native_and_keeps_original_evidence_limit():
    original = json.loads(FIXTURE.read_bytes())
    assert digest(original) == EXACT_SCHEMA_SHA
    assert original == compact_schema(ReliableCheckV5)
    original_body = payload_for(configured(), original)
    before = copy.deepcopy(original_body)
    wire, metadata = prepare_schema_wire(configured(), original_body, original)
    assert original_body == before
    assert original == compact_schema(ReliableCheckV5)
    assert metadata["removed_bound_count"] == 42
    assert metadata["original_response_schema_sha256"] == EXACT_SCHEMA_SHA
    assert metadata["provider_schema_before_projection_sha256"] == EXACT_SCHEMA_SHA
    projected = wire["response_format"]["json_schema"]["schema"]
    assert metadata["wire_schema_sha256"] == digest(projected)
    assert metadata["wire_schema_sha256"] != EXACT_SCHEMA_SHA
    assert original["$defs"]["RequirementCheck"]["properties"]["evidence"]["maxItems"] == 8
    evidence = projected["$defs"]["RequirementCheck"]["properties"]["evidence"]
    assert "maxItems" not in evidence
    assert "maxItems=8" in evidence["description"]
    assert projected["required"] == original["required"]
    assert projected["additionalProperties"] is False
    assert projected["$defs"]["RequirementEvidence"]["additionalProperties"] is False
    assert projected["$defs"]["RequirementCheck"]["properties"]["sufficiency"]["enum"] == original["$defs"]["RequirementCheck"]["properties"]["sufficiency"]["enum"]
    assert projected["properties"]["requirements"]["items"] == original["properties"]["requirements"]["items"]
    assert wire["messages"] == original_body["messages"]
    assert wire["provider"] == original_body["provider"]
    assert wire["response_format"]["json_schema"]["strict"] is True


@pytest.mark.parametrize("profile", [p for p in PROFILES if p != HAIKU])
def test_all_other_fixed_profiles_preserve_exact_request_and_no_projection_metadata(profile):
    schema = json.loads(FIXTURE.read_bytes())
    body = payload_for(configured(profile), schema)
    before = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    wire, metadata = prepare_schema_wire(configured(profile), body, schema)
    assert wire is body
    assert json.dumps(wire, ensure_ascii=False, separators=(",", ":")).encode() == before
    assert metadata == {}
    assert PROFILES[profile].schema_transport is None


def test_property_names_annotation_data_refs_and_supported_minitems_are_preserved():
    schema = {
        "type": "object", "additionalProperties": False, "required": ["minLength"],
        "properties": {
            "minLength": {"type": "string", "minLength": 2, "maxLength": 3, "enum": ["ab"]},
            "bounded": {"type": "number", "minimum": 0, "exclusiveMaximum": 2, "multipleOf": 0.5},
            "zero": {"type": "array", "minItems": 0, "maxItems": 0, "items": {"type": "string"}},
            "one": {"type": "array", "minItems": 1, "maxItems": 1, "items": {"$ref": "#/$defs/Value"}},
            "two": {"type": "array", "minItems": 2, "items": {"type": "string"}},
        },
        "$defs": {"Value": {"type": "string", "maxLength": 9, "description": "Original description."}},
        "default": {"minLength": 99}, "examples": [{"maxItems": 17}],
    }
    before = copy.deepcopy(schema)
    wire, metadata = prepare_schema_wire(configured(), payload_for(configured(), schema), schema)
    projected = wire["response_format"]["json_schema"]["schema"]
    assert schema == before
    assert set(projected["properties"]) == set(schema["properties"])
    assert projected["properties"]["minLength"]["enum"] == ["ab"]
    assert "minLength" not in projected["properties"]["minLength"]
    assert projected["properties"]["zero"]["minItems"] == 0
    assert projected["properties"]["one"]["minItems"] == 1
    assert "maxItems" not in projected["properties"]["zero"]
    assert "maxItems" not in projected["properties"]["one"]
    assert "minItems" not in projected["properties"]["two"]
    assert projected["properties"]["one"]["items"] == {"$ref": "#/$defs/Value"}
    assert projected["$defs"]["Value"]["description"].startswith("Original description.\n")
    assert projected["default"] == {"minLength": 99}
    assert projected["examples"] == [{"maxItems": 17}]
    assert metadata["removed_bound_count"] == 9


def test_teacher_numeric_bounds_are_projected_but_local_response_validation_remains_strict():
    schema = compact_schema(TeachingDraftV5)
    wire, metadata = prepare_schema_wire(configured(), payload_for(configured(), schema), schema)
    confidence = wire["response_format"]["json_schema"]["schema"]["properties"]["confidence"]["anyOf"][0]
    assert "minimum" not in confidence and "maximum" not in confidence
    assert metadata["removed_bound_count"] == 11
    response = {
        "schema_version": "chat_response_v1", "response_type": "answer",
        "answer_text": "Synthetic answer.", "short_answer": None, "citations": [],
        "refusal_reason": None, "follow_up_questions": [], "confidence": 0.5,
    }
    ChatResponseV1.model_validate(response)
    for bad in (dict(response, confidence=2.0), dict(response, answer_text=""), dict(response, citations=["ev_1", "ev_1"])):
        with pytest.raises(ValidationError):
            ChatResponseV1.model_validate(bad)


def judgment():
    return {
        "claims": [], "body_ok": True, "specific_help": True, "scope_ok": True,
        "suggestions_ok": True, "evidence_display_ok": True, "cumulative_ok": True,
        "complete_answer": True, "coverage": "full", "missing_facets": [],
        "limitations_explicit": True, "reason": "Synthetic judgment.", "repair_fragment_ids": [],
        "attempt_evaluation_ok": True, "tutor_question_ok": True, "non_repetitive_next_action": True,
        "requirements": [{
            "requirement_id": "R1", "relevance": "related", "sufficiency": "sufficient",
            "evidence": [{"evidence_id": "ev_1", "fragment_id": "F1", "quote": "Synthetic support."}],
            "conditions_preserved": True, "response_coverage": "covered",
            "missing_information": "", "reason": "Synthetic justification.",
        }],
    }


def test_original_v5_rejects_nine_evidence_items_and_string_limits_after_projection():
    value = judgment()
    row = value["requirements"][0]
    row["evidence"] *= 8
    ReliableCheckV5.model_validate(value)
    row["evidence"].append(copy.deepcopy(row["evidence"][0]))
    with pytest.raises(ValidationError) as error:
        ReliableCheckV5.model_validate(value)
    assert any(tuple(e["loc"]) == ("requirements", 0, "evidence") for e in error.value.errors())
    for quote in ("", "x" * 1201):
        invalid = judgment()
        invalid["requirements"][0]["evidence"][0]["quote"] = quote
        with pytest.raises(ValidationError):
            ReliableCheckV5.model_validate(invalid)
    invalid = judgment()
    invalid["unexpected_field"] = True
    with pytest.raises(ValidationError):
        ReliableCheckV5.model_validate(invalid)


def test_original_semantic_requirement_quality_gates_remain_effective():
    value = judgment()
    coverage = {"requirements": [{"id": "R1"}]}
    fragments = [{"fragment_id": "F1", "evidence_id": "ev_1", "exact_text": "Synthetic support.", "complete_block": True}]
    args = {"answer_mode": "textbook", "teaching_mode": "direct"}
    assert assess_requirements(value, coverage, fragments, **args)[:2] == ([], [])
    invalid = copy.deepcopy(value)
    invalid["requirements"][0]["evidence"][0]["quote"] = "Unquoted claim."
    contract, _, _ = assess_requirements(invalid, coverage, fragments, **args)
    assert any(row["code"] == "REQUIREMENT_SOURCE_QUOTE_INVALID" for row in contract)
    invalid = copy.deepcopy(value)
    invalid["requirements"][0]["conditions_preserved"] = False
    _, defects, _ = assess_requirements(invalid, coverage, fragments, **args)
    assert any(row["code"] == "REQUIREMENT_CONDITION_LOST" for row in defects)
    invalid = copy.deepcopy(value)
    invalid["requirements"][0].update(sufficiency="partial", missing_information="Missing facet.")
    contract, defects, _ = assess_requirements(invalid, coverage, fragments, **args)
    assert any(row["code"] == "FULL_COVERAGE_WITH_REQUIREMENT_GAP" for row in contract)
    assert any(row["code"] == "INSUFFICIENT_CONTEXT_FULL_COVERAGE" for row in defects)


@pytest.fixture
def fake_provider_interface(monkeypatch):
    providers = ModuleType("generation.providers")
    providers.endpoint = lambda config, **kw: BASE_URL + "/chat/completions"
    providers.headers = lambda config, key: {"Authorization": "Bearer synthetic-key"}
    providers.payload = runtime_payload
    providers.prepare_checker_transport = lambda *args, **kwargs: None
    providers.checker_transport_enabled = lambda config: False
    providers.hydrate_checker_transport = lambda *args: pytest.fail("Unexpected compact transport")
    def decode_response(decoded, result, **kwargs):
        result.model = configured().model
        result.raw_text = json.dumps(decoded["value"])
        result.finish_reason = "stop"
    providers.decode_response = decode_response
    monkeypatch.setitem(sys.modules, "generation.providers", providers)
    from generation import capabilities
    monkeypatch.setattr(capabilities, "resolve", lambda config: None)
    monkeypatch.setattr(ModelConfig, "validate", lambda config: None)
    return providers


@pytest.mark.parametrize("status", [200, 400])
def test_actual_adapter_envelope_and_safe_metadata_match_observed_wire(monkeypatch, fake_provider_interface, status):
    from generation import adapters
    schema = json.loads(FIXTURE.read_bytes())
    messages = [{"role": "user", "content": "Synthetic private learner text."}]
    observed = []
    class Response:
        status = 200
        headers = {}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            return json.dumps({"model": configured().model, "value": {"ok": True}}).encode()
    def fake_open(envelope, **kwargs):
        observed.append(json.loads(envelope.data))
        if status == 400:
            raise HTTPError(envelope.full_url, 400, "Synthetic HTTP failure", {}, io.BytesIO(b'{"error":{"message":"Synthetic failure"}}'))
        return Response()
    monkeypatch.setattr(adapters, "open_provider", fake_open)
    result = adapters.LLMAdapter(configured(), api_key="synthetic-key").generate(messages, response_schema=schema, response_schema_name="joint_check_v5")
    assert result.request_submitted is True and len(observed) == 1
    metadata = result.diagnostic["schema_transport"]
    assert metadata["wire_schema_sha256"] == digest(observed[0]["response_format"]["json_schema"]["schema"])
    assert metadata["original_response_schema_sha256"] == EXACT_SCHEMA_SHA
    assert observed[0]["messages"] == messages
    assert (result.error is None) == (status == 200)
    assert "synthetic-key" not in json.dumps(metadata)
    assert messages[0]["content"] not in json.dumps(metadata)


def test_probe_estimate_and_metadata_use_the_same_actual_wire(monkeypatch, fake_provider_interface):
    from generation import probes
    counted = []
    class Counter:
        def __init__(self, config):
            pass
        def count(self, text):
            counted.append(json.loads(text))
            return 32
        def report(self):
            return {"method": "synthetic"}
    monkeypatch.setattr(probes, "TokenCounter", Counter)
    monkeypatch.setattr(probes, "resolve", lambda config: None)
    monkeypatch.setattr(probes, "payload", fake_provider_interface.payload)
    description = probes.description(configured(), "project", "checker")
    metadata = description["metadata"]
    assert len(counted) == 1
    actual_schema = counted[0]["response_format"]["json_schema"]["schema"]
    wire_metadata = metadata["effective_parameters"]["schema_transport"]
    assert wire_metadata["wire_schema_sha256"] == digest(actual_schema)
    expected_wire, expected_metadata = prepare_schema_wire(
        description["config"],
        runtime_payload(
            description["config"], description["messages"], description["schema"], description["name"]
        ),
        description["schema"],
    )
    assert counted[0] == expected_wire
    assert wire_metadata == expected_metadata
    assert metadata["schema_hash"] == EXACT_SCHEMA_SHA
    assert digest(description["schema"]) == EXACT_SCHEMA_SHA
    assert wire_metadata["removed_bound_count"] == 42
    assert metadata["input_tokens"] == 160


def test_current_checker_schema_changes_only_requirement_evidence_descriptions():
    legacy = json.loads(LEGACY_FIXTURE.read_bytes())
    current = json.loads(FIXTURE.read_bytes())
    assert digest(legacy) == LEGACY_SCHEMA_SHA
    assert digest(current) == EXACT_SCHEMA_SHA
    assert current == compact_schema(ReliableCheckV5)
    stripped = copy.deepcopy(current)
    descriptions = {
        ("RequirementEvidence", "evidence_id"),
        ("RequirementEvidence", "fragment_id"),
        ("RequirementEvidence", "quote"),
        ("RequirementCheck", "evidence"),
    }
    for definition, field in descriptions:
        old_field = legacy["$defs"][definition]["properties"][field]
        new_field = stripped["$defs"][definition]["properties"][field]
        assert "description" not in old_field
        assert isinstance(new_field.pop("description"), str)
    assert stripped == legacy
