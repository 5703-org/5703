"""Bounded source revision controls; captured failures are never regraded."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from generation import GenerationService, RequestBudget
from generation import assertion_provenance_v1 as assertions
from generation import assertion_reselection_v1 as reselection
from generation.reliability_v4 import normalize_judgment
from generation.reliability_v5 import assess_requirements, response_claims

from fixtures_generic163 import (
    ScriptedTransport,
    authored_parent,
    checker_labels,
    diagnosis_for,
    freeze,
    packet_from_messages,
    prepare_fixture,
    proposal_for,
)

CAPTURE_PATH = Path(__file__).parent / "fixtures" / "captured162-cases.json"
CAPTURE_SHA256 = "78125990b1e066d11ac7657ad4743d912973adba6ea64d2b04364df37a38dbb1"
CAPTURE = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "case_id,statuses",
    [
        ("D160-Q01", ["supported", "supported", "partial"]),
        ("D160-Q02", ["supported", "partial", "partial"]),
    ],
)
def test_captured162_exact_six_claims_and_raw_negatives_remain(case_id, statuses):
    assert hashlib.sha256(CAPTURE_PATH.read_bytes()).hexdigest() == CAPTURE_SHA256
    case = next(c for c in CAPTURE["cases"] if c["case_id"] == case_id)
    raw = json.loads(case["actual162_checker_raw"])
    assert raw == case["actual162_raw_judgment"]
    assert [c["status"] for c in raw["claims"]] == statuses
    assert raw["body_ok"] is False
    assert len(raw["claims"]) == len(case["claims"]) == 3
    assert {c["claim_id"] for c in raw["claims"]} == {c["claim_id"] for c in case["claims"]}
    typed = assertions.AssertionCheck.model_validate(raw).model_dump()
    assert assertions.assess_judgment(typed, case["provenance"]) == []
    normalized, _ = normalize_judgment(typed, case["bindings"])
    assert normalized["body_ok"] is False
    bank = assertions.source_bank(case["original_fragments"], case["submitted_evidence"])
    aliased = [{**row, "fragment_id": row["source_id"]} for row in bank]
    contract, defects, _ = assess_requirements(
        typed, case["coverage"], aliased, answer_mode="textbook", teaching_mode="direct"
    )
    if case_id == "D160-Q02":
        assert {
            "code": "REQUIREMENT_SUFFICIENCY_CONTRADICTION",
            "requirement_id": "requirement_03",
        } in contract
        assert {
            "code": "SUFFICIENT_CONTEXT_UNDERUSED",
            "requirement_id": "requirement_03",
        } in defects
        assert raw["claims"][2]["proof_audit"]["actor_identity_preserved"] is True
        assert raw["claims"][2]["status"] == "partial"
        assert not raw["claims"][2]["proof_audit"]["causal_bridges_entailed"]
    else:
        assert contract == defects == []
        original = json.loads(case["original161_generation_raw"])
        assert original["answer_text"][0]["source_ids"] == ["F001"]
        assert original["answer_text"][2]["source_ids"] == ["F001"]
        assert case["provenance"]["assertions"][0]["sources"][0]["source_id"] == "F007"
    assert CAPTURE["actual162_final_closed_batch"]["remaining_model_slots"] == 0
    assert case["native_public_answer_accepted"] is False


def test_one_explicit_proposal_freezes_whole_body_and_protected_good_bindings():
    request, parent, fragments, continuation, plan = prepare_fixture()
    before = deepcopy((request, parent, fragments, continuation, plan))
    packet = reselection.selector_packet(plan)
    assert packet["literal_question"] == request.question
    assert packet["frozen_public_response"] == parent["drafts"][0]["response"]
    assert len(packet["targets"]) == 1
    assert [r["evidence_id"] for r in packet["targets"][0]["eligible_sources_by_evidence"]] == [
        "ev_001"
    ]
    response, provenance, audit = reselection.bind_proposal(
        plan, proposal_for(plan), fragments, parent["evidence"]
    )
    assert response == parent["drafts"][0]["response"]
    assert response_claims(response) == response_claims(parent["drafts"][0]["response"])
    assert (
        provenance["assertions"][1] == parent["drafts"][0]["assertion_provenance"]["assertions"][1]
    )
    assert (
        provenance["assertions"][0]["assertion_text"]
        == parent["drafts"][0]["assertion_provenance"]["assertions"][0]["assertion_text"]
    )
    assert [s["source_id"] for s in provenance["assertions"][0]["sources"]] == ["F001", "F002"]
    assert audit["candidate_count"] == 1 and audit["requires_complete_fresh_check"] is True
    assert audit["semantic_support_certified"] is False and audit["state"] == "proposal_bound"
    assert (request, parent, fragments, continuation, plan) == before


@pytest.mark.parametrize(
    "defect",
    [
        "unknown_target",
        "duplicate_target",
        "unchanged_union",
        "unknown_source",
        "wrong_evidence_owner",
        "duplicate_source",
        "new_evidence_id",
        "foreign_good_assertion",
        "missing_target",
        "changed_prose",
        "changed_plan_digest",
        "changed_prior_binding",
    ],
)
def test_proposal_cannot_expand_or_mutate_its_frozen_scope(defect):
    _, parent, fragments, _, plan = prepare_fixture()
    proposal = proposal_for(plan)
    row = proposal["replacements"][0]
    if defect == "unknown_target":
        row["claim_id"] = "foreign-claim"
    elif defect == "duplicate_target":
        proposal["replacements"].append(deepcopy(row))
    elif defect in ("accepted_target", "foreign_good_assertion"):
        row["claim_id"] = plan["provenance"]["assertions"][1]["claim_id"]
    elif defect == "unchanged_union":
        row["selections"][0]["source_ids"] = ["F001"]
    elif defect == "unknown_source":
        row["selections"][0]["source_ids"] = ["F999"]
    elif defect == "wrong_evidence_owner":
        row["selections"][0]["source_ids"] = ["F002", "F004"]
    elif defect == "duplicate_source":
        row["selections"][0]["source_ids"] = ["F002", "F002"]
    elif defect == "new_evidence_id":
        row["selections"].append({"evidence_id": "ev_002", "source_ids": ["F004"]})
    elif defect == "missing_target":
        proposal["replacements"] = []
    elif defect == "changed_prose":
        row["text"] = "An unapproved rewrite."
    elif defect == "changed_plan_digest":
        proposal["plan_sha256"] = "0" * 64
    elif defect == "changed_prior_binding":
        row["prior_binding_sha256"] = "0" * 64
    with pytest.raises((ValueError, ValidationError)):
        reselection.bind_proposal(plan, proposal, fragments, parent["evidence"])


@pytest.mark.parametrize(
    "defect", ["quote", "hash", "parent", "locator", "incomplete", "bank_order", "evidence_text"]
)
def test_fresh_source_binding_rejects_exact_quote_hash_locator_or_bank_drift(defect):
    _, parent, fragments, _, plan = prepare_fixture()
    changed, evidence = deepcopy(fragments), deepcopy(parent["evidence"])
    if defect == "quote":
        changed[1]["exact_text"] += " Altered."
    elif defect == "hash":
        changed[1]["text_hash"] = "0" * 64
    elif defect == "parent":
        changed[1]["evidence_id"] = "ev_002"
    elif defect == "locator":
        changed[1]["source_unit_id"] = "foreign-unit-with-identical-quote"
    elif defect == "incomplete":
        changed[1]["complete_block"] = False
    elif defect == "bank_order":
        changed.reverse()
    elif defect == "evidence_text":
        evidence[0]["text"] += " Altered."
    with pytest.raises(ValueError):
        reselection.bind_proposal(plan, proposal_for(plan), changed, evidence)


@pytest.mark.parametrize(
    "defect",
    [
        "already_published",
        "other_failure",
        "second_draft",
        "candidate_used",
        "unknown_usage",
        "unsubmitted_parent",
        "extra_check_ID",
        "global_requirement_failure",
        "other_gate_failure",
        "accepted_target",
        "foreign_candidate",
        "already_selected_candidate",
        "duplicate_candidate",
        "no_remaining_calls",
        "elapsed_budget",
    ],
)
def test_saved_failure_admission_is_finite_and_only_selection_specific(defect):
    request, parent, fragments = authored_parent()
    candidate_ids = ["F002"]
    if defect == "already_published":
        parent["response"] = deepcopy(parent["drafts"][0]["response"])
    elif defect == "other_failure":
        parent["error"]["code"] = "CHECKER_INCONSISTENT"
    elif defect == "second_draft":
        parent["drafts"].append(deepcopy(parent["drafts"][0]))
    elif defect == "candidate_used":
        parent["token_budget"]["assertion_reselection"] = {"candidate_count": 1}
    elif defect == "unknown_usage":
        parent["attempts"][0]["usage"]["total_tokens"] = None
    elif defect == "unsubmitted_parent":
        parent["attempts"][0]["request_submitted"] = False
    elif defect == "extra_check_ID":
        parent["checks"][0]["typed_judgment_raw_aliases"]["claims"].append(
            deepcopy(parent["checks"][0]["typed_judgment_raw_aliases"]["claims"][0])
        )
    elif defect == "global_requirement_failure":
        parent["checks"][0]["publication_block"]["requirement_issue_codes"] = [
            "REQUIREMENT_SUFFICIENCY_CONTRADICTION"
        ]
    elif defect == "other_gate_failure":
        parent["checks"][0]["publication_block"]["failed_checker_gate_names"].append("scope_ok")
    elif defect == "accepted_target":
        parent["checks"][0]["typed_judgment_raw_aliases"] = checker_labels(
            parent["drafts"][0]["assertion_provenance"], negative_target=False
        )
    elif defect == "foreign_candidate":
        candidate_ids = ["F004"]
    elif defect == "already_selected_candidate":
        candidate_ids = ["F001"]
    elif defect == "duplicate_candidate":
        candidate_ids = ["F002", "F002"]
    elif defect == "no_remaining_calls":
        parent["budget"]["max_calls"] = 3
    elif defect == "elapsed_budget":
        parent["budget"]["active_seconds"] = parent["budget"]["max_active_seconds"]
    diagnosis = diagnosis_for(request, parent, fragments, candidate_ids=candidate_ids)
    continuation = freeze(request, parent, fragments, diagnosis=diagnosis)
    with pytest.raises((ValueError, ValidationError)):
        reselection.prepare(
            request,
            continuation,
            fragments,
            parent["evidence"],
            RequestBudget.from_dict(parent["budget"]),
        )


def test_full_or_reordered_identical_union_is_not_a_new_candidate():
    request, parent, fragments = authored_parent(source_ids=["F001", "F002", "F003"])
    diagnosis = diagnosis_for(request, parent, fragments, candidate_ids=["F002"])
    continuation = freeze(request, parent, fragments, diagnosis=diagnosis)
    with pytest.raises(ValueError, match="NO_ELIGIBLE_NEW_SOURCE"):
        reselection.prepare(
            request,
            continuation,
            fragments,
            parent["evidence"],
            RequestBudget.from_dict(parent["budget"]),
        )
    _, parent, fragments, _, plan = prepare_fixture(source_ids=["F001", "F003"])
    # Reordering two original blocks contributes no newly diagnosed premise.
    with pytest.raises(ValueError, match="NO_DIRECTED_CHANGE"):
        reselection.bind_proposal(
            plan, proposal_for(plan, ids=["F003", "F001"]), fragments, parent["evidence"]
        )


def test_opaque_saved_ID_or_candidate_count_tamper_stops_before_any_call():
    request, parent, fragments = authored_parent()
    continuation = freeze(request, parent, fragments)
    for defect in ("history", "profile", "unknown_teaching_key"):
        _assert_nonempty_personal_context_rejected(defect)
    for key, value in [("parent_draft_id", "different-owned-draft"), ("candidate_count", 1)]:
        changed = deepcopy(continuation)
        changed[key] = value
        with pytest.raises((ValueError, ValidationError)):
            reselection.prepare(
                request,
                changed,
                fragments,
                parent["evidence"],
                RequestBudget.from_dict(parent["budget"]),
            )


def fresh_check(messages, *, defect=None):
    packet = packet_from_messages(messages)
    proofs = packet["ASSERTION_PROOFS"]["assertions"]
    provenance = {
        "assertions": [
            {
                "assertion_id": row["assertion_id"],
                "claim_id": row["claim_id"],
                "sources": [
                    {**s, "source_id": s["fragment_id"]} for s in row["selected_source_union"]
                ],
            }
            for row in proofs
        ]
    }
    value = checker_labels(provenance, negative_target=False)
    first = proofs[0]["selected_source_union"][0]
    value["requirements"] = [
        {
            "requirement_id": row["id"],
            "relevance": "related",
            "sufficiency": "sufficient",
            "evidence": [
                {
                    "evidence_id": first["evidence_id"],
                    "fragment_id": first["fragment_id"],
                    "quote": first["exact_text"],
                }
            ],
            "conditions_preserved": True,
            "response_coverage": "covered",
            "missing_information": "",
            "reason": "Authored engineering wire label, not semantic measurement.",
        }
        for row in packet["CONTEXT_COVERAGE"]["requirements"]
    ]
    if defect in ("actor_identity_preserved", "conditions_preserved", "causal_bridges_entailed"):
        value["claims"][0]["status"] = "partial"
        value["claims"][0]["proof_audit"].update(
            all_predicates_entailed=False,
            missing_predicates=[f"Authored missing predicate: {defect}"],
        )
        value["claims"][0]["proof_audit"][defect] = False
        value["body_ok"] = False
    elif defect == "duplicate_ID":
        value["claims"].append(deepcopy(value["claims"][0]))
    elif defect == "phantom_ID":
        value["claims"].append({**deepcopy(value["claims"][0]), "claim_id": "practice_present"})
    return value


def selector_response(messages):
    packet = json.loads(messages[-1]["content"])
    return {
        "plan_sha256": packet["plan_sha256"],
        "replacements": [
            {
                "claim_id": row["claim_id"],
                "prior_binding_sha256": row["prior_binding_sha256"],
                "selections": [
                    {"evidence_id": row["evidence_ids"][0], "source_ids": ["F001", "F002"]}
                ],
            }
            for row in packet["targets"]
        ],
    }


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "actor_identity_preserved",
        "conditions_preserved",
        "causal_bridges_entailed",
        "duplicate_ID",
        "phantom_ID",
    ],
)
def test_actual_service_continuation_skips_GEN_and_has_one_selector_one_whole_CHECK(defect):
    request, parent, fragments = authored_parent()
    # These adversarial unions exercise gates, never a deterministic entailment oracle.
    selected_ids = ["F001", "F002"]
    candidate_ids = ["F002"]
    if defect == "conditions_preserved":
        selected_ids = ["F002"]  # No selected valve/open-condition antecedent.
    elif defect == "actor_identity_preserved":
        selected_ids = ["F002", "F003"]  # The intervening selected antecedent names U.
    elif defect == "causal_bridges_entailed":
        selected_ids, candidate_ids = ["F001", "F003"], ["F003"]
    diagnosis = diagnosis_for(request, parent, fragments, candidate_ids=candidate_ids)
    request.assertion_reselection = freeze(request, parent, fragments, diagnosis=diagnosis)
    protected_parent = deepcopy(parent)

    def chosen_selector(messages):
        proposal = selector_response(messages)
        proposal["replacements"][0]["selections"][0]["source_ids"] = selected_ids
        return proposal

    transport = ScriptedTransport(
        [chosen_selector, lambda messages: fresh_check(messages, defect=defect)]
    )
    events = []
    out = GenerationService(transport).generate(
        request, RequestBudget.from_dict(parent["budget"]), events.append
    )
    assert len(transport.calls) == 2
    assert [a["stage"] for a in out.attempts] == ["assertion_source_reselection", "joint_recheck"]
    assert out.budget["consumed_calls"] == 4
    assert out.budget["format_repairs"] == out.budget["transient_retries"] == 0
    assert parent == protected_parent
    assert len(events) == 4
    if defect is None:
        assert out.succeeded, out.error
        assert out.response == parent["drafts"][0]["response"]
        assert out.drafts[0]["revision"] == 1
        audit = out.drafts[0]["assertion_reselection"]
        assert audit["parent_outcome"] == parent
        assert audit["public_response_changed"] is False
        assert audit["requires_complete_fresh_check"] is True
    else:
        assert out.response is None and not out.succeeded
        assert out.error is not None


def _assert_nonempty_personal_context_rejected(defect):
    request, parent, fragments = authored_parent()
    if defect == "history":
        request.history = [{"role": "user", "content": "A previous problem."}]
    elif defect == "profile":
        request.profile = {"use_profile": True, "profile": {"level": "advanced"}}
    else:
        request.teaching_context["hidden_prior_solution"] = "An unknown context field."
    with pytest.raises(ValueError):
        freeze(request, parent, fragments)


def test_legacy_default_None_keeps_actual_GEN_CHECK_and_original_private_schemas():
    from fixtures_generic163 import private_draft

    request, _, _ = authored_parent()
    assert request.assertion_reselection is request.requirement_scope_policy is None
    transport = ScriptedTransport([private_draft(source_ids=["F001", "F002"]), fresh_check])
    out = GenerationService(transport).generate(request, RequestBudget(max_calls=2))
    assert out.succeeded, out.error
    assert [row["stage"] for row in out.attempts] == ["generation", "joint_check"]
    assert len(transport.calls) == out.budget["consumed_calls"] == 2
    assert transport.calls[0][1]["response_schema_name"] == assertions.DRAFT_SCHEMA
    assert transport.calls[1][1]["response_schema_name"] == assertions.CHECK_SCHEMA
    assert "REQUIREMENT_SCOPE" not in packet_from_messages(transport.calls[1][0])
