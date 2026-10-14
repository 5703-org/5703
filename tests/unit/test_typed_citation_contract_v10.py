"""Authored contract/transport fixtures; no model-quality or human labels."""

from copy import deepcopy
from dataclasses import replace
import json

import pytest
from pydantic import ValidationError

from generation import GenerationService, RequestBudget
from generation.checker_contract import LEGACY_POLICY, SCHEMA_CORRECTIONS_POLICY
from generation.checker_encoding import decode
from generation.local_repair import VERSION as CLAIM_PATCH_POLICY
from generation.reliability_v5 import ReliableCheckV5, pessimistic_body_contract_issues
from generation.typed_citation_contract_v10 import (
    POLICY,
    pessimistic_body_contract_issues as citation_aware,
)
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer


def input_data(messages):
    data = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
    if "CHECKER_INPUT_ENCODING" in data:
        data = decode(data)
    if "SOURCE_FRAGMENT_TABLE" in data:
        table = data["SOURCE_FRAGMENT_TABLE"]
        data["SOURCE_FRAGMENTS"] = [dict(zip(table["columns"], row)) for row in table["rows"]]
    return data


def uncited_science(messages, *, body_ok=False):
    data = input_data(messages)
    value = checker(messages, body_ok=body_ok)
    by_claim = {row["claim_id"]: row for row in data["CLAIMS"]}
    # Preserve the original identity for every independently
    # classified factual sentence, including summary and short-answer fields.
    for row in value["claims"]:
        cid = row["claim_id"]
        if not by_claim[cid]["evidence_ids"]:
            row.clear()
            row.update(
                claim_id=cid,
                basis="textbook",
                status="supported",
                citations=[],
                reason="Authored contradictory support metadata for an uncited scientific sentence.",
            )
    return value


def missing_draft():
    return answer(
        "Photosynthesis uses light energy. Photosynthesis uses light energy. [ev_001]",
        short_answer="Photosynthesis uses light energy.",
    )


def repaired_draft():
    return answer(
        "Photosynthesis uses light energy. [ev_001] Photosynthesis uses light energy. [ev_001]",
        short_answer="Photosynthesis uses light energy. [ev_001]",
    )


def run(values, *, policy=POLICY, calls=4, request=None):
    transport = Script(values)
    value = request or req(joint_checker_policy=policy)
    return GenerationService(transport).generate(value, RequestBudget(max_calls=calls)), transport


def test_current_uncited_fact_uses_local_repair_then_mandatory_full_final_check():
    initial = missing_draft()
    fixed = repaired_draft()
    out, transport = run([initial, uncited_science, fixed, checker])
    assert out.succeeded, out.error
    assert out.response == fixed
    assert out.budget["consumed_calls"] == len(transport.calls) == 4
    assert [row["stage"] for row in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    first = out.checks[0]
    assert first["judgment"]["body_ok"] is False
    assert first["effective_body_ok"] is False and not first["accepted"]
    assert first["checker_inconsistencies"] == []
    assert len(first["body_contract_draft_defects"]) == 2
    assert all(row["publication_override"] is False for row in first["body_contract_draft_defects"])
    assert "CHECK_SUPPORT_WITHOUT_SOURCE" in {row["code"] for row in first["structural_issues"]}
    assert not out.drafts[0]["published"]
    assert out.checks[-1]["accepted"] is True
    protected = "Photosynthesis uses light energy. [ev_001]"
    assert protected in out.drafts[0]["response"]["answer_text"]
    assert protected in out.response["answer_text"]
    assert out.attribution["claims"][0]["support"]["human_rating"] is None


@pytest.mark.parametrize("final_pass", [True, False])
def test_current_claim_patch_policy_keeps_approved_science_exact_and_checks_every_repaired_claim(
    final_pass,
):
    seen = []

    def patch(messages):
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[-1])
        protected = data["protected_exact_claims"]
        assert len(protected) == 1
        assert protected[0]["text"] == "Photosynthesis uses light energy. [ev_001]"
        assert {row["code"] for row in data["structural_issues"]} >= {
            "CHECK_SUPPORT_WITHOUT_SOURCE",
            "CURRENT_FACTUAL_CITATION_MISSING",
        }
        targets = [row for row in data["original_claims"] if not row["evidence_ids"]]
        assert len(targets) == 2
        seen.extend(targets)
        return {
            "edits": [
                {"claim_id": row["claim_id"], "replacement_text": row["text"] + " [ev_001]"}
                for row in targets
            ],
            "append_answer_text": "",
        }

    def final(messages):
        value = checker(messages)
        if not final_pass:
            value["body_ok"] = False
            value["claims"][0]["status"] = "unsupported"
        return value

    out, transport = run(
        [missing_draft(), uncited_science, patch, final],
        request=req(joint_checker_policy=POLICY, repair_policy=CLAIM_PATCH_POLICY),
    )
    assert out.succeeded is final_pass
    assert len(transport.calls) == out.budget["consumed_calls"] == 4
    assert transport.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert len(seen) == 2
    assert out.drafts[1]["response"] == repaired_draft()
    assert out.checks[-1]["accepted"] is final_pass
    if not final_pass:
        assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
        assert out.delivered_projection == {}


