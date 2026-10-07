"""Shared source-bound selection inputs across generation, check and repair."""

from copy import deepcopy
import hashlib
import json

import pytest

from generation import GenerationService, RequestBudget
from generation.reliability_v3 import repair_plan
from generation.teaching_plan_v10 import scope_repair_plan
from test_enhancement_generation import Script
from test_h1_selection_scaffold_contract import g01_without_supplied_option
from test_hint_task_alignment_v10 import generated_context
from test_teaching_plan_v9 import CASES, data, hint, judgment
from test_teaching_plan_v10 import request as gas_request


def annotate(value, presence):
    value = deepcopy(value)
    goal = value.teaching_context["practice_context"]["current_step_prompt"]
    refs = []
    if presence == "supplied":
        source = value.evidence[0]
        text = source["text"]
        quote = "P1 * V1 = P2 * V2"
        start = text.index(quote)
        refs.append(
            {
                "origin": "evidence",
                "chunk_id": source["chunk_id"],
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "start": start,
                "end": start + len(quote),
                "exact_quote": quote,
            }
        )
    value.teaching_context["practice_context"]["selection_task"] = {
        "version": "selection_task_v1",
        "current_step": value.teaching_context["current_step"],
        "task_ref": {
            "field": "recorded_step_goal.operation",
            "start": 0,
            "end": len(goal),
            "exact_quote": goal,
        },
        "candidate_presence": presence,
        "candidate_refs": refs,
    }
    value.teaching_context["practice_context"]["selection_candidates"] = {
        "version": "selection_candidates_v1",
        "current_step": value.teaching_context["current_step"],
        "task_ref": deepcopy(
            value.teaching_context["practice_context"]["selection_task"]["task_ref"]
        ),
        "candidate_refs": deepcopy(refs),
    }
    return value


def bound_patch(feedback, target_id, replacement_text):
    plan = feedback["bound_repair_plan"]
    return {
        "version": "bound_claim_patch_v1",
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
        "edits": [{"target_id": target_id, "replacement_text": replacement_text}],
    }


def test_bound_supplied_option_is_identical_in_generator_checker_and_report():
    original = annotate(gas_request(), "supplied")
    draft = hint(
        "Comparing the given constant temperature and fixed amount with prerequisites helps decide justified use before applying anything.",
        "Does the supplied candidate fit those conditions, what supports your judgment, and why check first?",
    )
    script = Script([draft, judgment(CASES[0])])
    out = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=4)
    )
    assert out.succeeded, out.error
    generated = generated_context(script.calls[0][0])
    checked = data(script.calls[1][0])
    bound = generated["SELECTION_TASK_CONTRACT"]
    assert (
        bound == checked["SELECTION_TASK_CONTRACT"] == out.token_budget["selection_task_contract"]
    )
    assert bound == generated["TEACHING_ACTION_PLAN"]["selection_task_contract"]
    assert bound["candidate_presence"] == "supplied"
    assert bound["candidate_refs"][0]["exact_quote"] == "P1 * V1 = P2 * V2"
    assert bound["display_policy"]["candidate_expression_allowed"] is False
    assert "P1 * V1 = P2 * V2" not in out.response["answer_text"]


