"""Synthetic structural controls; no model, app service or database is used."""

import hashlib
import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from generation.reliability_v4 import compact_schema
from generation.source_relations_v2 import ReliableUnitCheck, scoped_syntactic_units

MODULE_PATH = Path(__file__).resolve().parents[2] / "generation" / "lossless_unit_findings_v1.py"
SPEC = importlib.util.spec_from_file_location("candidate_output_projection", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
# Dataclasses resolve their own module during import.
codec = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = codec
SPEC.loader.exec_module(codec)


def fixture():
    texts = [
        "If enabled, the module does not emit two sparks. α😀",
        "Two available modes are named red and blue.",
        "Another source.",
    ]
    fragments = [
        {
            "fragment_id": f"F{i:03d}",
            "evidence_id": "ev1" if i < 3 else "ev2",
            "exact_text": text,
            "complete_block": True,
            "block_kind": "prose",
        }
        for i, text in enumerate(texts, 1)
    ]
    bases = [
        "textbook",
        "problem_input",
        "derived_calculation",
        "general_knowledge",
        "nonfactual",
        "evidence_limitation",
    ]
    claims, bindings, parents, verdicts = [], [], [], []
    for i, basis in enumerate(bases, 1):
        cid = f"claim_original_long_identity_{i:03d}"
        text = f"Original draft assertion {i}."
        cited = basis in {"textbook", "derived_calculation"}
        citation = {"evidence_id": "ev1", "allowed_fragment_ids": ["F001", "F002"]}
        claims.append(
            {
                "claim_id": cid,
                "text": text,
                "answer_field": "answer_text",
                "start": 0,
                "end": len(text),
                "evidence_ids": ["ev1"] if cited else [],
            }
        )
        bindings.append({"claim_id": cid, "citations": [citation] if cited else []})
        unit = {
            "unit_id": "U01",
            "start": 0,
            "end": len(text),
            "text": text,
            "text_hash": hashlib.sha256(text.encode()).hexdigest(),
        }
        parents.append(
            {
                "claim_id": cid,
                "full_claim": text,
                "actual_citation_scope": [citation] if cited else [],
                "units": [unit],
            }
        )
        row = {
            "claim_id": cid,
            "reason": "Do not remove this original reason.",
            "basis": basis,
        }
        if basis not in {"nonfactual", "evidence_limitation"}:
            row["status"] = "partial"
        if cited:
            row["citations"] = [
                {
                    "evidence_id": "ev1",
                    "fragment_ids": ["F001", "F002"],
                    "relation": "supporting",
                }
            ]
        if basis == "textbook":
            row["units"] = [
                {
                    "unit_id": "U01",
                    "status": "unsupported",
                    "fragment_ids": ["F001", "F002"],
                    "relation_preserved": False,
                    "conditions_preserved": False,
                    "reason": "The negation is necessary.",
                }
            ]
        if basis == "problem_input":
            row["problem_quote"] = "The learner supplied a quantity of two."
        if basis == "derived_calculation":
            row["derivation"] = {
                "formula_basis": "textbook",
                "formula_fragment_id": "F001",
                "formula_quote": texts[0],
                "expression": "x+1",
                "result": "3",
                "result_quote": "3",
                "result_unit": "items",
                "units_consistent": False,
                "formula_applicable": False,
                "inputs": [
                    {
                        "name": "x1",
                        "value": "2",
                        "unit": "items",
                        "quote": "two sparks",
                        "origin": "textbook",
                        "fragment_id": "F001",
                    }
                ],
            }
        verdicts.append(row)
    packet = {
        "SOURCE_RELATION_POLICY": "source_relation_contract_v2",
        "CLAIMS": claims,
        "ACTUAL_CITATION_BINDINGS": bindings,
        "SOURCE_SYNTACTIC_UNITS": parents,
        "SOURCE_FRAGMENTS": fragments,
        "question": "The learner supplied a quantity of two.",
        "current_problem": "",
        "CONTEXT_COVERAGE": {"requirements": [{"id": "req_original_1"}]},
    }
    packet["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(claims, bindings, fragments)
    full = {
        key: False
        for key, schema in compact_schema(ReliableUnitCheck)["properties"].items()
        if schema.get("type") == "boolean"
    }
    full.update(
        claims=verdicts,
        coverage="supported_partial",
        missing_facets=["a required condition"],
        reason="Do not assert success from structural hydration.",
        repair_fragment_ids=["F002"],
        requirements=[
            {
                "requirement_id": "req_original_1",
                "relevance": "related",
                "sufficiency": "partial",
                "evidence": [
                    {"evidence_id": "ev1", "fragment_id": "F001", "quote": texts[0]},
                    {"evidence_id": "ev1", "fragment_id": "F002", "quote": texts[1]},
                ],
                "conditions_preserved": False,
                "response_coverage": "partial",
                "missing_information": "Unresolved quantity scope.",
                "reason": "Needs evidence.",
            }
        ],
    )
    return packet, full


def test_all_variants_full_canonical_roundtrip_preserves_every_negative_and_order():
    packet, full = fixture()
    context = codec.build_context(packet)
    encoded = codec.encode_findings(full, context)
    restored = codec.hydrate_findings(encoded, context)
    assert restored == full
    assert ReliableUnitCheck.model_validate(restored).model_dump() == full
    assert codec.encode_findings(restored, context) == encoded
    assert restored["claims"][0]["units"][0]["status"] == "unsupported"
    assert restored["claims"][0]["units"][0]["conditions_preserved"] is False
    assert all(
        restored[key] is False
        for key in (
            "body_ok",
            "specific_help",
            "scope_ok",
            "suggestions_ok",
            "evidence_display_ok",
            "cumulative_ok",
            "complete_answer",
            "limitations_explicit",
            "attempt_evaluation_ok",
            "tutor_question_ok",
            "non_repetitive_next_action",
        )
    )


def test_fragment_full_text_is_explicit_fixed_id_without_duplicate_source_text():
    packet, full = fixture()
    context = codec.build_context(packet)
    encoded = codec.encode_findings(full, context)
    evidence = encoded["rs"][0]["ev"][0]
    assert evidence == {
        "e": "ev1",
        "f": "F001",
        "p": "F001",
    }
    assert codec.hydrate_findings(encoded, context)["requirements"][0]["evidence"][0][
        "quote"
    ].endswith("α😀")
    instructions = codec.reference_instructions(context)
    assert "whole_fragment_quote_ids" in instructions
    assert packet["SOURCE_FRAGMENTS"][0]["exact_text"] not in instructions
    assert "no ID is a default" in instructions


def test_uncatalogued_partial_quote_rejects_without_widening_and_literal_quotes_roundtrip():
    packet, full = fixture()
    context = codec.build_context(packet)
    encoded = codec.encode_findings(full, context)
    assert encoded["rs"][0]["ev"][0]["p"] == "F001"
    assert encoded["cs"][1]["pq"] == full["claims"][1]["problem_quote"]
    assert encoded["cs"][2]["d"]["fq"] == full["claims"][2]["derivation"]["formula_quote"]
    assert codec.hydrate_findings(encoded, context) == full
    full["requirements"][0]["evidence"][0]["quote"] = "does not emit two sparks"
    before = deepcopy(full)
    with pytest.raises(ValueError, match="no widening"):
        codec.encode_findings(full, context)
    assert full == before


def test_nullable_negative_calculation_refs_remain_null_without_positive_or_citation_fill():
    packet, full = fixture()
    calculation = full["claims"][2]
    calculation["status"] = "unsupported"
    calculation["derivation"]["formula_fragment_id"] = None
    calculation["derivation"]["inputs"][0]["fragment_id"] = None
    before = deepcopy(calculation)
    context = codec.build_context(packet)
    projected = codec.encode_full(full, context)
    assert projected["cs"][2]["d"]["ff"] is None
    assert projected["cs"][2]["d"]["ins"][0]["f"] is None
    restored = codec.decode(projected, context)
    assert restored == full
    assert restored["claims"][2] == before
    assert restored["claims"][2]["status"] == "unsupported"
    assert restored["claims"][2]["derivation"]["formula_applicable"] is False
    assert restored["claims"][2]["derivation"]["units_consistent"] is False
    assert restored["body_ok"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x.pop("bo"),
        lambda x: x.update(body_ok=True),
        lambda x: x.update(bo="false"),
        lambda x: x.update(v="scoped_compact_v6"),
        lambda x: x.update(h="0" * 64),
        lambda x: x["cs"].pop(),
        lambda x: x["cs"].append(deepcopy(x["cs"][0])),
        lambda x: x["cs"][0].update(c="C999"),
        lambda x: x["cs"][0].update(c=[]),
        lambda x: x["cs"][0]["us"].pop(),
        lambda x: x["cs"][0]["us"].append(deepcopy(x["cs"][0]["us"][0])),
        lambda x: x["cs"][0]["us"][0].update(u="U02"),
        lambda x: x["cs"][0]["us"][0].update(fs=["F003"]),
        lambda x: x["cs"][0]["ci"][0].update(fs=["F001"]),
        lambda x: x["cs"][0]["ci"][0].update(fs=["F003"]),
        lambda x: x["cs"][0]["ci"][0].update(fs=["F001", "F001"]),
        lambda x: x["cs"][0]["us"][0].update(rp=1),
        lambda x: x["cs"][2]["d"].update(ff="F003"),
        lambda x: x["cs"][2]["d"]["ins"][0].update(f="F003"),
        lambda x: x["rs"].pop(),
        lambda x: x["rs"].append(deepcopy(x["rs"][0])),
        lambda x: x["rs"][0].update(k="R999"),
        lambda x: x["rs"][0]["ev"][0].update(e="ev2"),
        lambda x: x["rs"][0]["ev"][0].update(f="F999"),
        lambda x: x["rs"][0]["ev"][0].update(p=[True, 2]),
        lambda x: x["rs"][0]["ev"][0].update(p=[0, False]),
        lambda x: x["rs"][0]["ev"][0].update(p=[0.0, 2]),
        lambda x: x["rs"][0]["ev"][0].update(p=[-1, 2]),
        lambda x: x["rs"][0]["ev"][0].update(p=[2, 2]),
        lambda x: x["rs"][0]["ev"][0].update(p=[3, 2]),
        lambda x: x["rs"][0]["ev"][0].update(p=[0, 9999]),
        lambda x: x["rs"][0]["ev"][0].update(q="invented"),
        lambda x: x["rs"][0]["ev"].append(deepcopy(x["rs"][0]["ev"][0])),
        lambda x: x.update(rf=["F999"]),
    ],
)
def test_malformed_missing_duplicate_foreign_mixed_keys_or_stale_output_fails_closed(
    mutation,
):
    packet, full = fixture()
    context = codec.build_context(packet)
    encoded = codec.encode_findings(full, context)
    mutation(encoded)
    with pytest.raises(ValueError):
        codec.hydrate_findings(encoded, context)


@pytest.mark.parametrize("bad", [None, [], "{}", 1, True])
def test_invalid_top_level_is_value_error(bad):
    packet, _ = fixture()
    with pytest.raises(ValueError):
        codec.hydrate_findings(bad, codec.build_context(packet))


def test_context_frozen_by_value_and_changed_negation_or_binding_is_stale():
    packet, full = fixture()
    context = codec.build_context(packet)
    encoded = codec.encode_findings(full, context)
    packet["SOURCE_FRAGMENTS"][0]["exact_text"] = "If enabled, the module emits two sparks."
    assert (
        "does not emit"
        in codec.hydrate_findings(encoded, context)["requirements"][0]["evidence"][0]["quote"]
    )
    with pytest.raises(ValueError, match="stale"):
        codec.hydrate_findings(encoded, codec.build_context(packet))
    changed = context.packet
    changed["ACTUAL_CITATION_BINDINGS"][0]["citations"][0]["allowed_fragment_ids"] = ["F002"]
    changed["SOURCE_SYNTACTIC_UNITS"][0]["actual_citation_scope"] = changed[
        "ACTUAL_CITATION_BINDINGS"
    ][0]["citations"]
    with pytest.raises(ValueError, match="stale"):
        codec.hydrate_findings(encoded, codec.build_context(changed))


def test_changed_canonical_schema_cannot_reuse_an_old_context(monkeypatch):
    packet, full = fixture()
    context = codec.build_context(packet)
    encoded = codec.encode_findings(full, context)
    original = codec.compact_schema

    def changed_schema(model):
        changed = original(model)
        changed["properties"]["reason"]["maxLength"] += 1
        return changed

    monkeypatch.setattr(codec, "compact_schema", changed_schema)
    with pytest.raises(ValueError, match="context digest"):
        codec.hydrate_findings(encoded, context)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x["CLAIMS"].append(deepcopy(x["CLAIMS"][0])),
        lambda x: x["SOURCE_FRAGMENTS"].append(deepcopy(x["SOURCE_FRAGMENTS"][0])),
        lambda x: x["SOURCE_SYNTACTIC_UNITS"][0]["units"][0].update(start=True),
        lambda x: x["SOURCE_SYNTACTIC_UNITS"][0]["units"][0].update(text="Changed predicate."),
        lambda x: x["SOURCE_SYNTACTIC_UNITS"][0].update(full_claim="Changed predicate."),
        lambda x: x["SOURCE_SYNTACTIC_UNITS"][0].update(actual_citation_scope=[]),
    ],
)
def test_bad_original_context_is_rejected(mutation):
    packet, _ = fixture()
    mutation(packet)
    with pytest.raises(ValueError):
        codec.build_context(packet)


