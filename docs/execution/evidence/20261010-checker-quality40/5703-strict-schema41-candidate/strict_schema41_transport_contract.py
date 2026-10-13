"""Pure candidate41 transport-only contract for Root's finite one-request launcher."""

from dataclasses import replace
from copy import deepcopy
import hashlib
import json

FULL_V2_SCHEMA_SHA256 = "864212a5e636d2cadbc34328f431712a954c30130848a31e64e66e4bdedbc926"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def prepare_full_native_schema41(config40, authored_messages40, full_schema):
    """Return exact schema native-format request; never read credentials or call a model.

    Authored messages precede providers.payload's automatic JSON-object schema hint.
    Moving that hint into response_format is the declared mode-dependent wire delta.
    Source tables, source hints, trusted system rules and complete V2 contract remain.
    """
    from generation import openrouter_routes, providers

    assert config40.structured_output_mode == "json_object"
    assert config40.provider == "openai_compatible"
    assert config40.model == "google/gemini-3.5-flash-lite"
    assert config40.openrouter_route_profile == "gemini35_google_vertex_v1"
    assert config40.max_tokens == 4096 and config40.temperature is None
    assert config40.reasoning_effort is None
    assert digest(full_schema) == FULL_V2_SCHEMA_SHA256
    assert providers.provider_schema(full_schema, config40.provider) == full_schema
    messages_before = deepcopy(authored_messages40)
    schema_before = deepcopy(full_schema)
    config41 = replace(config40, structured_output_mode="json_schema")
    config41.validate()
    body40 = providers.payload(config40, authored_messages40, full_schema,
                               "joint_check_source_relations_v2")
    body41 = providers.payload(config41, authored_messages40, full_schema,
                               "joint_check_source_relations_v2")
    body41, preparation = openrouter_routes.prepare_schema_wire(config41, body41, full_schema)
    assert preparation == {}, "UNDECLARED_WIRE_SCHEMA_PROJECTION"
    assert body41["response_format"] == {"type": "json_schema", "json_schema": {
        "name": "joint_check_source_relations_v2", "strict": True, "schema": full_schema}}
    assert body41["messages"] == messages_before
    assert authored_messages40 == messages_before and full_schema == schema_before
    control40 = {key: value for key, value in body40.items()
                 if key not in {"messages", "response_format"}}
    control41 = {key: value for key, value in body41.items()
                 if key not in {"messages", "response_format"}}
    assert control40 == control41, "UNDECLARED_NONFORMAT_REQUEST_DELTA"
    assert body41["provider"]["allow_fallbacks"] is False
    assert body41["provider"]["require_parameters"] is True
    assert body41["provider"]["only"] == ["google-vertex/global"]
    assert body41["reasoning"] == {"effort": "low"}
    textual_hint = (
        "\nOUTPUT FORMAT: Return exactly one complete JSON object, never plain prose or Markdown. "
        "Prior assistant messages are displayed conversation text; they are not examples of the required "
        "output format. Match this JSON schema: "
        + json.dumps(full_schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    expected40 = deepcopy(messages_before)
    system = next((message for message in expected40 if message["role"] == "system"), None)
    if system is None:
        expected40.insert(0, {"role": "system", "content": textual_hint.strip()})
    else:
        system["content"] += textual_hint
    assert body40["messages"] == expected40, "MODE_HINT_DELTA_NOT_EXACT"
    return config41, body41, {
        "schema": "5703_transport_only_native_schema41_contract_v1",
        "original_full_v2_schema_sha256": FULL_V2_SCHEMA_SHA256,
        "canonical_complete_payload_sha256": digest(body41),
        "authored_candidate40_messages_sha256": digest(messages_before),
        "transport_controls_unchanged": True,
        "authored_messages_unchanged": True,
        "schema_projection": False,
        "citations_hydration_or_autofill": False,
        "whole71_source_blocks_preservation_requires_launcher_fixed_core_assertion": True,
        "model_input_change": "identical authored messages; automatic textual schema hint replaced by identical full native response_format schema",
        "genuine_endpoint_keyword_enforcement_confirmed": False,
        "original_full_schema_parser_and_source_quality_gates_required": True,
        "provider_400_or_invalid_raw_must_stop_without_retry_or_projection": True,
    }