@pytest.mark.parametrize("presence", ["supplied", "absent"])
def test_unmapped_opposite_branch_failure_preserves_failed_gates_and_stops_before_repair(presence):
    original = annotate(
        gas_request() if presence == "supplied" else g01_without_supplied_option(), presence
    )
    case = CASES[0]
    first = hint(
        "Use the given structure.", "Which part must you consider before applying anything?"
    )

    def rejected(messages):
        result = judgment(case)(messages)
        result.update(
            specific_help=False,
            tutor_question_ok=False,
            non_repetitive_next_action=False,
            reason="The proposed action follows the opposite selection branch.",
        )
        return result

    script = Script([first, rejected])
    out = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=4)
    )
    assert not out.succeeded and out.response is None
    assert out.error["code"] == "BOUND_REPAIR_UNMAPPABLE"
    gen = generated_context(script.calls[0][0])["SELECTION_TASK_CONTRACT"]
    assert data(script.calls[1][0])["SELECTION_TASK_CONTRACT"] == gen
    assert out.token_budget["selection_task_contract"] == gen
    assert [v["stage"] for v in out.attempts] == ["generation", "joint_check"]
    assert out.budget["consumed_calls"] == len(script.calls) == 2
    assert [v["accepted"] for v in out.checks] == [False]
    for gate in ("specific_help", "tutor_question_ok", "non_repetitive_next_action"):
        assert out.checks[0]["judgment"][gate] is False
    assert "specific_help" in [action["code"] for action in out.checks[0]["repair_plan"]["actions"]]


@pytest.mark.parametrize("presence", ["supplied", "absent"])
def test_locatable_question_failure_repairs_with_same_contract_and_fresh_check(presence):
    original = annotate(
        gas_request() if presence == "supplied" else g01_without_supplied_option(), presence
    )
    case = CASES[0]
    first = hint(
        "Use the given structure.", "Which part must you consider before applying anything?"
    )
    final_question = (
        "Does the proposed treatment fit the whole structure, what is its basis, "
        "and why check the ordering before use?"
    )

    def rejected(messages):
        value = judgment(case)(messages)
        value.update(
            tutor_question_ok=False,
            non_repetitive_next_action=False,
            reason="The visible question needs a current-step fit judgment and reason.",
        )
        assert value["specific_help"] is True
        return value

    def patch(messages):
        feedback = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        target = next(
            row
            for row in feedback["bound_repair_plan"]["targets"]
            if row["original_text"] == first["tutor_question"]["question"]
        )
        return bound_patch(feedback, target["target_id"], final_question)

    script = Script([first, rejected, patch, judgment(case)])
    out = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=4)
    )
    assert out.succeeded, out.error
    gen = generated_context(script.calls[0][0])["SELECTION_TASK_CONTRACT"]
    repaired = generated_context(script.calls[2][0])["SELECTION_TASK_CONTRACT"]
    feedback = json.loads(script.calls[2][0][-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    assert gen == repaired == feedback["SELECTION_TASK_CONTRACT"]
    assert feedback["selection_binding_sha256"] == gen["binding_sha256"]
    assert all(data(script.calls[i][0])["SELECTION_TASK_CONTRACT"] == gen for i in [1, 3])
    assert [v["stage"] for v in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.budget["consumed_calls"] == 4
    assert [v["accepted"] for v in out.checks] == [False, True]
    assert out.checks[0]["judgment"]["specific_help"] is True
    assert out.response["answer_text"] == "Use the given structure. " + final_question
    assert out.drafts[1]["tutor_question"]["question"] == final_question
    assert out.drafts[1]["precheck_transformations"][0]["requires_full_check"] is True


def test_stale_source_annotation_fails_before_any_provider_invocation():
    original = annotate(gas_request(), "supplied")
    for key in ("selection_task", "selection_candidates"):
        original.teaching_context["practice_context"][key]["candidate_refs"][0]["text_sha256"] = (
            "0" * 64
        )
    script = Script([])
    out = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=4)
    )
    assert not out.succeeded and out.response is None
    assert script.calls == [] and out.budget["consumed_calls"] == 0
    assert out.error["details"]["validation_code"] == "SELECTION_TASK_SOURCE_HASH_MISMATCH"


def test_source_supported_candidate_expression_still_cannot_be_displayed():
    original = annotate(gas_request(), "supplied")
    script = Script([hint("Use P1 * V1 = P2 * V2.", "Does it fit?"), judgment(CASES[0])])
    out = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=2)
    )
    assert not out.succeeded and out.response is None
    assert (
        "HINT_SELECTION_EXPRESSION_DISCLOSED"
        in out.checks[0]["hint_progression_support"]["issue_codes"]
    )
    assert out.budget["consumed_calls"] == 2