def test_fixed_id_selection_does_not_certify_conditions_or_turn_negative_flags_positive():
    packet, full = fixture()
    context = codec.build_context(packet)
    encoded = codec.encode_findings(full, context)
    restored = codec.hydrate_findings(encoded, context)
    assert (
        restored["requirements"][0]["evidence"][0]["quote"]
        == packet["SOURCE_FRAGMENTS"][0]["exact_text"]
    )
    assert restored["requirements"][0]["conditions_preserved"] is False
    assert restored["body_ok"] is False
    # A fixed original-text ID is structural identity, not semantic sufficiency.


def test_schema_preserves_all_original_caps_and_requires_model_fields():
    packet, _ = fixture()
    context = codec.build_context(packet)
    schema = codec.wire_schema(context)
    assert set(schema["required"]) == set(schema["properties"])
    original = compact_schema(ReliableUnitCheck)
    for name, definition in original["$defs"].items():
        transformed = schema["$defs"][name]
        assert len(definition["properties"]) == len(transformed["properties"])
        for field, value in definition["properties"].items():
            if name == "RequirementEvidence" and field == "quote":
                continue
            actual = transformed["properties"][codec.KEYS[field]]
            for cap in ("minLength", "maxLength", "minItems", "maxItems", "pattern"):
                if cap in value:
                    assert actual[cap] == value[cap]
    assert codec.SCHEMA_NAME == "lossless_unit_findings_v1"