@pytest.mark.parametrize("body_ok", [False, True])
def test_final_unrepaired_uncited_facts_remain_unpublished(body_ok):
    def negative(messages):
        return uncited_science(messages, body_ok=body_ok)

    out, transport = run([missing_draft(), negative, missing_draft(), negative])
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == len(transport.calls) == 4
    assert not any(row["accepted"] for row in out.checks)
    assert out.delivered_projection == {}


def test_old_typed_v5_keeps_the_three_call_unchanged_draft_failure():
    out, transport = run(
        [missing_draft(), uncited_science, uncited_science],
        policy="typed_joint_v5",
    )
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert len(transport.calls) == out.budget["consumed_calls"] == 3
    assert [row["stage"] for row in out.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
    ]
    assert out.checks[0]["checker_inconsistencies"][0]["code"] == (
        "BODY_REJECTED_WITH_ALL_FACTS_SUPPORTED"
    )
    assert out.checks[0]["projection_hash"] == out.checks[1]["projection_hash"]
    assert "TYPED CITATION V10" not in transport.calls[0][0][0]["content"]
    assert "TYPED CITATION V10" not in transport.calls[1][0][0]["content"]


def test_good_current_citations_and_negative_aggregate_still_recheck_unchanged_draft():
    def negative(messages):
        return checker(messages, body_ok=False)

    out, transport = run([answer(), negative, checker], calls=3)
    assert out.succeeded, out.error
    assert len(transport.calls) == 3
    assert out.checks[0]["body_contract_draft_defects"] == []
    assert out.checks[0]["checker_inconsistencies"][0]["code"] == (
        "BODY_REJECTED_WITH_ALL_FACTS_SUPPORTED"
    )
    assert out.checks[0]["projection_hash"] == out.checks[1]["projection_hash"]


@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_named_semantic_negatives_remain_negative_and_require_answer_repair(status):
    def negative(messages):
        value = checker(messages, body_ok=False)
        value["claims"][0]["status"] = status
        return value

    out, transport = run([answer(), negative, answer(), checker])
    assert out.succeeded, out.error
    assert len(transport.calls) == 4
    assert out.checks[0]["judgment"]["claims"][0]["status"] == status
    assert out.checks[0]["effective_body_ok"] is False
    assert [row["stage"] for row in out.attempts][-2:] == ["semantic_repair", "joint_recheck"]


@pytest.mark.parametrize("calls", [2, 3])
def test_missing_citation_cannot_start_repair_without_two_remaining_calls(calls):
    out, transport = run([missing_draft(), uncited_science], calls=calls)
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(transport.calls) == 2
    block = out.error["details"]["publication_block"]
    assert block["required_calls_for_repair_and_recheck"] == 2
    assert block["stop_reason"] == "insufficient_calls_for_repair_and_recheck"


@pytest.mark.parametrize("gate", ["complete_answer", "attempt_evaluation_ok", "tutor_question_ok"])
def test_final_local_repair_does_not_bypass_other_required_gates(gate):
    def negative(messages):
        return checker(messages, **{gate: False})

    out, _ = run([missing_draft(), uncited_science, repaired_draft(), negative])
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.delivered_projection == {}


@pytest.mark.parametrize(
    "defect", ["condition_lost", "requested_content_omitted", "semantic_partial"]
)
def test_final_repair_must_preserve_conditions_required_knowledge_and_semantic_support(defect):
    def negative(messages):
        value = checker(messages)
        if defect == "condition_lost":
            value["requirements"][0]["conditions_preserved"] = False
        elif defect == "requested_content_omitted":
            value["requirements"][0]["response_coverage"] = "not_addressed"
        else:
            value["claims"][0]["status"] = "partial"
            value["body_ok"] = False
        return value

    out, transport = run([missing_draft(), uncited_science, repaired_draft(), negative])
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(transport.calls) == 4
    assert out.checks[-1]["accepted"] is False
    assert out.delivered_projection == {}


