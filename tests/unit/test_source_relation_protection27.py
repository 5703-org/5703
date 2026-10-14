"""Authored relation fixtures exercise transport/protection, not semantic accuracy.

Run from the project's unit-test environment. No workspace fixtures, database,
network, or provider configuration are required.
"""

from copy import deepcopy
from dataclasses import replace
import json

import pytest

from generation import GenerationService, ModelConfig, RequestBudget
from generation.local_repair import VERSION as CLAIM_PATCH_POLICY
from generation.reliability_v4 import normalize_judgment
from generation.reliability_v5 import protected_claims
from generation.source_relations_v2 import VERSION, assess_source_relations
from retrieval.source_spans import text_hash
from test_answer_core_v5 import req
from test_enhancement_generation import Script, answer
from test_source_relation_units_v2 import check_input, unit_checker


DEVICE_SOURCE = "The device transfers stored energy."
VESSEL_SOURCE = "The vessel stores material."
INLET_SOURCE = "The material enters the vessel through an inlet."
SOURCE = " ".join((DEVICE_SOURCE, VESSEL_SOURCE, INLET_SOURCE))
GOOD = "The device transfers stored energy [ev_001]."
TARGET = "The vessel stores material and creates material without input [ev_001]."
BODY = TARGET + " " + GOOD
REPLACEMENT = "The vessel stores material [ev_001]."
SHORT = GOOD
MARKER = "REPAIR_DATA_JSON:\n"
PROTECTION_GATES = ("scope_ok", "suggestions_ok", "evidence_display_ok", "cumulative_ok")


class CapturedRelationRepair(BaseException):
    """Stop at the third scripted call before any repair result is returned."""


def request_fixture():
    value = req(
        question="Explain the device's energy transfer and the vessel's material storage.",
        answer_mode="textbook",
        teaching_context={"teaching_mode": "direct", "help_level": 0},
        joint_checker_policy="typed_joint_v5",
        source_relation_policy=VERSION,
        repair_policy=CLAIM_PATCH_POLICY,
        config=ModelConfig(window_tokens=32768, tokenizer_provider="estimate"),
    )
    evidence, mapping = deepcopy(value.evidence), deepcopy(value.source_map)
    evidence[0].update(text=SOURCE, text_hash=text_hash(SOURCE), section="Authored device")
    mapping["c1"].update(chunk_text=SOURCE, chunk_hash=text_hash(SOURCE))
    mapping["c1"]["units"][0].update(cleaned_text=SOURCE, text_hash=text_hash(SOURCE))
    mapping["c1"]["spans"][0].update(end=len(SOURCE), chunk_end=len(SOURCE))
    return replace(value, evidence=evidence, source_map=mapping)


def relation_checker(state, *, adverse=False, invalid=None, target_text=TARGET):
    """Bind every unit to the claim's actually selected complete source fragment."""
    def callback(messages):
        data = check_input(messages)
        fragments = data["SOURCE_FRAGMENTS"]
        by_text = {row["exact_text"].strip(): row for row in fragments}
        assert len(fragments) == 3
        assert set(by_text) == {DEVICE_SOURCE, VESSEL_SOURCE, INLET_SOURCE}
        assert all(row["complete_block"] for row in fragments)
        claims = {row["claim_id"]: row for row in data["CLAIMS"]}
        bindings = {row["claim_id"]: row for row in data["ACTUAL_CITATION_BINDINGS"]}
        target_ids = [cid for cid, row in claims.items() if row["text"] == target_text]
        assert len(claims) == 3 and len(target_ids) == 1
        target_id = target_ids[0]
        judgment = unit_checker(messages)
        assert judgment["body_ok"] is True
        assert all(judgment[gate] is True for gate in PROTECTION_GATES)
        assert all(row["basis"] == "textbook" and row["status"] == "supported"
                   for row in judgment["claims"])
        for row in judgment["claims"]:
            cid = row["claim_id"]
            fragment = by_text[VESSEL_SOURCE if cid == target_id else DEVICE_SOURCE]
            citation = bindings[cid]["citations"]
            assert len(citation) == 1 and citation[0]["evidence_id"] == "ev_001"
            assert fragment["fragment_id"] in citation[0]["allowed_fragment_ids"]
            row["citations"] = [{
                "evidence_id": "ev_001", "relation": "supporting",
                "fragment_ids": [fragment["fragment_id"]],
            }]
            for unit in row["units"]:
                unit["fragment_ids"] = [fragment["fragment_id"]]
        normalized, binding_issues = normalize_judgment(
            deepcopy(judgment), data["ACTUAL_CITATION_BINDINGS"],
        )
        assert not binding_issues
        assert all(row["factual"] for row in normalized["claims"])
        baseline_protected = protected_claims(data["CLAIMS"], normalized, [])
        assert baseline_protected == data["CLAIMS"]
        target = next(row for row in judgment["claims"] if row["claim_id"] == target_id)
        if adverse:
            assert len(target["units"]) >= 2
            target["units"][-1].update(status="unsupported", relation_preserved=False)
        if invalid == "missing_unit":
            target["units"].pop()
        elif invalid == "foreign_unit":
            target["units"][-1]["unit_id"] = "U999"
        elif invalid == "foreign_fragment":
            fid = "not-an-actual-source-fragment"
            assert fid not in {row["fragment_id"] for row in fragments}
            target["units"][-1]["fragment_ids"] = [fid]
        elif invalid == "unselected_fragment":
            fid = by_text[INLET_SOURCE]["fragment_id"]
            assert fid in bindings[target_id]["citations"][0]["allowed_fragment_ids"]
            assert fid not in target["citations"][0]["fragment_ids"]
            target["units"][-1]["fragment_ids"] = [fid]
        else:
            assert invalid is None
        contract, defects, assessment = assess_source_relations(
            judgment, data["CLAIMS"], data["ACTUAL_CITATION_BINDINGS"], fragments,
        )
        if invalid:
            assert contract and not assessment["accepted"]
        elif adverse:
            assert not contract and not assessment["accepted"]
            assert defects and {row["claim_id"] for row in defects} == {target_id}
            assert sum(unit["status"] != "supported"
                       for row in judgment["claims"] for unit in row["units"]) == 1
        else:
            assert not contract and not defects and assessment["accepted"]
        state.update(
            claims=deepcopy(data["CLAIMS"]), judgment=deepcopy(judgment),
            target_id=target_id, defects=deepcopy(defects),
            baseline_protected=deepcopy(baseline_protected),
        )
        return judgment
    return callback