def test_original_quote_cap_and_reason_cap_are_not_reduced_or_bypassed():
    packet, full = fixture()
    packet["SOURCE_FRAGMENTS"][0]["exact_text"] = "n" * 1200
    full["requirements"][0]["evidence"][0]["quote"] = "n" * 1200
    full["claims"][0]["reason"] = "r" * 800
    full["claims"][0]["units"][0]["reason"] = "u" * 200
    full["requirements"][0]["reason"] = "s" * 1200
    full["reason"] = "t" * 1600
    context = codec.build_context(packet)
    encoded = codec.encode_findings(full, context)
    assert codec.hydrate_findings(encoded, context) == full
    packet["SOURCE_FRAGMENTS"][0]["exact_text"] += "n"
    context = codec.build_context(packet)
    encoded["h"] = context.digest
    encoded["rs"][0]["ev"][0]["p"] = [0, 1201]
    with pytest.raises(ValueError, match="fixed quote ID"):
        codec.hydrate_findings(encoded, context)


def request_fixture():
    from generation.types import ModelConfig

    return SimpleNamespace(
        checker_output_policy=codec.VERSION,
        checker_config=None,
        config=ModelConfig(),
        enhancement_version="learning_enhancement_v1",
        mode="interactive_chat",
        condition="E1",
        answer_mode="textbook",
        source_relation_policy="source_relation_contract_v2",
        reliability_policy="evidence_reliability_v5",
        joint_checker_policy="typed_joint_v5",
        checker_schema_policy=None,
        teaching_context={"turn_role": "user_question"},
    )