@pytest.mark.parametrize("defect", ["unknown_claim", "unknown_fragment", "extra_field"])
def test_invalid_first_checker_cannot_use_current_missing_citation_routing(defect):
    def malformed(messages):
        value = uncited_science(messages)
        if defect == "unknown_claim":
            value["claims"][0]["claim_id"] = "foreign"
        elif defect == "unknown_fragment":
            cited = next(row for row in value["claims"] if row.get("citations"))
            cited["citations"][0]["fragment_ids"] = ["FOREIGN"]
        else:
            value["claims"][0]["reason_detail"] = "Forbidden field."
        return value

    out, transport = run([missing_draft(), malformed, malformed])
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert len(transport.calls) == 3
    assert [row["stage"] for row in out.attempts][-1] == "checker_contract_repair"
    assert not any(row.get("body_contract_draft_defects") for row in out.checks)


def test_new_generation_and_checker_prompts_are_opt_in_and_evidence_ceiling_is_unchanged():
    out, transport = run([answer(), checker])
    assert out.succeeded
    assert len(transport.calls) == 2
    assert "TYPED CITATION V10: COMPLETE LOCAL CITATIONS" in transport.calls[0][0][0]["content"]
    rubric = transport.calls[1][0][0]["content"]
    assert "at most EIGHT evidence records per requirement" in rubric
    assert "EXAMPLE_UNCITED" in rubric
    assert out.budget["max_calls"] == 4 and out.budget["max_active_seconds"] == 180
    assert out.token_budget["evidence_packing"]["text_token_ceiling"] == 3000


def helper_fixture():
    normalized = [
        {
            "claim_id": "c1",
            "basis": "textbook",
            "factual": True,
            "status": "supported",
            "fragment_ids": [],
            "reason": "Authored.",
        },
        {
            "claim_id": "c2",
            "basis": "textbook",
            "factual": True,
            "status": "supported",
            "fragment_ids": ["F001"],
            "reason": "Authored.",
        },
    ]
    raw = [
        {
            "claim_id": "c1",
            "basis": "textbook",
            "status": "supported",
            "citations": [],
            "reason": "Authored.",
        },
        {
            "claim_id": "c2",
            "basis": "textbook",
            "status": "supported",
            "citations": [
                {"evidence_id": "ev_001", "fragment_ids": ["F001"], "relation": "supporting"}
            ],
            "reason": "Authored.",
        },
    ]
    return {
        "judgment": {"body_ok": False, "claims": normalized},
        "typed_judgment": {"body_ok": False, "claims": raw},
        "claims": [
            {"claim_id": "c1", "evidence_ids": []},
            {"claim_id": "c2", "evidence_ids": ["ev_001"]},
        ],
        "bindings": [
            {"claim_id": "c1", "citations": []},
            {
                "claim_id": "c2",
                "citations": [{"evidence_id": "ev_001", "allowed_fragment_ids": ["F001"]}],
            },
        ],
        "fragments": [
            {
                "fragment_id": "F001",
                "evidence_id": "ev_001",
                "complete_block": True,
                "block_kind": "prose",
            }
        ],
        "schema_validated": True,
    }


def test_pure_current_empty_binding_is_a_blocking_draft_defect_and_does_not_mutate_verdict():
    fixture = helper_fixture()
    saved = deepcopy(fixture)
    issues, defects = citation_aware(**fixture)
    assert issues == []
    assert [row["claim_id"] for row in defects] == ["c1"]
    assert defects[0]["code"] == "CURRENT_FACTUAL_CITATION_MISSING"
    assert defects[0]["requires_fresh_final_check"] is True
    assert fixture == saved


