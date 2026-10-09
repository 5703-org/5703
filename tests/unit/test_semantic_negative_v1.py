"""Authored routing regressions; no source-entailment or human-quality labels."""

from copy import deepcopy

import pytest

from generation.semantic_negative_v1 import AGGREGATE_ONLY, route_semantic_negatives


def judgment():
    return {
        "body_ok": True,
        "specific_help": True,
        "scope_ok": True,
        "suggestions_ok": True,
        "evidence_display_ok": True,
        "cumulative_ok": True,
        "complete_answer": True,
        "coverage": "full",
        "missing_facets": [],
        "limitations_explicit": True,
        "attempt_evaluation_ok": True,
        "tutor_question_ok": True,
        "non_repetitive_next_action": True,
        "claims": [
            {"claim_id": "c1", "factual": True, "basis": "textbook", "status": "supported"},
            {"claim_id": "c2", "factual": True, "basis": "textbook", "status": "supported"},
        ],
        "requirements": [
            {
                "requirement_id": "r1",
                "sufficiency": "sufficient",
                "conditions_preserved": True,
                "response_coverage": "covered",
            }
        ],
    }


def policy(mode="direct", **kwargs):
    return {
        "teaching_mode": mode,
        "check_suggestions": False,
        "control_evidence": False,
        "check_cumulative": False,
        **kwargs,
    }


def route(data, **kwargs):
    arguments = {
        "schema_validated": True,
        "inconsistencies": [{"code": "COMPLETE_PARTIAL_WITHOUT_LIMITS"}],
        "contract_issues": [],
        "semantic_issues": [],
        "teaching_policy": policy(),
        **kwargs,
    }
    return route_semantic_negatives(data, **arguments)


def test_same_draft_valid_partial_cannot_be_promoted_by_aggregate_correction():
    data = judgment()
    data.update(body_ok=False, coverage="supported_partial", limitations_explicit=False)
    data["claims"][0]["status"] = "partial"
    data["requirements"][0].update(sufficiency="partial", response_coverage="partial")
    issues = [
        {"code": "COMPACT_UNIT_PARTIAL", "claim_id": "c1", "unit_id": "U02"},
        {"code": "REQUIREMENT_LIMITATION_MISSING", "requirement_id": "r1"},
    ]
    before = deepcopy(data)
    result = route(data, semantic_issues=issues)
    assert result["route"] == "semantic_repair"
    assert result["remaining_inconsistencies"] == []
    assert all(issue in result["semantic_issues"] for issue in issues)
    assert result["deferred_aggregate_issues"][0]["code"] == "COMPLETE_PARTIAL_WITHOUT_LIMITS"
    assert data == before
    assert data["claims"][1]["status"] == "supported"
    assert result["publication_override"] is False


def test_valid_unit_negative_wins_over_supported_compound_and_body():
    data = judgment()
    issues = [{"code": "COMPACT_UNIT_CONDITION_CHANGED", "claim_id": "c1", "unit_id": "U02"}]
    result = route(data, semantic_issues=issues)
    assert result["route"] == "semantic_repair"
    assert result["semantic_issues"] == issues
    assert data["body_ok"] and data["claims"][0]["status"] == "supported"
    assert result["judgment_changed"] is False


def test_named_requirement_gap_with_full_coverage_is_deferred_but_retained():
    data = judgment()
    data["requirements"][0].update(sufficiency="partial", response_coverage="limitation")
    result = route(
        data,
        inconsistencies=[],
        contract_issues=[{"code": "FULL_COVERAGE_WITH_REQUIREMENT_GAP"}],
    )
    assert result["route"] == "semantic_repair"
    assert result["remaining_contract_issues"] == []
    assert {r["code"] for r in result["retained_negatives"]} == {"REQUIREMENT_GAP"}
    assert result["semantic_issues"] == [{"code": "REQUIREMENT_GAP", "requirement_id": "r1"}]
    assert data["body_ok"] and data["complete_answer"] and data["limitations_explicit"]


@pytest.mark.parametrize("code", sorted(AGGREGATE_ONLY))
def test_only_known_aggregate_codes_are_deferred_with_real_granular_negative(code):
    data = judgment()
    data["claims"][0]["status"] = "unsupported"
    result = route(data, inconsistencies=[{"code": code}])
    assert result["route"] == "semantic_repair"
    assert result["deferred_aggregate_issues"][0]["code"] == code
    assert any(row["code"] == "CLAIM_UNSUPPORTED" for row in result["retained_negatives"])


@pytest.mark.parametrize(
    "code",
    [
        "CHECKER_SCHEMA_INVALID",
        "COMPACT_UNIT_IDENTITY_MISMATCH",
        "COMPACT_ACTUAL_CITATION_FRAGMENT_INVALID",
        "COMPACT_QUOTE_REFERENCE_INVALID",
        "REQUIREMENT_IDENTITY_MISMATCH",
        "REQUIREMENT_SOURCE_QUOTE_INVALID",
        "REQUIREMENT_GAP_UNSPECIFIED",
        "DERIVED_WITHOUT_PROOF",
        "UNKNOWN_FUTURE_CODE",
    ],
)
@pytest.mark.parametrize("location", ["inconsistencies", "contract_issues"])
def test_true_contract_or_source_defects_are_never_deferred(code, location):
    data = judgment()
    data["claims"][0]["status"] = "partial"
    issues = [{"code": code, "claim_id": "c1"}]
    result = route(data, **{location: issues})
    assert result["route"] == "contract_correction"
    key = (
        "remaining_inconsistencies"
        if location == "inconsistencies"
        else "remaining_contract_issues"
    )
    assert result[key] == issues
    assert result["deferred_aggregate_issues"] == []


