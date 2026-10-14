"""Observational audit controls; source verdicts are authored unit fixtures."""

from copy import deepcopy

from generation.reliability_v5 import protected_claims
from generation.source_relation_protection_audit import source_relation_protection_audit
from generation.source_relations_v2 import assess_source_relations, syntactic_units


def fixture():
    claims = [
        {"claim_id": "target", "answer_field": "answer_text",
         "text": "The vessel stores material and creates material without input [ev_001]."},
        {"claim_id": "other", "answer_field": "answer_text",
         "text": "The device transfers stored energy [ev_002]."},
    ]
    units = {row["claim_id"]: row["units"] for row in syntactic_units(claims)}
    typed = {"claims": []}
    bindings, fragments = [], []
    for number, claim in enumerate(claims, 1):
        cid, fid, eid = claim["claim_id"], f"F{number:03d}", f"ev_{number:03d}"
        typed["claims"].append({
            "claim_id": cid, "basis": "textbook", "status": "supported",
            "citations": [{"evidence_id": eid, "fragment_ids": [fid], "relation": "supporting"}],
            "units": [{
                "unit_id": unit["unit_id"], "status": "supported", "fragment_ids": [fid],
                "relation_preserved": True, "conditions_preserved": True, "reason": "Authored fixture.",
            } for unit in units[cid]],
        })
        bindings.append({"claim_id": cid, "citations": [{"evidence_id": eid, "allowed_fragment_ids": [fid]}]})
        fragments.append({
            "fragment_id": fid, "evidence_id": eid, "complete_block": True,
            "exact_text": "The vessel stores material." if number == 1 else claim["text"],
        })
    typed["claims"][0]["units"][-1].update(
        status="unsupported", relation_preserved=False,
        reason="The selected source states storage but does not state material creation.",
    )
    judgment = {
        "claims": [{"claim_id": row["claim_id"], "status": row["status"], "factual": True}
                   for row in typed["claims"]],
        "scope_ok": True, "suggestions_ok": True, "evidence_display_ok": True,
        "cumulative_ok": True, "non_repetitive_next_action": True,
    }
    return typed, claims, bindings, fragments, judgment


def test_validated_negative_unit_audit_explains_exact_selector_delta_without_mutation():
    typed, claims, bindings, fragments, judgment = fixture()
    contract, issues, assessment = assess_source_relations(typed, claims, bindings, fragments)
    assert not contract
    protected = protected_claims(claims, judgment, issues)
    inputs = deepcopy((claims, judgment, issues, protected, assessment))
    audit = source_relation_protection_audit(claims, judgment, issues, protected, assessment)
    assert (claims, judgment, issues, protected, assessment) == inputs
    assert audit["protected_without_negative_unit_ids"] == ["other", "target"]
    assert audit["protected_with_all_diagnostic_ids"] == ["other"]
    assert audit["protection_removed_claim_ids"] == ["target"]
    assert audit["unattributed_protection_losses"] == []
    assert len(audit["negative_unit_reasons"]) == 1
    reason = audit["negative_unit_reasons"][0]
    assert reason["claim_id"] == "target" and reason["unit_id"] == "U02"
    assert reason["checker_claim_status"] == "supported"
    assert reason["checker_unit_status"] == "unsupported"
    assert reason["actual_assessed_source_refs"] == [{"evidence_id": "ev_001", "fragment_id": "F001"}]
    assert not reason["source_entailment_certified"] and not audit["publication_override"]
    assert "quote" not in reason and "claim_quote" not in reason


def test_invalid_source_binding_cannot_receive_a_contract_valid_audit():
    typed, claims, bindings, fragments, judgment = fixture()
    typed["claims"][0]["units"][-1]["fragment_ids"] = ["F999"]
    contract, issues, assessment = assess_source_relations(typed, claims, bindings, fragments)
    assert contract
    assert source_relation_protection_audit(claims, judgment, issues, [], assessment) is None


def test_global_gate_failure_does_not_claim_target_only_protection_loss():
    typed, claims, bindings, fragments, judgment = fixture()
    contract, issues, assessment = assess_source_relations(typed, claims, bindings, fragments)
    assert not contract
    judgment["scope_ok"] = False
    protected = protected_claims(claims, judgment, issues)
    audit = source_relation_protection_audit(claims, judgment, issues, protected, assessment)
    assert protected == [] and audit["protected_without_negative_unit_ids"] == []
    assert audit["protection_removed_claim_ids"] == []
    assert not audit["negative_unit_reasons"][0]["protected_without_negative_units"]


def test_missing_contract_validation_report_is_not_a_validated_audit():
    typed, claims, bindings, fragments, judgment = fixture()
    contract, issues, assessment = assess_source_relations(typed, claims, bindings, fragments)
    assert not contract
    assessment.pop("contract_issue_codes")
    assert source_relation_protection_audit(claims, judgment, issues, [], assessment) is None


def test_assessor_status_provenance_survives_changed_current_judgment_status():
    typed, claims, bindings, fragments, judgment = fixture()
    contract, issues, assessment = assess_source_relations(typed, claims, bindings, fragments)
    assert not contract
    judgment["claims"][0]["status"] = "partial"
    protected = protected_claims(claims, judgment, issues)
    audit = source_relation_protection_audit(claims, judgment, issues, protected, assessment)
    reason = audit["negative_unit_reasons"][0]
    assert reason["checker_claim_status"] == "supported"
    assert reason["current_judgment_claim_status"] == "partial"
    assert audit["protection_removed_claim_ids"] == []


def test_counterfactual_preserves_unmatched_same_code_diagnostic():
    typed, claims, bindings, fragments, judgment = fixture()
    contract, issues, assessment = assess_source_relations(typed, claims, bindings, fragments)
    assert not contract
    issues.append({"code": "SOURCE_RELATION_CHANGED", "claim_id": "other", "unit_id": "U999"})
    protected = protected_claims(claims, judgment, issues)
    audit = source_relation_protection_audit(claims, judgment, issues, protected, assessment)
    assert audit["protected_without_negative_unit_ids"] == ["target"]
    assert audit["protected_with_all_diagnostic_ids"] == []
    assert audit["protection_removed_claim_ids"] == ["target"]
    assert {row["claim_id"] for row in audit["negative_unit_reasons"]} == {"target"}
