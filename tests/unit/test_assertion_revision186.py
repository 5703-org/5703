"""Offline local-revision controls; authored labels never regrade frozen CHECKs."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from generation import assertion_provenance_v1 as assertions
from generation import assertion_revision_v1 as revision
from generation.parser import parse_response
from generation.providers import payload
from generation.reliability_v4 import compact_schema, normalize_judgment
from generation.reliability_v5 import assess_requirements, response_claims
from retrieval.source_spans import map_fragments

from fixtures_generic163 import checker_labels, fixture_request, private_draft

ROOT = Path(__file__).parents[2]
CAPTURE_PATH = Path(__file__).parent / "fixtures/captured162-cases.json"
CAPTURE_SHA = "78125990b1e066d11ac7657ad4743d912973adba6ea64d2b04364df37a38dbb1"
PROOF_PATH = ROOT / "docs/execution/evidence/phase186/proof/FROZEN-OWN-SOURCE-PROOF186.json"
PROOF_SHA = "e540fb22ead89e708afc1704a3258589bdfdbfd0f36911a0655e3c54aae1e296"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def proposal_for(draft, provenance, fragments, *, index=0, text=None):
    row = provenance["assertions"][index]
    return {
        **revision.parent_bindings(draft, provenance, fragments),
        "edits": [
            {
                "claim_id": row["claim_id"],
                "prior_binding_sha256": assertions._canonical_hash(row),
                "replacement_text": text
                or (
                    "When valve A is open, pressure from chamber P moves piston T "
                    "and lifts its attached load against gravity."
                ),
            }
        ],
    }


def generic(*, source_ids=None):
    request = fixture_request()
    fragments, issues = map_fragments(request.evidence, request.source_map)
    assert not issues
    draft = private_draft(source_ids=source_ids or ["F001", "F002"])
    _, provenance = assertions.compile_draft(draft, fragments)
    return request, draft, provenance, fragments


def consume(typed, public, provenance, fragments):
    """Run production consumer functions; no provider or publication is invoked."""
    typed = assertions.AssertionCheck.model_validate(typed).model_dump()
    proof_issues = assertions.assess_judgment(typed, provenance)
    bindings = assertions.checker_bindings(response_claims(public), provenance, fragments)
    normalized, citation_issues = normalize_judgment(typed, bindings)
    return typed, normalized, proof_issues + citation_issues


def compile_generic(*, source_ids=None, text=None):
    request, draft, provenance, fragments = generic(source_ids=source_ids)
    proposal = proposal_for(draft, provenance, fragments, text=text)
    candidate = revision.compile_local_revision(
        draft,
        provenance,
        proposal,
        fragments,
        authorized_claim_ids=[provenance["assertions"][0]["claim_id"]],
    )
    return request, draft, provenance, fragments, proposal, candidate


def test_normal_local_revision_reuses_parser_proofs_and_provider_payload_without_GEN():
    request, draft, provenance, fragments, proposal, candidate = compile_generic()
    before = deepcopy((draft, provenance, fragments, proposal))
    public = deepcopy(candidate["public_response"])
    public.pop("tutor_question")
    public.pop("learner_attempt_evaluation")
    assert (
        parse_response(
            json.dumps(public),
            mode=request.mode,
            condition=request.condition,
            evidence_ids=[row["evidence_id"] for row in request.evidence],
            answer_mode=request.answer_mode,
        )
        == public
    )
    rows = candidate["assertion_provenance"]
    typed, normalized, issues = consume(
        checker_labels(rows, negative_target=False), public, rows, fragments
    )
    assert not issues and typed["body_ok"] and normalized["body_ok"]
    assert all(row["status"] == "supported" for row in normalized["claims"])
    schema = assertions.bind_checker_schema(compact_schema(assertions.AssertionCheck), rows)
    Draft202012Validator(schema).validate(typed)
    messages = [
        {
            "role": "user",
            "content": json.dumps(
                {
                    "CLAIMS": response_claims(public),
                    "ASSERTION_PROOFS": assertions.checker_packet(rows),
                    "ACTUAL_CITATION_BINDINGS": assertions.checker_bindings(
                        response_claims(public), rows, fragments
                    ),
                }
            ),
        }
    ]
    wire = payload(request.config, messages, schema, assertions.CHECK_SCHEMA)
    assert wire["messages"] == messages
    assert wire["response_format"]["json_schema"]["schema"] == schema
    assert candidate["audit"]["candidate_state"] == "UNVERIFIED"
    assert candidate["audit"]["requires_complete_fresh_check"] is True
    assert candidate["audit"]["publication"] is False
    assert candidate["audit"]["semantic_support_certified"] is False
    assert (draft, provenance, fragments, proposal) == before


def test_missing_bridge_is_not_supplied_by_a_successful_mechanical_revision():
    _, _, _, fragments, _, candidate = compile_generic(source_ids=["F001"])
    provenance = candidate["assertion_provenance"]
    typed, normalized, issues = consume(
        checker_labels(provenance), candidate["public_response"], provenance, fragments
    )
    assert not issues
    assert typed["body_ok"] is normalized["body_ok"] is False
    assert normalized["claims"][0]["status"] == "partial"
    assert typed["claims"][0]["proof_audit"]["missing_predicates"]
    assert candidate["audit"]["semantic_support_certified"] is False


def test_contradictory_candidate_remains_rejected_by_unchanged_consumers():
    _, _, _, fragments, _, candidate = compile_generic(
        text=(
            "When valve A is closed, pressure from chamber P moves piston T "
            "and lifts its attached load against gravity."
        )
    )
    provenance = candidate["assertion_provenance"]
    authored = checker_labels(provenance)
    authored["claims"][0]["status"] = "unsupported"
    authored["claims"][0]["proof_audit"]["conditions_preserved"] = False
    authored["claims"][0]["proof_audit"]["missing_predicates"] = [
        "The source requires valve A open, contradicting the closed condition."
    ]
    authored["claims"][0]["citations"][0]["relation"] = "contradictory"
    typed, normalized, issues = consume(
        authored, candidate["public_response"], provenance, fragments
    )
    assert typed["body_ok"] is normalized["body_ok"] is False
    assert normalized["claims"][0]["status"] == "unsupported"
    assert {issue["code"] for issue in issues} == {"ACTUAL_CITATION_CONTRADICTORY"}
    assert candidate["audit"]["publication"] is False


def test_extra_ID_cannot_be_removed_or_hidden_by_optimistic_body_flags():
    _, _, _, fragments, _, candidate = compile_generic()
    provenance = candidate["assertion_provenance"]
    authored = checker_labels(provenance, negative_target=False)
    authored["claims"].append(
        {
            "claim_id": "practice_present",
            "basis": "nonfactual",
            "reason": "Authored foreign-ID control copied from the historical failure shape.",
        }
    )
    typed, normalized, issues = consume(
        authored, candidate["public_response"], provenance, fragments
    )
    assert typed["body_ok"] is normalized["body_ok"] is True
    assert {issue["code"] for issue in issues} == {"ASSERTION_CHECK_COVERAGE_INVALID"}
    schema = assertions.bind_checker_schema(compact_schema(assertions.AssertionCheck), provenance)
    assert list(Draft202012Validator(schema).iter_errors(typed))
    assert len(typed["claims"]) == 3 and typed["claims"][-1]["claim_id"] == "practice_present"
    assert candidate["audit"]["publication"] is False


@pytest.mark.parametrize("case_id", ["D160-Q01", "D160-Q02"])
def test_frozen162_raw_verdicts_and_requirement_failures_are_never_regraded(case_id):
    assert sha(CAPTURE_PATH.read_bytes()) == CAPTURE_SHA
    capture = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))
    case = next(row for row in capture["cases"] if row["case_id"] == case_id)
    before = deepcopy(case)
    raw = json.loads(case["actual162_checker_raw"])
    public = {
        "answer_text": "\n\n".join(
            row["rendered_text"]
            for row in case["provenance"]["assertions"]
            if row["answer_field"] == "answer_text"
        )
    }
    typed, normalized, issues = consume(raw, public, case["provenance"], case["original_fragments"])
    assert not issues and typed["body_ok"] is normalized["body_ok"] is False
    expected = (
        ["supported", "supported", "partial"]
        if case_id.endswith("Q01")
        else ["supported", "partial", "partial"]
    )
    assert [row["status"] for row in typed["claims"]] == expected
    bank = assertions.source_bank(case["original_fragments"], case["submitted_evidence"])
    contract, defects, _ = assess_requirements(
        typed,
        case["coverage"],
        [{**row, "fragment_id": row["source_id"]} for row in bank],
        answer_mode="textbook",
        teaching_mode="direct",
    )
    if case_id.endswith("Q02"):
        assert {row["code"] for row in contract} == {"REQUIREMENT_SUFFICIENCY_CONTRADICTION"}
        assert {row["code"] for row in defects} == {"SUFFICIENT_CONTEXT_UNDERUSED"}
    else:
        assert not contract and not defects
    assert case == before and case["native_public_answer_accepted"] is False


def test_exact_Q02_candidate_protects_supported_and_disputed_assertions_identically():
    assert sha(PROOF_PATH.read_bytes()) == PROOF_SHA
    proof = json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    exact = proof["minimal_controlled_candidate_NOT_published"]
    capture = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))
    case = next(row for row in capture["cases"] if row["case_id"] == "D160-Q02")
    draft = json.loads(case["original161_generation_raw"])
    before = deepcopy((case, draft))
    proposal = proposal_for(
        draft,
        case["provenance"],
        case["original_fragments"],
        index=2,
        text=exact["candidate_assertion"],
    )
    candidate = revision.compile_local_revision(
        draft,
        case["provenance"],
        proposal,
        case["original_fragments"],
        authorized_claim_ids=[exact["parent_canonical_claim_id"]],
    )
    assert candidate["public_response"]["answer_text"] == exact["candidate_public_body"]
    assert (
        sha(candidate["public_response"]["answer_text"].encode()) == exact["candidate_body_sha256"]
    )
    assert candidate["private_draft"]["answer_text"][:2] == draft["answer_text"][:2]
    assert (
        candidate["assertion_provenance"]["assertions"][:2] == case["provenance"]["assertions"][:2]
    )
    target = candidate["assertion_provenance"]["assertions"][2]
    assert target["assertion_sha256"] == exact["candidate_assertion_sha256"]
    assert target["claim_id"] != exact["parent_canonical_claim_id"]
    assert target["sources"] == case["provenance"]["assertions"][2]["sources"]
    assert candidate["audit"]["protected_claim_ids"] == [
        row["claim_id"] for row in case["provenance"]["assertions"][:2]
    ]
    assert candidate["audit"]["publication"] is False
    assert (case, draft) == before


@pytest.mark.parametrize(
    "defect",
    [
        "private_digest",
        "provenance_digest",
        "public_digest",
        "bank_digest",
        "prior_binding",
        "unknown_target",
        "duplicate_target",
        "missing_target",
        "protected_target",
        "no_op",
        "whitespace",
        "whole_row_delete",
        "append_field",
        "source_field",
        "third_target",
        "stale_provenance",
        "changed_source",
        "protected_canonical_collision",
    ],
)
def test_revision_binding_or_permission_faults_fail_closed_without_mutation(defect):
    _, draft, provenance, fragments = generic()
    proposal = proposal_for(draft, provenance, fragments)
    allowed = [provenance["assertions"][0]["claim_id"]]
    if defect.endswith("_digest"):
        field = {
            "private_digest": "parent_private_draft_sha256",
            "provenance_digest": "parent_provenance_sha256",
            "public_digest": "parent_public_response_sha256",
            "bank_digest": "parent_source_bank_sha256",
        }[defect]
        proposal[field] = "0" * 64
    elif defect == "prior_binding":
        proposal["edits"][0]["prior_binding_sha256"] = "0" * 64
    elif defect == "unknown_target":
        proposal["edits"][0]["claim_id"] = "unknown"
    elif defect == "duplicate_target":
        proposal["edits"].append(deepcopy(proposal["edits"][0]))
    elif defect == "missing_target":
        proposal["edits"] = []
    elif defect == "protected_target":
        proposal = proposal_for(draft, provenance, fragments, index=1)
    elif defect == "no_op":
        proposal["edits"][0]["replacement_text"] = provenance["assertions"][0]["assertion_text"]
    elif defect == "whitespace":
        proposal["edits"][0]["replacement_text"] = "   "
    elif defect == "whole_row_delete":
        proposal["edits"][0]["replacement_text"] = ""
    elif defect == "append_field":
        proposal["append_answer_text"] = "An arbitrary extra paragraph."
    elif defect == "source_field":
        proposal["edits"][0]["source_ids"] = ["F003"]
    elif defect == "third_target":
        proposal["edits"] *= 3
    elif defect == "stale_provenance":
        provenance["assertions"][1]["assertion_text"] = "Changed protected text."
    elif defect == "changed_source":
        fragments[0]["exact_text"] += " Changed."
    else:
        # Adopting a protected duplicate's text shifts its occurrence suffix.
        proposal["edits"][0]["replacement_text"] = provenance["assertions"][1]["assertion_text"]
    before = deepcopy((draft, provenance, proposal, fragments, allowed))
    with pytest.raises((ValueError, ValidationError)):
        revision.compile_local_revision(
            draft, provenance, proposal, fragments, authorized_claim_ids=allowed
        )
    assert (draft, provenance, proposal, fragments, allowed) == before