def complete_hint_judgment():
    """Canonical normalized shape for a complete hint with a withheld solution."""
    return {
        "claims": [],
        "body_ok": True,
        "specific_help": True,
        "scope_ok": True,
        "suggestions_ok": True,
        "evidence_display_ok": True,
        "cumulative_ok": True,
        "attempt_evaluation_ok": True,
        "tutor_question_ok": True,
        "non_repetitive_next_action": True,
        "complete_answer": False,
        "coverage": "full",
        "missing_facets": [],
        "requirements": [
            {
                "requirement_id": "requirement_current_step",
                "relevance": "related",
                "sufficiency": "sufficient",
                "evidence": [],
                "conditions_preserved": True,
                "response_coverage": "deferred_for_hint",
                "missing_information": "",
                "reason": "The current hint asks for the learner judgment; the full solution is deferred.",
            }
        ],
    }


def quote_repair(value, *, teaching_mode="hint"):
    original = repair_plan(
        value, [{"code": "CHECK_PROBLEM_QUOTE_MISMATCH", "claim_id": "given_claim"}]
    )
    assert "INCOMPLETE_REQUEST" in [action["code"] for action in original["actions"]]
    return scope_repair_plan(original, teaching_mode=teaching_mode, judgment=value)


def test_complete_current_hint_repairs_only_real_quote_defect_without_completing_solution():
    value = complete_hint_judgment()
    before = deepcopy(value)
    scoped = quote_repair(value)
    assert [action["code"] for action in scoped["actions"]] == ["CHECK_PROBLEM_QUOTE_MISMATCH"]
    assert scoped["actions"][0]["origin"] == "source_coverage"
    assert scoped["actions"][0]["claim_id"] == "given_claim"
    assert scoped["actions"][0]["action"] == "separate_given_formula_and_result"
    assert scoped["remaining_repair_pairs"] == 1
    assert value == before


@pytest.mark.parametrize(
    "gate",
    [
        "body_ok",
        "specific_help",
        "scope_ok",
        "suggestions_ok",
        "evidence_display_ok",
        "cumulative_ok",
        "attempt_evaluation_ok",
        "tutor_question_ok",
        "non_repetitive_next_action",
    ],
)
def test_a_failed_current_help_gate_retains_the_completion_repair(gate):
    value = complete_hint_judgment()
    value[gate] = False
    scoped = quote_repair(value)
    assert "INCOMPLETE_REQUEST" in [action["code"] for action in scoped["actions"]]
    assert "CHECK_PROBLEM_QUOTE_MISMATCH" in [action["code"] for action in scoped["actions"]]


@pytest.mark.parametrize(
    "gap",
    [
        "partial_coverage",
        "unknown_coverage",
        "missing_facets",
        "partial_requirement",
        "unaddressed_requirement",
        "lost_condition",
        "missing_information",
        "missing_gate",
        "empty_requirements",
        "malformed_requirement",
        "malformed_evidence",
    ],
)
def test_partial_or_unproven_hint_retains_completion_repair(gap):
    value = complete_hint_judgment()
    if gap == "partial_coverage":
        value["coverage"] = "supported_partial"
    elif gap == "unknown_coverage":
        value.pop("coverage")
    elif gap == "missing_facets":
        value["missing_facets"] = ["An uncovered current-step requirement."]
    elif gap == "partial_requirement":
        value["requirements"][0]["sufficiency"] = "partial"
    elif gap == "unaddressed_requirement":
        value["requirements"][0]["response_coverage"] = "not_addressed"
    elif gap == "lost_condition":
        value["requirements"][0]["conditions_preserved"] = False
    elif gap == "missing_information":
        value["requirements"][0]["missing_information"] = (
            "The current hint omits necessary context."
        )
    elif gap == "missing_gate":
        del value["tutor_question_ok"]
    elif gap == "empty_requirements":
        value["requirements"] = []
    elif gap == "malformed_requirement":
        del value["requirements"][0]["conditions_preserved"]
    else:
        value["requirements"][0]["evidence"] = ["Not a canonical requirement evidence row."]
    scoped = quote_repair(value)
    assert "INCOMPLETE_REQUEST" in [action["code"] for action in scoped["actions"]]