def test_valid_supported_relation_units_keep_the_two_call_path():
    state = {}
    adapter = Script([answer(BODY, short_answer=SHORT), relation_checker(state)])
    out = GenerationService(adapter).generate(request_fixture(), RequestBudget(max_calls=2))
    assert out.succeeded, out.error
    assert len(adapter.calls) == 2 and out.budget["consumed_calls"] == 2
    assert out.response["answer_text"] == BODY and out.response["short_answer"] == SHORT
    assert out.checks[-1]["source_relation_assessment"]["accepted"]


@pytest.mark.parametrize(
    "invalid", ["missing_unit", "foreign_unit", "foreign_fragment", "unselected_fragment"],
)
def test_invalid_relation_units_contract_fail_before_any_semantic_unlock(invalid):
    state = {}
    adapter = Script([
        answer(BODY, short_answer=SHORT),
        relation_checker(state, adverse=True, invalid=invalid),
    ])
    out = GenerationService(adapter).generate(request_fixture(), RequestBudget(max_calls=2))
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert len(adapter.calls) == 2 and out.budget["consumed_calls"] == 2
    assert all(kwargs["request_context"]["purpose"] != "semantic_repair"
               for _messages, kwargs in adapter.calls)


def test_valid_adverse_unit_unlocks_only_original_target_at_third_repair_wire():
    state = {}
    value = request_fixture()
    untouched = deepcopy((value.evidence, value.source_map))

    def capture(_messages):
        raise CapturedRelationRepair

    adapter = Script([
        answer(BODY, short_answer=SHORT), relation_checker(state, adverse=True), capture,
    ])
    with pytest.raises(CapturedRelationRepair):
        GenerationService(adapter).generate(value, RequestBudget(max_calls=4))
    assert len(adapter.calls) == 3
    assert (value.evidence, value.source_map) == untouched
    messages, kwargs = adapter.calls[2]
    assert kwargs["request_context"]["purpose"] == "semantic_repair"
    assert kwargs["response_schema_name"] == "claim_patch_repair_v1"
    packet = json.loads(messages[-1]["content"].rsplit(MARKER, 1)[1])
    assert "source_relation_protection_invalidation" not in json.dumps(packet)
    target_id = state["target_id"]
    protected = [row for row in state["baseline_protected"] if row["claim_id"] != target_id]
    assert {row["answer_field"] for row in protected} == {"answer_text", "short_answer"}
    assert packet["original_claims"] == state["claims"]
    assert packet["protected_exact_claims"] == protected
    assert packet["editable_claim_ids"] == [target_id]
    assert packet["draft"]["answer_text"] == BODY and packet["draft"]["short_answer"] == SHORT
    assert packet["judgment"]["body_ok"] == state["judgment"]["body_ok"] is True
    raw_by_id = {row["claim_id"]: row for row in state["judgment"]["claims"]}
    actual_by_id = {row["claim_id"]: row for row in packet["judgment"]["claims"]}
    assert set(actual_by_id) == set(raw_by_id)
    assert all(actual_by_id[cid]["status"] == raw_by_id[cid]["status"] == "supported"
               for cid in raw_by_id)
    assert packet["structural_issues"]
    assert {row["claim_id"] for row in packet["structural_issues"]} == {target_id}
    assert {row["code"] for row in packet["structural_issues"]} == {
        row["code"] for row in state["defects"]
    }
    assert all(row["text"] == (GOOD if row["answer_field"] == "answer_text" else SHORT)
               for row in packet["protected_exact_claims"])



