"""Authored V9 routing/publication fixtures; no model or human accuracy labels."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from generation import GenerationService, RequestBudget
from generation.checker_encoding_v6 import decode
from generation.reliability_v4 import normalize_judgment
from generation.reliability_v6 import expand_compact_judgment
from generation.semantic_negative_v2 import CHECKER_POLICY, route_semantic_negatives
from test_compact_checker_pipeline import candidate
from test_compact_checker_v7_pipeline import check
from test_enhancement_generation import Script, answer

FACT = "Photosynthesis uses light energy. [ev_001]"
LIMIT = "The supplied source does not state the requested temperature condition."


def data_from(messages):
    data = next(json.loads(row["content"]) for row in messages if row["content"].startswith("{"))
    return decode(data) if "CHECKER_INPUT_ENCODING" in data else data


def limited_check(messages):
    data = data_from(messages)
    value = check(messages)
    target = next(row for row in data["CLAIMS"] if LIMIT in row["text"])
    value["claims"] = [
        {
            "claim_id": row["claim_id"],
            "basis": "evidence_limitation",
            "reason": "Authored source gap.",
        }
        if row["claim_id"] == target["claim_id"]
        else row
        for row in value["claims"]
    ]
    value.update(
        coverage="supported_partial",
        missing_facets=["temperature condition"],
        limitations_explicit=True,
    )
    value["requirements"][0].update(
        sufficiency="partial",
        response_coverage="partial",
        missing_information="The requested temperature condition is absent from the authored source.",
    )
    return value


def patch(messages):
    data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[-1])
    target = next(row for row in data["original_claims"] if LIMIT in row["text"])
    kept = next(row for row in data["original_claims"] if row["text"] == FACT)
    assert kept in data["protected_exact_claims"]
    codes = {row["code"] for row in data["structural_issues"]}
    assert "CITATION_ON_EVIDENCE_LIMITATION" in codes
    assert "CHECK_LIMITATION_BASIS_INVALID" in codes
    return {
        "edits": [{"claim_id": target["claim_id"], "replacement_text": LIMIT}],
        "append_answer_text": "",
    }


def run(steps, *, policy=CHECKER_POLICY, calls=4, **changes):
    adapter = Script(steps)
    out = GenerationService(adapter).generate(
        candidate(joint_checker_policy=policy, **changes), RequestBudget(max_calls=calls)
    )
    return out, adapter


def capture():
    out, adapter = run([answer(FACT + " " + LIMIT + " [ev_001]"), limited_check], calls=2)
    data = data_from(adapter.calls[1][0])
    raw = limited_check(adapter.calls[1][0])
    expanded, contract, semantic, _ = expand_compact_judgment(
        raw, data, answer_mode="textbook", teaching_mode="direct"
    )
    normalized, bindings = normalize_judgment(expanded, data["ACTUAL_CITATION_BINDINGS"])
    return (
        normalized,
        {
            "schema_validated": True,
            "inconsistencies": contract,
            "contract_issues": bindings + contract,
            "semantic_issues": semantic,
            "teaching_policy": data["POLICY"],
            "raw_compact": raw,
            "check_data": data,
        },
        out,
    )


def test_proven_cited_limitation_routes_local_patch_and_exact_fresh_final_check():
    out, adapter = run(
        [answer(FACT + " " + LIMIT + " [ev_001]"), limited_check, patch, limited_check]
    )
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4
    assert [row["stage"] for row in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.response["answer_text"] == FACT + " " + LIMIT
    assert not out.checks[0]["accepted"] and out.checks[1]["accepted"]
    routing = out.checks[0]["semantic_negative_routing"]
    assert routing["version"] == "semantic_negative_routing_v2"
    assert routing["route"] == "semantic_repair"
    assert routing["publication_override"] is False and routing["judgment_changed"] is False
    assert {row["code"] for row in routing["deferred_citation_basis_issues"]} == {
        "COMPACT_UNEXPECTED_CITATION_FOR_BASIS",
        "UNEXPECTED_CITATION_FOR_BASIS",
    }
    assert routing["current_limitation_identity_proof"][0]["identity_only"] is True
    assert out.checks[0]["projection_hash"] != out.checks[1]["projection_hash"]
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert all(row["human_rating"] is None for row in out.checks)


def test_v8_keeps_the_same_draft_contract_correction_and_three_call_failure():
    out, _ = run(
        [answer(FACT + " " + LIMIT + " [ev_001]"), limited_check, limited_check],
        policy="scoped_compact_v8",
        calls=3,
    )
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == 3
    assert not any(row["stage"] == "semantic_repair" for row in out.attempts)
    assert out.checks[0]["projection_hash"] == out.checks[1]["projection_hash"]
    assert all(
        row["semantic_negative_routing"]["version"] == "semantic_negative_routing_v1"
        for row in out.checks
    )


def test_repaired_body_still_needs_positive_final_semantic_and_independent_gates():
    def negative_final(messages):
        value = limited_check(messages)
        value["claims"][0]["status"] = "unsupported"
        value["claims"][0]["units"][0]["status"] = "unsupported"
        value["body_ok"] = False
        return value

    out, _ = run([answer(FACT + " " + LIMIT + " [ev_001]"), limited_check, patch, negative_final])
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 4
    assert all(not row["accepted"] for row in out.checks)


@pytest.mark.parametrize("calls", [2, 3])
def test_missing_repair_or_final_check_budget_never_publishes(calls):
    steps = [answer(FACT + " " + LIMIT + " [ev_001]"), limited_check] + (
        [patch] if calls == 3 else []
    )
    out, _ = run(steps, calls=calls)
    assert out.response is None
    assert out.budget["consumed_calls"] <= calls


@pytest.mark.parametrize(
    "code",
    [
        "CHECKER_SCHEMA_INVALID",
        "COMPACT_QUOTE_REFERENCE_INVALID",
        "COMPACT_QUOTE_SOURCE_INCOMPLETE",
        "COMPACT_PROOF_ASSESSED_FRAGMENT_MISMATCH",
        "ACTUAL_CITATION_FRAGMENT_INVALID",
        "FRAGMENT_IDENTITY_MISMATCH",
        "CLAIM_IDENTITY_MISMATCH",
        "REQUEST_TARGET_PRESENCE_STATUS_MISMATCH",
        "REQUIREMENT_SOURCE_QUOTE_INVALID",
        "REQUIREMENT_IDENTITY_MISMATCH",
        "UNKNOWN_NEW_CODE",
    ],
)
@pytest.mark.parametrize("location", ["inconsistencies", "contract_issues"])
def test_any_other_contract_source_quote_or_proof_issue_stays_fail_closed(code, location):
    normalized, args, _ = capture()
    args[location] = args[location] + [{"code": code}]
    out = route_semantic_negatives(normalized, **args)
    assert out["route"] == "contract_correction"
    assert not out.get("deferred_citation_basis_issues")
    assert not out["publication_override"] and not out["judgment_changed"]


@pytest.mark.parametrize(
    "fault",
    [
        "unchecked",
        "other_basis",
        "raw_extra_union_field",
        "missing_raw_gate",
        "missing_normalized_gate",
        "changed_normalized_gate",
        "factual_flag",
        "normalized_fragment",
        "normalized_reason",
        "missing_one_code",
        "foreign_issue_claim",
        "extra_issue_metadata",
        "foreign_source",
        "missing_source",
        "missing_scope",
        "stale_scope",
        "missing_body_evidence",
        "changed_body",
        "changed_current_claim",
        "duplicate_claim",
        "changed_binding",
        "missing_allowed_fragment",
        "changed_unit_range",
        "missing_units",
    ],
)
def test_only_exact_current_limitation_union_and_bound_body_can_route(fault):
    normalized, args, _ = capture()
    args, normalized = deepcopy(args), deepcopy(normalized)
    cid = next(
        row["claim_id"]
        for row in args["raw_compact"]["claims"]
        if row["basis"] == "evidence_limitation"
    )
    raw = next(row for row in args["raw_compact"]["claims"] if row["claim_id"] == cid)
    norm = next(row for row in normalized["claims"] if row["claim_id"] == cid)
    current = next(row for row in args["check_data"]["CLAIMS"] if row["claim_id"] == cid)
    binding = next(
        row for row in args["check_data"]["ACTUAL_CITATION_BINDINGS"] if row["claim_id"] == cid
    )
    if fault == "unchecked":
        args["schema_validated"] = False
    elif fault == "other_basis":
        raw["basis"] = norm["basis"] = "nonfactual"
    elif fault == "raw_extra_union_field":
        raw["units"] = []
    elif fault == "missing_raw_gate":
        args["raw_compact"].pop("scope_ok")
    elif fault == "missing_normalized_gate":
        normalized.pop("scope_ok")
    elif fault == "changed_normalized_gate":
        normalized["scope_ok"] = False
    elif fault == "factual_flag":
        norm["factual"] = True
    elif fault == "normalized_fragment":
        norm["fragment_ids"] = ["F001"]
    elif fault == "normalized_reason":
        norm["reason"] = "Different judgment"
    elif fault == "missing_one_code":
        for field in ("inconsistencies", "contract_issues"):
            args[field] = [
                row for row in args[field] if row["code"] != "UNEXPECTED_CITATION_FOR_BASIS"
            ]
    elif fault == "foreign_issue_claim":
        args["contract_issues"][0]["claim_id"] = "foreign"
    elif fault == "extra_issue_metadata":
        args["contract_issues"][0]["unknown"] = True
    elif fault == "foreign_source":
        args["check_data"]["SOURCE_FRAGMENTS"][0]["evidence_id"] = "ev_999"
    elif fault == "missing_source":
        args["check_data"]["SOURCE_FRAGMENTS"] = []
    elif fault == "missing_scope":
        args["check_data"].pop("CLAIM_CITATION_SCOPE")
    elif fault == "stale_scope":
        args["check_data"]["CLAIM_CITATION_SCOPE"]["claims"][-1]["actual_citations"] = []
    elif fault == "missing_body_evidence":
        current.pop("evidence_ids")
    elif fault == "changed_body":
        args["check_data"]["PROPOSED_DELIVERY"]["response"]["answer_text"] += " New claim."
    elif fault == "changed_current_claim":
        current["text"] += " Different text."
    elif fault == "duplicate_claim":
        args["check_data"]["CLAIMS"].append(deepcopy(current))
    elif fault == "changed_binding":
        binding["citations"][0]["evidence_id"] = "ev_999"
    elif fault == "missing_allowed_fragment":
        binding["citations"][0]["allowed_fragment_ids"] = []
    elif fault == "changed_unit_range":
        args["check_data"]["COMPACT_CLAIM_UNITS"][-1]["units"][0]["end"] -= 1
    elif fault == "missing_units":
        args["check_data"].pop("COMPACT_CLAIM_UNITS")
    result = route_semantic_negatives(normalized, **args)
    assert result["route"] == "contract_correction"
    assert not result.get("deferred_citation_basis_issues")


def test_routing_keeps_every_input_and_raw_model_basis_unchanged():
    normalized, args, _ = capture()
    before = deepcopy((normalized, args))
    result = route_semantic_negatives(normalized, **args)
    assert result["route"] == "semantic_repair"
    assert (normalized, args) == before
    assert result["judgment_changed"] is False
    assert result["cross_revision_state"] is False
    assert result["independent_semantic_evaluation"] is False
    assert result["human_rating"] is None


@pytest.mark.parametrize("identity", [None, "", 1, [], {}])
def test_invalid_named_issue_identity_stays_in_the_original_contract_path(identity):
    normalized, args, _ = capture()
    args["contract_issues"][0]["claim_id"] = identity
    result = route_semantic_negatives(normalized, **args)
    assert result["route"] == "contract_correction"
    assert not result.get("deferred_citation_basis_issues")


def test_two_protected_scientific_clauses_remain_exact_after_the_local_patch():
    second = "Carbon dioxide supplies carbon for sugar. [ev_001]"
    out, adapter = run(
        [
            answer(FACT + " " + second + " " + LIMIT + " [ev_001]"),
            limited_check,
            patch,
            limited_check,
        ]
    )
    assert out.succeeded, out.error
    assert out.response["answer_text"] == FACT + " " + second + " " + LIMIT
    assert out.response["answer_text"].count(FACT) == out.response["answer_text"].count(second) == 1
    repair = json.loads(adapter.calls[2][0][-1]["content"].split("REPAIR_DATA_JSON:\n")[-1])
    assert [row["text"] for row in repair["protected_exact_claims"]] == [FACT, second]


@pytest.mark.parametrize("basis", ["problem_input", "general_knowledge"])
def test_valid_other_union_bases_with_actual_citations_are_not_limitation_repair(basis):
    from generation.reliability_v6 import CompactJointCheckV6

    normalized, args, _ = capture()
    raw = next(
        row for row in args["raw_compact"]["claims"] if row["basis"] == "evidence_limitation"
    )
    cid = raw["claim_id"]
    units = next(
        row["units"] for row in args["check_data"]["COMPACT_CLAIM_UNITS"] if row["claim_id"] == cid
    )
    raw.update(
        basis=basis,
        status="supported",
        units=[
            {
                "unit_id": unit["unit_id"],
                "status": "supported",
                "relation_preserved": True,
                "conditions_preserved": True,
                "reason": "Authored valid alternative union.",
            }
            for unit in units
        ],
    )
    if basis == "problem_input":
        raw["problem_quote_ref"] = "P01:Q01"
    norm = next(row for row in normalized["claims"] if row["claim_id"] == cid)
    norm.update(basis=basis, factual=True)
    CompactJointCheckV6.model_validate(args["raw_compact"])
    result = route_semantic_negatives(normalized, **args)
    assert result["route"] == "contract_correction"
    assert not result.get("deferred_citation_basis_issues")


def test_plain_uncited_limitation_uses_ordinary_validation_without_new_obligation():
    out, _ = run([answer(FACT + " " + LIMIT), limited_check], calls=2)
    assert out.succeeded, out.error
    routing = out.checks[0]["semantic_negative_routing"]
    assert routing["route"] == "ordinary_validation"
    assert not routing.get("deferred_citation_basis_issues")
    assert out.budget["consumed_calls"] == 2


@pytest.mark.parametrize(
    "policy", ["typed_joint_v5", "scoped_compact_v6", "scoped_compact_v7", "scoped_compact_v8"]
)
def test_old_policies_never_receive_v9_generation_appendix(policy):
    from test_answer_core_v5 import checker

    out, adapter = run(
        [answer(), checker if policy == "typed_joint_v5" else check], policy=policy, calls=2
    )
    assert out.succeeded, out.error
    assert not any(
        "SCOPED COMPACT V9" in row["content"] for messages, _ in adapter.calls for row in messages
    )


def test_candidate_operator_enum_accepts_v9_without_changing_default_or_combinations():
    path = Path(__file__).resolve().parents[2] / "backend/app/core/config.py"
    spec = importlib.util.spec_from_file_location("private_v9_config_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.Settings(_env_file=None).chat_joint_checker_policy == "typed_joint_v5"
    assert (
        module.Settings(
            _env_file=None, chat_joint_checker_policy=CHECKER_POLICY
        ).chat_joint_checker_policy
        == CHECKER_POLICY
    )
    with pytest.raises(ValueError):
        module.Settings(
            _env_file=None,
            chat_joint_checker_policy=CHECKER_POLICY,
            chat_source_relation_policy="source_relation_contract_v1",
        )