def test_default_off_does_not_inspect_incompatible_or_partial_legacy_request():
    codec.validate_request(SimpleNamespace())
    codec.validate_request(SimpleNamespace(checker_output_policy=None, mode="benchmark"))
    codec.validate_request(request_fixture())


@pytest.mark.parametrize(
    "fields",
    [
        {"checker_output_policy": "unknown"},
        {"enhancement_version": None},
        {"mode": "benchmark"},
        {"condition": "E0"},
        {"answer_mode": "general"},
        {"source_relation_policy": None},
        {"reliability_policy": "evidence_reliability_v4"},
        {"joint_checker_policy": "scoped_compact_v6"},
        {"checker_schema_policy": "textbook_v2_simple_schema_v1"},
        {"teaching_context": {"turn_role": "attempt"}},
    ],
)
def test_explicit_incompatible_policy_scope_is_rejected(fields):
    request = request_fixture()
    request.__dict__.update(fields)
    with pytest.raises(ValueError):
        codec.validate_request(request)


def test_explicit_research_or_prompt_config_is_rejected_but_json_object_keeps_full_gate():
    from dataclasses import replace

    request = request_fixture()
    with pytest.raises(ValueError):
        codec.validate_request(request, research_unchecked=True)
    request.config = replace(request.config, structured_output_mode="json_object")
    codec.validate_request(request)
    request.config = replace(request.config, structured_output_mode="prompt")
    with pytest.raises(ValueError):
        codec.validate_request(request)