@pytest.mark.parametrize(
    "defect",
    [
        "schema_unvalidated",
        "unknown_claim",
        "duplicate_claim",
        "foreign_fragment",
        "different_source",
        "incomplete_source",
        "irrelevant",
        "contradictory",
        "missing_assessment",
        "extra_assessment",
        "empty_selected_fragment",
        "invented_fragment_on_empty_binding",
        "changed_basis",
        "unexpected_raw_field",
        "unknown_factual_basis",
        "changed_actual_binding",
    ],
)
def test_no_structural_or_identity_failure_is_deferred(defect):
    f = helper_fixture()
    raw = f["typed_judgment"]["claims"]
    if defect == "schema_unvalidated":
        f["schema_validated"] = False
    elif defect == "unknown_claim":
        raw[0]["claim_id"] = "foreign"
    elif defect == "duplicate_claim":
        raw.append(deepcopy(raw[0]))
    elif defect == "foreign_fragment":
        raw[1]["citations"][0]["fragment_ids"] = ["FOREIGN"]
    elif defect == "different_source":
        f["fragments"][0]["evidence_id"] = "ev_999"
    elif defect == "incomplete_source":
        f["fragments"][0]["complete_block"] = False
    elif defect in {"irrelevant", "contradictory"}:
        raw[1]["citations"][0]["relation"] = defect
    elif defect == "missing_assessment":
        raw[1]["citations"] = []
    elif defect == "extra_assessment":
        raw[1]["citations"].append(deepcopy(raw[1]["citations"][0]))
    elif defect == "empty_selected_fragment":
        raw[1]["citations"][0]["fragment_ids"] = []
    elif defect == "invented_fragment_on_empty_binding":
        f["judgment"]["claims"][0]["fragment_ids"] = ["F001"]
    elif defect == "changed_basis":
        raw[0]["basis"] = "evidence_limitation"
    elif defect == "unexpected_raw_field":
        raw[0]["factual"] = True
    elif defect == "unknown_factual_basis":
        raw[1]["basis"] = f["judgment"]["claims"][1]["basis"] = "problem_input"
    else:
        f["claims"][0]["evidence_ids"] = ["ev_999"]
    issues, obligations = citation_aware(**f)
    assert obligations == []
    assert issues == pessimistic_body_contract_issues(f["judgment"])
    assert issues[0]["publication_override"] is False


@pytest.mark.parametrize("count", [8, 9])
def test_requirement_evidence_limit_is_strict_and_never_truncated(count):
    observed = []

    def sized(messages):
        value = checker(messages)
        support = value["requirements"][0]["evidence"][0]
        value["requirements"][0]["evidence"] = [deepcopy(support) for _ in range(count)]
        observed.append(deepcopy(value))
        return value

    out, transport = run([answer(), sized, checker], calls=3)
    assert out.succeeded, out.error
    assert len(observed[0]["requirements"][0]["evidence"]) == count
    if count == 8:
        assert len(transport.calls) == 2
        assert ReliableCheckV5.model_validate(observed[0]).requirements[0].evidence
    else:
        assert len(transport.calls) == 3
        issue = out.checks[0]["checker_inconsistencies"][0]
        assert issue["field_errors"] == [
            {"path": ["requirements", 0, "evidence"], "error_type": "too_long"}
        ]
        with pytest.raises(ValidationError):
            ReliableCheckV5.model_validate(observed[0])
        assert len(json.loads(out.checks[0]["raw_text"])["requirements"][0]["evidence"]) == 9


@pytest.mark.parametrize("contract", [LEGACY_POLICY, SCHEMA_CORRECTIONS_POLICY])
def test_persistent_over_eight_records_exhaust_the_same_bounded_call_budget(contract):
    def too_many(messages):
        value = checker(messages)
        support = value["requirements"][0]["evidence"][0]
        value["requirements"][0]["evidence"] = [deepcopy(support) for _ in range(9)]
        return value

    out, transport = run(
        [answer(), too_many, too_many, too_many],
        request=req(joint_checker_policy=POLICY, checker_contract_policy=contract),
    )
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert len(transport.calls) == (3 if contract == LEGACY_POLICY else 4)
    assert out.budget["max_calls"] == 4 and out.budget["max_active_seconds"] == 180


def test_new_policy_requires_current_enhanced_interactive_gate():
    out, transport = run([], request=req(joint_checker_policy=POLICY, enhancement_version=None))
    assert out.response is None and out.error["code"] == "JOINT_CHECKER_POLICY_INCOMPATIBLE"
    assert not transport.calls
    old = replace(req(joint_checker_policy=POLICY), reliability_policy="evidence_reliability_v4")
    out, transport = run([], request=old)
    assert out.response is None and out.error["code"] == "JOINT_CHECKER_POLICY_INCOMPATIBLE"
    assert not transport.calls
