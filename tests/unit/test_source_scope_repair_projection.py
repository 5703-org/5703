"""Reason-only local-patch transport; synthetic fixtures are not quality labels."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from generation import GenerationService, ModelConfig, RequestBudget
from generation.adapters import chat_value
from generation.checked import _compact_claim_patch_feedback, _json as service_json
from generation.checker_encoding import dumps as transport_json
from generation.local_repair import VERSION as CLAIM_PATCH_POLICY
from generation.reliability_v5 import evaluate_technical_entity_bindings
from generation.reliability_v4 import normalize_judgment
from retrieval.source_spans import map_fragments, text_hash
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script

COLLISION = "UNRESOLVED_TECHNICAL_ENTITY_COLLISION"
SCOPE = "SOURCE_SCOPE_CONTEXT_NOT_SELECTED"
SHORT_COLLISION = (
    "Selected support lacks this identifier; recheck the same-slot source witness. "
    "No alias or entailment is certified."
)
LONG_COLLISION = (
    "The claimed identifier is absent from its selected supporting union; a model "
    "reason cannot establish a source alias. A selected source supplies the same "
    "proposition with a one-edit different identifier in that slot. The model reason "
    "cannot exempt this source-binding conflict. Resolve this binding before "
    "publication; this is not a scientific falsehood verdict or an entailment certificate."
)
SHORT_SCOPE = (
    "Leading scope absent from selected support; recheck allowed source context. "
    "Occurrence alone is not support."
)
LONG_SCOPE = (
    "A literal leading scope is absent from this claim's own selected supporting union "
    "but occurs in a complete fragment allowed by the same actually supporting "
    "citation. Re-evaluate the source context or the stated scope. A candidate "
    "occurrence, heading or literal spelling does not certify support; aliases and "
    "semantic scope inheritance are not assessed by this diagnostic."
)
IDENTITY = "The system uses ALFB to transfer energy."
STORAGE = "Light energy is converted into chemical energy and temporarily stored in ALFA."
CONTEXT = "The heat-dependent reactions produce ALFA."
SOURCE = " ".join((IDENTITY, STORAGE, CONTEXT))
BODY = (
    "The system uses ALFA to transfer energy [ev_001]. "
    "The heat-dependent reactions store chemical energy in ALFA [ev_001]."
)
MARKER = "\nREPAIR_DATA_JSON:\n"


class CapturedRepairWire(BaseException):
    """Stop specifically at the third scripted call, before any repair result."""


def test_projection_is_nonmutating_and_changes_only_whitelisted_structural_reason():
    feedback = {
        "structural_issues": [
            {
                "code": COLLISION,
                "reason": LONG_COLLISION,
                "claim_id": "c1",
                "source_identifiers": ["ALFB"],
                "selected_fragment_ids": ["F1"],
                "source_entailment_certified": False,
                "publication_override": False,
            },
            {
                "code": SCOPE,
                "reason": SHORT_SCOPE,
                "claim_id": "c2",
                "leading_scope": "heat-dependent reactions",
                "binding_recheck_required": True,
            },
            {"code": "OTHER", "reason": LONG_COLLISION},
        ],
        "draft": {"answer_text": BODY},
        "original_claims": [{"text": BODY}],
        "judgment": {"body_ok": True, "reason": LONG_COLLISION},
        "source_repair_candidates": [{"exact_text": SOURCE}],
        "unrecognized_metadata": {"code": COLLISION, "reason": LONG_COLLISION},
    }
    untouched = deepcopy(feedback)
    expected = deepcopy(feedback)
    expected["structural_issues"][0]["reason"] = SHORT_COLLISION
    projected = _compact_claim_patch_feedback(feedback)
    assert feedback == untouched and projected == expected
    assert projected is not feedback
    old = deepcopy(feedback)
    old["structural_issues"][1]["reason"] = LONG_SCOPE
    saving = len(transport_json(old).encode()) - len(transport_json(projected).encode())
    assert saving == len(LONG_SCOPE) - len(SHORT_SCOPE) + len(LONG_COLLISION) - len(SHORT_COLLISION)
    assert saving >= 443


def test_actual_service_third_wire_preserves_raw_guard_and_compacts_two_reasons():
    value = req(
        question="Explain the system's energy transfer and storage.",
        answer_mode="textbook",
        teaching_context={"teaching_mode": "direct", "help_level": 0},
        joint_checker_policy="typed_joint_v5",
        repair_policy=CLAIM_PATCH_POLICY,
        config=ModelConfig(tokenizer_provider="estimate"),
    )
    evidence, mapping = deepcopy(value.evidence), deepcopy(value.source_map)
    evidence[0].update(text=SOURCE, text_hash=text_hash(SOURCE), section="Authored system")
    mapping["c1"].update(chunk_text=SOURCE, chunk_hash=text_hash(SOURCE))
    mapping["c1"]["units"][0].update(cleaned_text=SOURCE, text_hash=text_hash(SOURCE))
    mapping["c1"]["spans"][0].update(end=len(SOURCE), chunk_end=len(SOURCE))
    value = replace(value, evidence=evidence, source_map=mapping)
    untouched = deepcopy((value.evidence, value.source_map))
    full_fragments, mapping_issues = map_fragments(value.evidence, value.source_map)
    assert value.source_block_policy == "legacy_source_blocks_v1"
    assert not mapping_issues and len(full_fragments) == 3
    full_by_text = {f["exact_text"].strip(): f for f in full_fragments}
    original = {}

    def selected_support(messages):
        data = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
        if "CHECKER_INPUT_ENCODING" in data:
            from generation.checker_encoding import decode

            data = decode(data)
        if "SOURCE_FRAGMENT_TABLE" in data:
            table = data["SOURCE_FRAGMENT_TABLE"]
            data["SOURCE_FRAGMENTS"] = [dict(zip(table["columns"], row)) for row in table["rows"]]
        fragments = data["SOURCE_FRAGMENTS"]
        by_text = {f["exact_text"].strip(): f for f in fragments}
        assert len(fragments) == 3 and set(by_text) == {IDENTITY, STORAGE, CONTEXT}
        assert all(f["complete_block"] for f in fragments)
        bound = {row["claim_id"]: row for row in data["ACTUAL_CITATION_BINDINGS"]}
        claims = {row["claim_id"]: row for row in data["CLAIMS"]}
        judgment = checker(messages)
        assert len(judgment["claims"]) == 2
        for row in judgment["claims"]:
            fid = by_text[
                IDENTITY if "The system uses" in claims[row["claim_id"]]["text"] else STORAGE
            ]["fragment_id"]
            bindings = bound[row["claim_id"]]["citations"]
            assert len(bindings) == 1 and bindings[0]["evidence_id"] == "ev_001"
            assert fid in bindings[0]["allowed_fragment_ids"]
            row["citations"] = [
                {"evidence_id": "ev_001", "relation": "supporting", "fragment_ids": [fid]}
            ]
        original["judgment"] = deepcopy(judgment)
        original["claims"] = deepcopy(data["CLAIMS"])
        original["aliases"] = {
            f["fragment_id"]: full_by_text[f["exact_text"].strip()]["fragment_id"]
            for f in fragments
        }
        normalized, binding_issues = normalize_judgment(
            deepcopy(judgment),
            data["ACTUAL_CITATION_BINDINGS"],
        )
        assert not binding_issues
        original["normalized_claims"] = normalized["claims"]
        original["issues"] = evaluate_technical_entity_bindings(
            judgment,
            data["CLAIMS"],
            data["ACTUAL_CITATION_BINDINGS"],
            fragments,
        )
        assert [row["code"] for row in original["issues"]] == [COLLISION, SCOPE]
        assert original["issues"][0]["reason"] == LONG_COLLISION
        assert original["issues"][1]["reason"] == SHORT_SCOPE
        return judgment

    def capture(_messages):
        raise CapturedRepairWire

    adapter = Script([chat_value("answer", BODY, citations=["ev_001"]), selected_support, capture])
    with pytest.raises(CapturedRepairWire):
        GenerationService(adapter).generate(value, RequestBudget(max_calls=4))
    assert len(adapter.calls) == 3
    messages, kwargs = adapter.calls[2]
    assert kwargs["request_context"]["purpose"] == "semantic_repair"
    assert messages[:-1] == adapter.calls[0][0]
    assert (value.evidence, value.source_map) == untouched
    prefix, encoded = messages[-1]["content"].rsplit(MARKER, 1)
    packet = json.loads(encoded)
    assert packet["draft"]["answer_text"] == BODY, repr(packet["draft"]["answer_text"])
    serializers = [
        serializer for serializer in (transport_json, service_json) if encoded == serializer(packet)
    ]
    assert serializers, "Actual repair JSON matches neither known service serializer"
    serialize_packet = serializers[0]
    expected = deepcopy(original["issues"])
    expected[0]["reason"] = SHORT_COLLISION
    assert packet["structural_issues"] == expected
    assert original["issues"][0]["reason"] == LONG_COLLISION
    assert all(row["status"] == "supported" for row in original["judgment"]["claims"])
    assert packet["judgment"]["body_ok"] == original["judgment"]["body_ok"] is True
    assert packet["original_claims"] == original["claims"]
    assert packet["protected_exact_claims"] == []  # Both claims need repair: full-draft fallback.
    expected_claims = deepcopy(original["normalized_claims"])
    for claim in expected_claims:
        claim["fragment_ids"] = [original["aliases"][fid] for fid in claim["fragment_ids"]]
    keys = ("claim_id", "basis", "factual", "status", "reason", "fragment_ids")
    expected_meaning = [{key: row[key] for key in keys} for row in expected_claims]
    actual_meaning = [{key: row[key] for key in keys} for row in packet["judgment"]["claims"]]
    assert actual_meaning == expected_meaning

    old_packet = deepcopy(packet)
    old_packet["structural_issues"][0]["reason"] = LONG_COLLISION
    old_packet["structural_issues"][1]["reason"] = LONG_SCOPE
    old_messages = deepcopy(messages)
    old_messages[-1]["content"] = prefix + MARKER + serialize_packet(old_packet)
    restored = deepcopy(old_packet)
    restored["structural_issues"] = deepcopy(expected)
    assert restored == packet  # No evidence, claims, raw status or other metadata changed.
    saving = len(transport_json(old_messages).encode()) - len(transport_json(messages).encode())
    expected_saving = (
        len(LONG_SCOPE) - len(SHORT_SCOPE) + len(LONG_COLLISION) - len(SHORT_COLLISION)
    )
    assert saving == expected_saving and saving >= 443
    print(
        "SOURCE_SCOPE_REPAIR_PROJECTION="
        + transport_json(
            {
                "scripted_calls": 3,
                "scope_occurrences": 1,
                "collision_occurrences": 1,
                "saved_message_bytes": saving,
                "native25_wire_60443_minus_delta_conditional_only": 60443 - saving,
            }
        )
    )
