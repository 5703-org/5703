"""Public saved-output permissions replay; no model-quality approval is fabricated."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from generation import GenerationRequest, GenerationService, ModelConfig, RequestBudget
from generation.parser import ResponseValidationError
from generation.reliability_v3 import given_matches, numerical_values
from generation.reliability_v4 import unchanged_claims
from generation.repair_patch_v1 import (
    VERSION,
    build_bound_repair_plan,
    compile_bound_repair_patch,
    scope_current_hint_question_protection,
)
from test_enhancement_generation import Script

FIXTURE = Path(__file__).parents[1] / "fixtures/structured_repair/g01_current_native_20261006.json"


def saved_case():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def scope(case):
    return scope_current_hint_question_protection(
        case["draft"], case["claims"], case["protected"], case["repair_plan"], case["judgment"]
    )


def build(case, protected):
    return build_bound_repair_plan(
        case["draft"],
        case["claims"],
        protected,
        case["repair_plan"],
        request_binding=case["request_binding"],
        selection_contract=case["selection_contract"],
        projection=case["projection"],
    )


def patch(plan):
    replacements = {
        "claim_c82c5c03949b739723edc7e3_1": "The equation is 5x - 4 = 21.",
        "claim_66c09bb66ae72aec59684436_2": (
            "Suppose, as a neutral hypothesis, that a visible local component is handled "
            "before considering the whole expression."
        ),
        "claim_d14357d732d75bbd63d75ab2_1": (
            "Would that treatment fit the equation's whole structure and the order of steps, "
            "what visible feature supports your judgment, and why check this before "
            "deciding on a first step?"
        ),
    }
    return {
        "version": VERSION,
        **{
            key: plan[key]
            for key in (
                "plan_sha256",
                "base_sha256",
                "request_sha256",
                "selection_sha256",
                "projection_sha256",
            )
        },
        "edits": [
            {"target_id": row["target_id"], "replacement_text": replacements[row["target_id"]]}
            for row in plan["targets"]
        ],
    }


def compile_patch(case, protected, plan, proposal):
    return compile_bound_repair_patch(
        case["draft"],
        case["claims"],
        protected,
        proposal,
        case["evidence_ids"],
        plan=plan,
        repair_plan=case["repair_plan"],
        request_binding=case["request_binding"],
        selection_contract=case["selection_contract"],
        projection=case["projection"],
    )


def test_saved_failure_and_original_protection_conflict_remain_recorded():
    case = saved_case()
    assert case["saved_error"]["code"] == "BOUND_REPAIR_UNMAPPABLE"
    assert case["saved_checker_accepted"] is False
    assert case["saved_native_published"] is False
    assert case["human_rating"] is None
    with pytest.raises(ResponseValidationError, match="crosses protected claim bounds"):
        build(case, case["protected"])


def test_explicit_hint_defect_releases_only_supported_nonfactual_exact_question_claims():
    case = saved_case()
    before = deepcopy(case)
    protected, receipt = scope(case)
    assert receipt["released_claim_ids"] == [
        "claim_66c09bb66ae72aec59684436_2",
        "claim_d14357d732d75bbd63d75ab2_1",
    ]
    assert (receipt["visible_start"], receipt["visible_end"]) == (463, 802)
    assert receipt["requires_full_check"] is True
    assert receipt["publication_override"] is False
    assert len(protected) == 3
    assert case == before
    plan = build(case, protected)
    assert len(plan["targets"]) == 3
    assert all(
        row["claim_id"] not in {t["target_id"] for t in plan["targets"]} for row in protected
    )


def test_splice_preserves_every_byte_outside_declared_targets_and_syncs_question():
    case = saved_case()
    before = deepcopy(case)
    protected, _ = scope(case)
    plan = build(case, protected)
    proposal = patch(plan)
    compiled, receipt = compile_patch(case, protected, plan, proposal)
    replacement = {row["target_id"]: row["replacement_text"] for row in proposal["edits"]}
    original = case["draft"]["answer_text"]
    expected, cursor, compiled_cursor = [], 0, 0
    for target in sorted(plan["targets"], key=lambda row: row["start"]):
        unchanged = original[cursor : target["start"]]
        assert compiled["answer_text"][compiled_cursor : compiled_cursor + len(unchanged)].encode(
            "utf-8"
        ) == unchanged.encode("utf-8")
        expected.extend((unchanged, replacement[target["target_id"]]))
        compiled_cursor += len(unchanged) + len(replacement[target["target_id"]])
        cursor = target["end"]
    expected.append(original[cursor:])
    assert compiled["answer_text"].encode("utf-8") == "".join(expected).encode("utf-8")
    assert unchanged_claims(protected, compiled)
    assert compiled["tutor_question"]["question"] in compiled["answer_text"]
    assert compiled["tutor_question"]["expected_response_kind"] == "explanation"
    for key in set(case["draft"]) - {"answer_text", "tutor_question"}:
        assert compiled[key] == case["draft"][key]
    assert receipt["requires_full_check"] is True
    assert receipt["source_entailment_certified"] is False
    assert receipt["publication_override"] is False
    assert case == before


@pytest.mark.parametrize("mutation", ["factual", "wrong_basis", "partial", "missing", "duplicate"])
def test_protected_question_requires_unique_explicit_supported_nonfactual_classification(mutation):
    case = saved_case()
    verdict = case["judgment"]["claims"][-1]
    if mutation == "factual":
        verdict.update(factual=True, basis="problem_input")
    elif mutation == "wrong_basis":
        verdict["basis"] = "evidence_limitation"
    elif mutation == "partial":
        verdict["status"] = "partial"
    elif mutation == "missing":
        case["judgment"]["claims"].pop()
    else:
        case["judgment"]["claims"].append(deepcopy(verdict))
    with pytest.raises(ResponseValidationError):
        scope(case)


def test_partially_intersecting_question_claim_is_never_released():
    case = saved_case()
    crossing = case["claims"][-2]
    crossing["start"] = 461
    crossing["text"] = case["draft"]["answer_text"][461 : crossing["end"]]
    case["protected"][-2] = deepcopy(crossing)
    with pytest.raises(ResponseValidationError, match="crosses protected claim bounds"):
        scope(case)


def test_ambiguous_visible_question_never_releases_protection():
    case = saved_case()
    case["draft"]["answer_text"] += "\n\n" + case["draft"]["tutor_question"]["question"]
    with pytest.raises(ResponseValidationError) as caught:
        scope(case)
    assert caught.value.code == "BOUND_REPAIR_METADATA_AMBIGUOUS"


@pytest.mark.parametrize(
    "mutation",
    [
        "absent",
        "different_action",
        "different_scope",
        "different_origin",
        "different_version",
        "not_incomplete",
    ],
)
def test_other_actions_and_nondefective_current_help_cannot_release_protection(mutation):
    case = saved_case()
    action = case["repair_plan"]["actions"][-1]
    if mutation == "absent":
        case["repair_plan"]["actions"].pop()
    elif mutation == "different_action":
        action["action"] = "restore_current_operation_with_useful_non_repetitive_learner_action"
    elif mutation == "different_scope":
        action["response_scope"] = "whole_answer"
    elif mutation == "different_origin":
        action["origin"] = "model_proposal"
    elif mutation == "different_version":
        case["repair_plan"]["version"] = "cause_specific_step_hint_repair_v9"
    else:
        case["judgment"]["complete_answer"] = True
    protected, receipt = scope(case)
    assert protected == case["protected"]
    assert receipt["released_claim_ids"] == []


def test_other_supported_nonfactual_protected_claims_stay_immutable():
    case = saved_case()
    protected, _ = scope(case)
    plan = build(case, protected)
    proposal = patch(plan)
    proposal["edits"][0]["target_id"] = protected[0]["claim_id"]
    with pytest.raises(ResponseValidationError) as caught:
        compile_patch(case, protected, plan, proposal)
    assert caught.value.code == "BOUND_REPAIR_PROTECTED_EDIT"


def test_existing_exact_quote_and_domain_number_guards_are_unchanged():
    case = saved_case()
    claim = case["claims"][0]["text"]
    quote = case["judgment"]["claims"][0]["problem_quote"]
    problem = case["native_request"]["teaching_context"]["current_problem"]
    assert quote in problem
    assert 2 in numerical_values(claim) and 2 not in numerical_values(quote)
    assert not given_matches(claim, quote, [problem])
    assert given_matches("The equation is 5x - 4 = 21.", quote, [problem])
    assert not given_matches("There are two litres of gas.", "There is gas.", ["There is gas."])
    s11 = json.loads(
        FIXTURE.with_name("s11_current_native_quote_20261006.json").read_text(encoding="utf-8")
    )
    assert s11["problem_quote"] not in s11["question"]
    assert s11["problem_quote"] not in s11["current_problem"]
    assert 2 in numerical_values(s11["claim_text"]) and 2 not in numerical_values(
        s11["problem_quote"]
    )
    assert not given_matches(
        s11["claim_text"], s11["problem_quote"], [s11["question"], s11["current_problem"]]
    )
    assert s11["saved_checker_accepted"] is False and s11["saved_native_published"] is False


def test_saved_native_generation_and_check_reach_mandatory_fresh_checker_boundary():
    case = saved_case()
    values = deepcopy(case["native_request"])
    for key in ("config", "checker_config"):
        values[key] = ModelConfig.from_dict(values[key])
    request = GenerationRequest(**values)
    captured = {}

    class FreshCheckerBoundary(BaseException):
        pass

    def proposal(messages):
        feedback = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        captured["feedback"] = feedback
        return patch(feedback["bound_repair_plan"])

    def fresh_checker(messages):
        captured["fresh"] = json.loads(messages[-1]["content"])
        raise FreshCheckerBoundary()

    script = Script(
        [
            json.loads(case["raw_generation"]),
            json.loads(case["raw_checker"]),
            proposal,
            fresh_checker,
        ]
    )
    budget = RequestBudget(max_calls=4, max_active_seconds=180)
    events = []
    with pytest.raises(FreshCheckerBoundary):
        GenerationService(script, checker_adapter=script).generate(
            request, budget, on_attempt=events.append
        )
    assert [row["stage"] for row in events if row["phase"] == "start"] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert budget.consumed_calls == len(script.calls) == 4
    assert script.calls[2][1]["response_schema_name"] == "bound_claim_patch_repair_v1"
    assert len(captured["feedback"]["current_hint_question_boundary"]["released_claim_ids"]) == 2
    fresh = captured["fresh"]
    assert fresh["PROPOSED_DELIVERY"]["response"]["answer_text"].startswith(
        "The equation is 5x - 4 = 21."
    )
    assert (
        fresh["TUTOR_QUESTION"]["question"] in fresh["PROPOSED_DELIVERY"]["response"]["answer_text"]
    )
    assert fresh["SELECTION_TASK_CONTRACT"] == case["selection_contract"]
    assert (
        fresh["SOURCE_FRAGMENTS"][0]["exact_text"]
        == "An equality remains valid when the same permissible operation is applied to both sides."
    )
    assert case["saved_checker_accepted"] is False and case["saved_native_published"] is False