def test_direct_answer_and_unknown_judgment_keep_the_original_completion_action():
    value = complete_hint_judgment()
    original = repair_plan(value, [])
    direct = scope_repair_plan(original, teaching_mode="direct", judgment=value)
    assert direct == original
    unknown = scope_repair_plan(original, teaching_mode="hint")
    assert "INCOMPLETE_REQUEST" in [action["code"] for action in unknown["actions"]]


@pytest.mark.parametrize("change_question", [False, True])
def test_complete_hint_quote_repair_preserves_approved_question_and_requires_fresh_check(
    change_question,
):
    original = annotate(gas_request(), "supplied")
    question = "Would the supplied candidate fit these givens, what supports your judgment, and why check first?"
    draft = hint(CASES[0]["given"], question)
    narrower_given = "pressure 100 kPa and volume 2 L."
    assert narrower_given in original.teaching_context["current_problem"]

    def complete_check(messages):
        value = judgment(CASES[0])(messages)
        value["complete_answer"] = False
        for claim, proposed in zip(value["claims"], data(messages)["CLAIMS"]):
            if proposed["text"] == narrower_given:
                claim.update(
                    basis="problem_input", status="supported", problem_quote=narrower_given
                )
        return value

    def wrong_quote(messages):
        value = complete_check(messages)
        for claim in value["claims"]:
            if claim["basis"] == "problem_input":
                claim["problem_quote"] = "A quotation absent from the actual problem input."
        return value

    def patch(messages):
        feedback = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
        if change_question:
            target = next(
                row for row in feedback["protected_exact_claims"] if row["text"] == question
            )
            return bound_patch(feedback, target["claim_id"], "A different proposed question?")
        target = next(
            row
            for row in feedback["bound_repair_plan"]["targets"]
            if row["original_text"] == CASES[0]["given"]
        )
        return bound_patch(feedback, target["target_id"], narrower_given)

    calls = [draft, wrong_quote, patch] + ([] if change_question else [complete_check])
    script = Script(calls)
    out = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=4)
    )
    feedback = json.loads(script.calls[2][0][-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    assert "INCOMPLETE_REQUEST" not in [
        action["code"] for action in feedback["repair_plan"]["actions"]
    ]
    assert "CHECK_PROBLEM_QUOTE_MISMATCH" in [
        action["code"] for action in feedback["repair_plan"]["actions"]
    ]
    assert any(question in row["text"] for row in feedback["protected_exact_claims"])
    if change_question:
        assert not out.succeeded and out.response is None
        assert out.error["code"] == "BOUND_REPAIR_PROTECTED_EDIT"
        assert out.budget["consumed_calls"] == len(script.calls) == 3
    else:
        assert out.succeeded, out.error
        assert out.response["answer_text"] == narrower_given + " " + question
        assert out.budget["consumed_calls"] == len(script.calls) == 4
        assert [row["stage"] for row in out.attempts] == [
            "generation",
            "joint_check",
            "semantic_repair",
            "joint_recheck",
        ]
        assert [row["accepted"] for row in out.checks] == [False, True]
        assert out.checks[1]["judgment"]["claims"][0]["basis"] == "problem_input"
        assert out.checks[1]["judgment"]["claims"][0]["problem_quote"] == narrower_given
        assert out.drafts[1]["tutor_question"]["question"] == question
        assert out.drafts[1]["precheck_transformations"][0]["requires_full_check"] is True