def test_compact_provider_is_rejected_without_route_mutation(monkeypatch):
    import generation.providers

    request = request_fixture()
    monkeypatch.setattr(generation.providers, "checker_transport_enabled", lambda _: True)
    original = request.config
    with pytest.raises(ValueError):
        codec.validate_request(request)
    assert request.config is original


def test_schema_mutating_actual_route_is_rejected_before_teacher_but_json_object_is_noop():
    from dataclasses import replace

    from generation.openrouter_routes import PROFILES, prepare_schema_wire
    from generation.types import ModelConfig

    profile = "haiku55_google_vertex_low_v1"
    request = request_fixture()
    request.config = ModelConfig(
        provider="openai_compatible",
        model=PROFILES[profile].model,
        base_url="https://openrouter.ai/api/v1",
        max_tokens=4096,
        window_tokens=10000,
        temperature=None,
        openrouter_route_profile=profile,
    )
    with pytest.raises(ValueError):
        codec.validate_request(request)
    request.config = replace(request.config, structured_output_mode="json_object")
    codec.validate_request(request)
    packet, _ = fixture()
    schema = codec.wire_schema(codec.build_context(packet))
    body = {
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": codec.canonical(schema)}],
    }
    original = deepcopy(body)
    actual, metadata = prepare_schema_wire(request.config, body, schema)
    assert actual == original
    assert metadata == {}


@pytest.mark.parametrize("encoding", ["objects", "fragment_table", "v1", "v2"])
def test_prepare_preserves_source_packet_and_supplies_same_pure_schema_for_accounting(
    encoding,
):
    from generation import checker_encoding, checker_encoding_v2
    from generation.binding_repair import table_fragments
    from generation.source_relations_v2 import scoped_syntactic_units

    packet, full = fixture()
    packet.update(
        answer_mode="textbook",
        LEARNER_TURN={"turn_role": "user_question"},
        ATTEMPT_EVALUATION=None,
        TUTOR_QUESTION=None,
    )
    # V2's existing input encoder verifies the real unit partition, not a mirror.
    packet["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(
        packet["CLAIMS"], packet["ACTUAL_CITATION_BINDINGS"], packet["SOURCE_FRAGMENTS"]
    )
    transport = {
        "objects": lambda value: value,
        "fragment_table": table_fragments,
        "v1": checker_encoding.encode,
        "v2": checker_encoding_v2.encode,
    }[encoding](packet)
    messages = [
        {"role": "system", "content": "Use the complete canonical checker contract."},
        {"role": "user", "content": json.dumps(transport, ensure_ascii=False)},
    ]
    before = deepcopy(messages)
    prepared = codec.prepare(messages, compact_schema(ReliableUnitCheck))
    assert messages == before
    assert prepared.messages[-1] == messages[-1]
    assert prepared.context.packet == packet
    assert prepared.schema == codec.wire_schema(prepared.context)
    assert prepared.context.descriptor()["source_entailment_certified"] is False
    assert codec.decode(codec.encode_full(full, prepared.context), prepared.context) == full


@pytest.mark.parametrize(
    "change", ["foreign_schema", "unknown_encoding", "attempt", "foreign_mode"]
)
def test_prepare_rejects_foreign_schema_encoding_and_revision_scope(change):
    packet, _ = fixture()
    packet.update(
        answer_mode="textbook",
        LEARNER_TURN={"turn_role": "user_question"},
        ATTEMPT_EVALUATION=None,
        TUTOR_QUESTION=None,
    )
    schema = compact_schema(ReliableUnitCheck)
    if change == "foreign_schema":
        schema["properties"]["body_ok"] = {"type": "string"}
    elif change == "unknown_encoding":
        packet["CHECKER_INPUT_ENCODING"] = {"version": "scoped_compact_v6"}
    elif change == "attempt":
        packet["LEARNER_TURN"]["turn_role"] = "attempt"
    else:
        packet["answer_mode"] = "general"
    messages = [
        {"role": "system", "content": "Original checker."},
        {"role": "user", "content": codec.canonical(packet)},
    ]
    with pytest.raises(ValueError):
        codec.prepare(messages, schema)