def test_completed_patch_preserves_neighboring_ids_text_and_summary_through_full_check():
    initial, final = {}, {}
    value = request_fixture()
    untouched = deepcopy((value.evidence, value.source_map))

    def patch(messages):
        packet = json.loads(messages[-1]["content"].rsplit(MARKER, 1)[1])
        assert "source_relation_protection_invalidation" not in json.dumps(packet)
        target_id = initial["target_id"]
        expected_protected = [
            row for row in initial["baseline_protected"] if row["claim_id"] != target_id
        ]
        assert packet["original_claims"] == initial["claims"]
        assert packet["protected_exact_claims"] == expected_protected
        assert packet["editable_claim_ids"] == [target_id]
        return {
            "edits": [{"claim_id": target_id, "replacement_text": REPLACEMENT}],
            "append_answer_text": "",
        }

    adapter = Script([
        answer(BODY, short_answer=SHORT),
        relation_checker(initial, adverse=True),
        patch,
        relation_checker(final, target_text=REPLACEMENT),
    ])
    out = GenerationService(adapter).generate(value, RequestBudget(max_calls=4))
    assert out.succeeded, out.error
    assert len(adapter.calls) == 4 and out.budget["consumed_calls"] == 4
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert adapter.calls[3][1]["response_schema_name"] == "joint_check_source_relations_v2"
    assert len(out.checks) == 2
    assert out.checks[-1]["source_relation_assessment"]["accepted"]
    assert out.response["answer_text"] == REPLACEMENT + " " + GOOD
    assert out.response["short_answer"] == SHORT
    assert (value.evidence, value.source_map) == untouched
    initial_by_id = {row["claim_id"]: row for row in initial["claims"]}
    final_by_id = {row["claim_id"]: row for row in final["claims"]}
    unaffected = {
        row["claim_id"] for row in initial["baseline_protected"]
        if row["claim_id"] != initial["target_id"]
    }
    audit = out.checks[0]["source_relation_protection_invalidation"]
    assert audit["protected_without_negative_unit_ids"] == sorted(initial_by_id)
    assert audit["protected_with_all_diagnostic_ids"] == sorted(unaffected)
    assert audit["protection_removed_claim_ids"] == [initial["target_id"]]
    assert audit["unattributed_protection_losses"] == []
    assert audit["source_binding_contract_valid"] is True
    assert audit["independent_semantic_evaluation"] is False
    assert audit["publication_override"] is False
    assert len(audit["negative_unit_reasons"]) == 1
    negative = audit["negative_unit_reasons"][0]
    raw_target = next(
        row for row in initial["judgment"]["claims"]
        if row["claim_id"] == initial["target_id"]
    )
    raw_unit = raw_target["units"][-1]
    assert negative["claim_id"] == initial["target_id"]
    assert negative["unit_id"] == raw_unit["unit_id"] == "U02"
    assert negative["checker_claim_status"] == raw_target["status"] == "supported"
    assert negative["current_judgment_claim_status"] == "supported"
    assert negative["checker_unit_status"] == raw_unit["status"] == "unsupported"
    assert negative["reason"] == raw_unit["reason"]
    assert negative["issue_codes"] == sorted({row["code"] for row in initial["defects"]})
    normalized_target = next(
        row for row in out.checks[0]["judgment"]["claims"]
        if row["claim_id"] == initial["target_id"]
    )
    assert len(normalized_target["fragment_ids"]) == 1
    assert negative["actual_assessed_source_refs"] == [
        {"evidence_id": "ev_001", "fragment_id": normalized_target["fragment_ids"][0]}
    ]
    assert negative["protected_without_negative_units"] is True
    assert negative["protected_with_all_diagnostics"] is False
    assert negative["source_entailment_certified"] is False
    assert negative["publication_override"] is False
    # Accepted publication exits before the repair-boundary protection selector.
    assert "source_relation_protection_invalidation" not in out.checks[-1]
    assert len(unaffected) == 2 and unaffected <= final_by_id.keys()
    for cid in unaffected:
        before, after = initial_by_id[cid], final_by_id[cid]
        assert after["answer_field"] == before["answer_field"]
        assert after["text"] == before["text"]
        if before["answer_field"] == "answer_text":
            assert after["start"] != before["start"]
        else:
            assert after["start"] == before["start"]
    assert initial["target_id"] != final["target_id"]
    assert initial["target_id"] not in final_by_id



