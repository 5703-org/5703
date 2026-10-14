"""Source-binding conflicts cannot be exempted by model reason wording."""
from copy import deepcopy

import pytest

from generation.reliability_v5 import evaluate_technical_entity_bindings


def inputs(reason="The selected source states XTR.", source=None, extras=(), selected=()):
    claim = {"claim_id": "claim_identifier", "answer_field": "answer_text",
             "text": "The system uses XTRP to transfer energy [ev_001]."}
    fragments = [{"fragment_id": "F1", "evidence_id": "ev_001",
                  "exact_text": source or "The system uses XTR to transfer energy."}]
    fragments.extend({"fragment_id": f"F{i + 2}", "evidence_id": "ev_001",
                      "exact_text": text} for i, text in enumerate(extras))
    binding = {"claim_id": claim["claim_id"], "citations": [{"evidence_id": "ev_001",
               "allowed_fragment_ids": [fragment["fragment_id"] for fragment in fragments]}]}
    judgment = {"claims": [{"claim_id": claim["claim_id"], "basis": "textbook",
                 "status": "supported", "reason": reason, "citations": [{
                     "evidence_id": "ev_001", "relation": "supporting",
                     "fragment_ids": ["F1", *selected]}]}]}
    return judgment, [claim], [binding], fragments


@pytest.mark.parametrize("reason", [
    "The selected source states XTR.", "The selected source states XTRP.",
    "XTR and XTRP are equivalent.", "This passage supports the claim.",
])
def test_same_source_collision_is_independent_of_reason(reason):
    values = inputs(reason)
    before = deepcopy(values)
    issues = evaluate_technical_entity_bindings(*values)
    assert values == before
    assert len(issues) == 1
    assert issues[0]["claimed_identifier"] == "XTRP"
    assert issues[0]["source_identifiers"] == ["XTR"]
    assert issues[0]["selected_fragment_ids"] == ["F1"]
    assert not issues[0]["source_entailment_certified"]
    assert not issues[0]["publication_override"]


@pytest.mark.parametrize("source", [
    "The system does not use XTR to transfer energy.",
    "The system compares XTR with XTRP to transfer energy.",
    "The system uses extended transport receptor phosphate to transfer energy, unlike XTR.",
    "The system uses ABC to transfer energy.",
])
def test_other_roles_negation_full_names_and_distant_ids_do_not_collide(source):
    assert evaluate_technical_entity_bindings(*inputs(source=source)) == []


@pytest.mark.parametrize("selected, expected", [([], 1), (["F2"], 0)])
def test_only_actual_selected_alias_can_clear_collision(selected, expected):
    values = inputs(extras=["XTR is also called XTRP."], selected=selected)
    assert len(evaluate_technical_entity_bindings(*values)) == expected


def test_fragments_cannot_be_stitched_into_a_copied_proposition():
    values = inputs(source="The system uses XTR", extras=["to transfer energy."], selected=["F2"])
    assert evaluate_technical_entity_bindings(*values) == []


@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_negative_model_status_is_not_rewritten(status):
    values = inputs()
    values[0]["claims"][0]["status"] = status
    before = deepcopy(values)
    assert evaluate_technical_entity_bindings(*values) == []
    assert values == before


def test_unallowed_source_cannot_trigger_collision():
    values = inputs()
    values[2][0]["citations"][0]["allowed_fragment_ids"] = []
    assert evaluate_technical_entity_bindings(*values) == []