def test_one_source_identity_defect_blocks_deferral_of_other_aggregate_issue():
    data = judgment()
    data["claims"][0]["status"] = "partial"
    result = route(data, contract_issues=[{"code": "FRAGMENT_IDENTITY_MISMATCH"}])
    assert result["remaining_inconsistencies"] == [{"code": "COMPLETE_PARTIAL_WITHOUT_LIMITS"}]
    assert result["route"] == "contract_correction"


def test_pessimistic_body_alone_preserves_existing_contract_correction():
    data = judgment()
    data["body_ok"] = False
    result = route(data, inconsistencies=[{"code": "BODY_REJECTED_WITH_ALL_FACTS_SUPPORTED"}])
    assert result["route"] == "contract_correction"
    assert result["retained_negatives"] == []


@pytest.mark.parametrize(
    ("field", "flag"),
    [
        ("specific_help", None),
        ("scope_ok", None),
        ("non_repetitive_next_action", None),
        ("suggestions_ok", "check_suggestions"),
        ("evidence_display_ok", "control_evidence"),
        ("cumulative_ok", "check_cumulative"),
    ],
)
def test_active_hint_gates_remain_repair_obligations(field, flag):
    data = judgment()
    data[field] = False
    settings = {flag: True} if flag else {}
    result = route(data, teaching_policy=policy("hint", **settings))
    assert result["route"] == "semantic_repair"
    assert any(row["code"] == "CHECK_" + field.upper() for row in result["retained_negatives"])


@pytest.mark.parametrize(
    "field", ["scope_ok", "suggestions_ok", "evidence_display_ok", "cumulative_ok"]
)
def test_inactive_direct_teaching_flags_do_not_force_repair(field):
    data = judgment()
    data[field] = False
    result = route(data)
    assert result["route"] == "contract_correction"
    assert result["retained_negatives"] == []


@pytest.mark.parametrize("field", ["suggestions_ok", "evidence_display_ok", "cumulative_ok"])
def test_disabled_optional_hint_flags_do_not_force_repair(field):
    data = judgment()
    data[field] = False
    assert route(data, teaching_policy=policy("hint"))["route"] == "contract_correction"


@pytest.mark.parametrize("field", ["attempt_evaluation_ok", "tutor_question_ok", "complete_answer"])
def test_active_answer_gates_are_repairable_even_when_claims_supported(field):
    data = judgment()
    data[field] = False
    assert route(data)["route"] == "semantic_repair"


def test_honest_limited_partial_is_not_a_new_semantic_error():
    data = judgment()
    data.update(coverage="supported_partial", limitations_explicit=True)
    data["requirements"][0].update(sufficiency="partial", response_coverage="limitation")
    result = route(data, inconsistencies=[])
    assert result["route"] == "ordinary_validation"
    assert result["retained_negatives"] == []


@pytest.mark.parametrize("basis", ["problem_input", "derived_calculation", "general_knowledge"])
def test_given_calculation_and_general_negative_do_not_become_textbook_support(basis):
    data = judgment()
    data["claims"][0].update(basis=basis, status="unsupported")
    before = deepcopy(data)
    result = route(data)
    assert result["route"] == "semantic_repair"
    assert data == before
    assert result["independent_semantic_evaluation"] is False
    assert result["human_rating"] is None


def test_valid_requirement_conditions_loss_is_kept_without_inventing_a_fact_label():
    data = judgment()
    data["requirements"][0]["conditions_preserved"] = False
    result = route(data)
    assert result["route"] == "semantic_repair"
    assert result["retained_negatives"] == [
        {"origin": "requirement", "requirement_id": "r1", "code": "REQUIREMENT_CONDITION_LOST"}
    ]


@pytest.mark.parametrize("validated", [False, None, 1, "true"])
def test_schema_validation_is_not_assumed_from_truthy_input(validated):
    data = judgment()
    data["claims"][0]["status"] = "partial"
    assert route(data, schema_validated=validated)["route"] == "contract_correction"


@pytest.mark.parametrize(
    "mutation", ["missing_gate", "string_bool", "missing_id", "unknown_status"]
)
def test_incomplete_normalized_projection_is_not_used_for_semantic_routing(mutation):
    data = judgment()
    data["claims"][0]["status"] = "partial"
    if mutation == "missing_gate":
        data.pop("scope_ok")
    elif mutation == "string_bool":
        data["body_ok"] = "false"
    elif mutation == "missing_id":
        data["claims"][0].pop("claim_id")
    else:
        data["claims"][0]["status"] = "unknown"
    assert route(data)["route"] == "contract_correction"


def test_unvalidated_and_missing_judgment_do_not_certify_any_negative():
    assert route(None)["route"] == "contract_correction"


def test_returned_metadata_is_independent_of_original_input_and_other_revisions():
    data = judgment()
    data["claims"][0]["status"] = "partial"
    source_issue = {"code": "COMPACT_UNIT_PARTIAL", "claim_id": "c1", "unit_id": "U01"}
    first = route(data, semantic_issues=[source_issue])
    first["semantic_issues"][0]["code"] = "MUTATED_COPY"
    assert source_issue["code"] == "COMPACT_UNIT_PARTIAL"
    fresh = route(judgment(), inconsistencies=[])
    assert fresh["route"] == "ordinary_validation"
    assert fresh["retained_negatives"] == []
    assert fresh["cross_revision_state"] is False
