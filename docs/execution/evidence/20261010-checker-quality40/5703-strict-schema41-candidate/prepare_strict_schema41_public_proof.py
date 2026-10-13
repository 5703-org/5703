"""Pure full-contract schema transport feasibility; no model, database, or secret access."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
MAIN = Path(r"E:\5703\learning-assistant")
OUT = ROOT / "5703-strict-schema41-candidate"


def audit(event, args):
    if event.startswith("socket.") or event in {"subprocess.Popen", "os.system"}:
        raise RuntimeError("OFFLINE_PROOF_NETWORK_OR_PROCESS_DENIED")
    if event == "open":
        path = args[0]
        mode = args[1]
        flags = args[2]
        writing = isinstance(mode, str) and any(char in mode for char in "wax+")
        writing = writing or isinstance(flags, int) and bool(flags & (1 | 2 | 64 | 512))
        if isinstance(path, (str, bytes)):
            resolved = Path(path).resolve()
            if writing and not resolved.is_relative_to(OUT):
                raise RuntimeError("OFFLINE_PROOF_WRITE_OUTSIDE_OWN_WORKSPACE_DENIED")
            if any(part.lower() in {".secrets", ".codex", ".aws"} for part in resolved.parts):
                raise RuntimeError("OFFLINE_PROOF_SECRET_OR_SESSION_PATH_DENIED")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def pin(path):
    blob = path.read_bytes()
    return {"path": str(path), "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}


def main():
    OUT.mkdir(exist_ok=True)
    sys.addaudithook(audit)
    sys.path[:0] = [str(MAIN), str(MAIN / ".venv" / "Lib" / "site-packages")]
    from generation import capabilities, openrouter_routes, providers
    from generation.reliability_v4 import compact_schema
    from generation.source_relations_v2 import ReliableUnitCheck
    from generation.types import ModelConfig

    schema = compact_schema(ReliableUnitCheck)
    expected_digest = "864212a5e636d2cadbc34328f431712a954c30130848a31e64e66e4bdedbc926"
    digest = hashlib.sha256(encoded(schema)).hexdigest()
    assert digest == expected_digest, "ORIGINAL_FULL_V2_SCHEMA_CHANGED"
    wire_schema = providers.provider_schema(schema, "openai_compatible")
    assert wire_schema == schema, "PROVIDER_SCHEMA_CHANGED_FULL_V2_CONTRACT"

    keyword_counts = Counter()
    keyword_paths = {}
    schema_node_count = 0
    maximum_depth = 0

    def visit(node, path="#", depth=0):
        nonlocal schema_node_count, maximum_depth
        if not isinstance(node, dict):
            return
        schema_node_count += 1
        maximum_depth = max(maximum_depth, depth)
        for key in node:
            keyword_counts[key] += 1
            keyword_paths.setdefault(key, []).append(path + "/" + key)
        for key in ("properties", "$defs", "definitions"):
            mapping = node.get(key, {})
            if isinstance(mapping, dict):
                for name, child in mapping.items():
                    visit(child, path + "/" + key + "/" + name, depth + 1)
        for key in ("anyOf", "oneOf", "allOf", "prefixItems"):
            sequence = node.get(key, [])
            if isinstance(sequence, list):
                for index, child in enumerate(sequence):
                    visit(child, path + "/" + key + "/" + str(index), depth + 1)
        for key in ("items", "additionalProperties", "not", "if", "then", "else"):
            if isinstance(node.get(key), dict):
                visit(node[key], path + "/" + key, depth + 1)

    visit(schema)
    shared = dict(
        provider="openai_compatible", model="google/gemini-3.5-flash-lite",
        base_url="https://openrouter.ai/api/v1", temperature=None,
        reasoning_effort=None, window_tokens=131072, max_tokens=4096,
        timeout_seconds=60, openrouter_route_profile="gemini35_google_vertex_v1",
        capability_version=None, capabilities=None,
    )
    schema_config = ModelConfig(**shared, structured_output_mode="json_schema")
    object_config = ModelConfig(**shared, structured_output_mode="json_object")
    schema_config.validate()
    object_config.validate()
    route = openrouter_routes.resolve(schema_config)
    assert route.checker_transport is None and route.schema_transport is None
    assert openrouter_routes.preferences(schema_config) == openrouter_routes.preferences(object_config)
    # Minimal public synthetic input isolates compiler transport behavior only.
    messages = [{"role": "system", "content": "PUBLIC OFFLINE TRANSPORT CONTROL"},
                {"role": "user", "content": "PUBLIC SYNTHETIC INPUT; NO MODEL CALL"}]
    schema_body = providers.payload(schema_config, messages, schema, "joint_check_source_relations_v2")
    object_body = providers.payload(object_config, messages, schema, "joint_check_source_relations_v2")
    prepared, diagnostic = openrouter_routes.prepare_schema_wire(schema_config, schema_body, schema)
    assert prepared == schema_body and diagnostic == {}
    assert prepared["response_format"] == {
        "type": "json_schema", "json_schema": {
            "name": "joint_check_source_relations_v2", "strict": True, "schema": schema}}
    assert prepared["messages"] == messages
    assert prepared["reasoning"] == {"effort": "low"}
    assert prepared["provider"] == {
        "order": ["google-vertex/global"], "only": ["google-vertex/global"],
        "allow_fallbacks": False, "require_parameters": True,
        "max_price": {"prompt": 0.3, "completion": 2.5}}
    textbook = schema["$defs"]["TextbookUnitClaim"]
    assert "citations" in textbook["required"]
    assert "units" in textbook["required"]
    assert "attempt_evaluation_ok" in schema["required"]
    assert textbook["additionalProperties"] is False
    assert "oneOf" not in keyword_counts and "discriminator" not in keyword_counts
    assert "uniqueItems" not in keyword_counts
    known_protocol_caps = capabilities.defaults("openai_compatible", shared["model"], shared["base_url"])
    declared = ModelConfig(**{**shared, "capability_version": capabilities.VERSION,
                             "capabilities": known_protocol_caps}, structured_output_mode="json_schema")
    capabilities.validate(declared)
    assert providers.payload(declared, messages, schema, "joint_check_source_relations_v2")["response_format"] == prepared["response_format"]

    proof = {
        "schema": "5703_full_v2_native_json_schema_transport41_pure_proof_v1",
        "status": "OFFLINE_PREPARED_NO_MODEL_CREDENTIAL_OR_DATABASE_ACCESS",
        "main_source_pins": [pin(MAIN / "generation" / name) for name in
            ("providers.py", "openrouter_routes.py", "capabilities.py", "types.py",
             "reliability_v4.py", "source_relations_v2.py")],
        "canonical_original_full_schema_sha256": digest,
        "canonical_original_full_schema_bytes": len(encoded(schema)),
        "provider_schema_exactly_canonical": wire_schema == schema,
        "schema_required_citations_and_units_unchanged": True,
        "required_attempt_evaluation_ok_unchanged": True,
        "schema_node_count_unexpanded": schema_node_count,
        "maximum_depth_unexpanded": maximum_depth,
        "schema_keyword_counts": dict(sorted(keyword_counts.items())),
        "schema_keyword_paths": {key: keyword_paths[key] for key in
            ("const", "$ref", "$defs", "anyOf", "default", "minLength", "maxLength") if key in keyword_paths},
        "wire_projection_policy": None,
        "compact_hydration_transport_enabled": False,
        "route_profile": shared["openrouter_route_profile"],
        "declared_model": shared["model"],
        "requested_provider_preferences": prepared["provider"],
        "effective_reasoning": prepared["reasoning"],
        "json_schema_response_format_without_schema": {
            "type": prepared["response_format"]["type"],
            "json_schema": {"name": prepared["response_format"]["json_schema"]["name"], "strict": True}},
        "local_types_and_route_validation_passed": True,
        "runtime_protocol_default_mode_guard_passed": True,
        "observed_live_endpoint_schema_support": False,
        "whole_actual_candidate40_wire_compared": False,
        "whole_actual_candidate41_wire_bytes": None,
        "local_full_schema_and_source_quality_gates_must_remain": True,
        "paid_request_budget_or_credential_allocated": False,
        "model_calls": 0, "database_calls": 0,
        "api_keys_read_or_exported": False,
        "notes": [
            "Changing saved mode removes automatic textual schema hint and moves the identical schema into response_format; candidate40 authored messages must otherwise remain exact.",
            "This synthetic proof is not the full actual wire size/pin; Root launcher must freeze actual candidate41 messages and full body before any POST.",
            "Gemini/OpenRouter endpoint translation and unsupported-keyword enforcement are not established by pure local serialization.",
            "Do not project unsupported keywords, fill citations, alter returned raw, loosen validation, enable fallback, or mark source entailment as schema certified."]}
    (OUT / "FULL_V2_CANONICAL_SCHEMA41.json").write_bytes(encoded(schema))
    (OUT / "STRICT_SCHEMA41_PURE_TRANSPORT_PROOF.json").write_bytes(encoded(proof))
    print(json.dumps({"status": proof["status"], "schema_digest": digest,
                      "schema_bytes": len(encoded(schema)), "schema_keyword_counts": proof["schema_keyword_counts"],
                      "proof_pin": pin(OUT / "STRICT_SCHEMA41_PURE_TRANSPORT_PROOF.json"),
                      "schema_pin": pin(OUT / "FULL_V2_CANONICAL_SCHEMA41.json")}, indent=2))


if __name__ == "__main__":
    main()
