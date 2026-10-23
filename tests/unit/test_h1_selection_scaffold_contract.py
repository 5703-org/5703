"""Scripted H1 reply and checker contracts; no real teaching quality measured."""

import json

import pytest

from generation import GenerationService, RequestBudget
from test_enhancement_generation import Script
from test_hint_task_alignment_v10 import (
    CASES,
    generated_context,
    hint,
    judgment,
    request,
)


def rejected_choice(case):
    def check(messages):
        value = judgment(case)(messages)
        value["tutor_question_ok"] = False
        return value

    return check


def choice_draft(case):
    value = hint("Use the supplied conditions.", case["useful"])
    value["tutor_question"]["expected_response_kind"] = "choice"
    return value


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_judgment_and_basis_metadata_requires_repair_and_fresh_check(case):
    original = request(case)
    corrected = hint("Use the supplied conditions.", case["useful"])
    script = Script([choice_draft(case), rejected_choice(case), corrected, judgment(case)])
    outcome = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=4)
    )
    assert outcome.succeeded, outcome.error
    assert outcome.response["answer_text"] == corrected["answer_text"]
    assert [row["stage"] for row in outcome.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert outcome.budget["consumed_calls"] == len(script.calls) == 4
    assert [row["accepted"] for row in outcome.checks] == [False, True]
    assert outcome.drafts[0]["tutor_question"]["expected_response_kind"] == "choice"
    assert outcome.drafts[-1]["tutor_question"]["expected_response_kind"] == "explanation"
    first = generated_context(script.calls[0][0])
    repaired = generated_context(script.calls[2][0])
    assert (
        first["PRACTICE_CONTEXT"]
        == repaired["PRACTICE_CONTEXT"]
        == original.teaching_context["practice_context"]
    )
    assert first["TEACHING_ACTION_PLAN"] == repaired["TEACHING_ACTION_PLAN"]
    assert first["TEACHING_ACTION_PLAN"]["recorded_step_goal"]["operation"] == case["goal"]
    assert first["TEACHING_ACTION_PLAN"]["allowed_disclosure"]["complete_answer_allowed"] is False


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_final_missing_checker_field_cannot_create_fifth_call_or_publish(case):
    def incomplete_check(messages):
        value = judgment(case)(messages)
        del value["non_repetitive_next_action"]
        return value

    script = Script(
        [
            choice_draft(case),
            rejected_choice(case),
            hint("Use the supplied conditions.", case["useful"]),
            incomplete_check,
        ]
    )
    outcome = GenerationService(script, checker_adapter=script).generate(
        request(case), RequestBudget(max_calls=4)
    )
    assert not outcome.succeeded and outcome.response is None
    assert outcome.error["code"] == "CHECKER_INCONSISTENT"
    assert outcome.error["details"]["issue_codes"] == ["CHECKER_SCHEMA_INVALID"]
    assert outcome.budget["consumed_calls"] == len(script.calls) == 4
    assert all(row["stage"] != "checker_contract_repair" for row in outcome.attempts)
    issues = outcome.checks[-1]["checker_inconsistencies"]
    assert issues[0]["field_errors"] == [
        {"path": ["non_repetitive_next_action"], "error_type": "missing"}
    ]
    assert not any(row["published"] for row in outcome.drafts)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_safe_generic_condition_question_still_needs_specific_help(case):
    def insufficient(messages):
        value = judgment(case)(messages)
        value["specific_help"] = False
        value["non_repetitive_next_action"] = False
        value["complete_answer"] = False
        return value

    generic = hint(
        "Use the supplied conditions.",
        "Which stated condition tells you whether the supplied candidate is relevant, and why?",
    )
    script = Script([generic, insufficient, generic, insufficient])
    outcome = GenerationService(script, checker_adapter=script).generate(
        request(case), RequestBudget(max_calls=4)
    )
    assert not outcome.succeeded and outcome.response is None
    assert outcome.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert outcome.budget["consumed_calls"] == len(script.calls) == 4
    assert outcome.checks[-1]["typed_judgment_raw_aliases"]["specific_help"] is False
    assert not any(row["published"] for row in outcome.drafts)


@pytest.mark.parametrize("remove_citation", [False, True])
def test_procedural_fit_citation_leak_needs_removal_and_fresh_check(remove_citation):
    from test_teaching_plan_v10 import request as gas_request
    from test_teaching_plan_v9 import CASES as source_cases, judgment as source_judgment

    question = (
        "Using the stated constant temperature and fixed gas amount, does the supplied "
        "candidate fit this setup, what supports your judgment, and why check before use?"
    )
    unsafe = hint("", question)
    unsafe["answer_text"] = question + " [ev_001]"
    unsafe["citations"] = ["ev_001"]
    repaired = hint("", question) if remove_citation else unsafe
    check = source_judgment(source_cases[0])

    def unsafe_display_check(messages):
        value = check(messages)
        value["evidence_display_ok"] = False
        value["reason"] = "The actual citation view reveals the still-unanswered selection."
        return value

    script = Script([unsafe, unsafe_display_check, repaired, check])
    original = gas_request()
    outcome = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=4)
    )
    assert outcome.succeeded is remove_citation, outcome.error
    assert outcome.budget["consumed_calls"] == len(script.calls) == 4
    assert [row["stage"] for row in outcome.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert outcome.checks[0]["judgment"]["evidence_display_ok"] is False
    feedback = json.loads(script.calls[2][0][-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    boundary = feedback["teaching_repair_boundary"]
    assert "evidence_display_ok" in boundary["failed_global_gate_names"]
    assert boundary["release_source_supported_claims_for_repair"] is True
    assert boundary["final_full_check_required"] is True
    assert feedback["protected_exact_claims"] == []
    first_issues = outcome.checks[0]["structural_issues"]
    assert any(
        row["code"] == "HINT_SELECTION_EXPRESSION_DISCLOSED"
        and row.get("surface_id", "").startswith("citation:")
        for row in first_issues
    )
    if remove_citation:
        assert outcome.response["citations"] == []
        assert "[ev_001]" not in outcome.response["answer_text"]
        assert outcome.delivered_projection["citation_views"] == []
        assert outcome.checks[-1]["accepted"] is True
    else:
        assert outcome.response is None
        assert not any(row["published"] for row in outcome.drafts)


def test_unsafe_procedural_citation_cannot_publish_without_fresh_check_budget():
    from test_teaching_plan_v10 import request as gas_request
    from test_teaching_plan_v9 import CASES as source_cases, judgment as source_judgment

    question = "Does the supplied candidate fit the stated conditions, and why?"
    unsafe = hint("", question)
    unsafe["answer_text"] = question + " [ev_001]"
    unsafe["citations"] = ["ev_001"]
    script = Script([unsafe, source_judgment(source_cases[0])])
    outcome = GenerationService(script, checker_adapter=script).generate(
        gas_request(), RequestBudget(max_calls=2)
    )
    assert outcome.response is None and not outcome.succeeded
    assert outcome.budget["consumed_calls"] == len(script.calls) == 2
    assert not any(row["published"] for row in outcome.drafts)


G01_NO_SUPPLIED_OPTION = {
    "id": "g01_no_supplied_inverse_option",
    "problem": (
        "Solve the equation 5x - 4 = 21. For now, choose the first inverse step "
        "without carrying it out."
    ),
    "step": 1,
    "goal": (
        "Choose the first inverse operation that starts isolating x before "
        "transforming either side."
    ),
    "source": (
        "An equality remains valid when the same permissible operation is applied to both sides."
    ),
    "given": "Solve the equation 5x - 4 = 21.",
    "conditions": [
        "5x - 4 = 21",
        "The objective is to isolate x using equality-preserving inverse operations.",
    ],
    "useful": (
        "If you treated the complete left side as only a multiple of x, what part "
        "would that miss, and why does the whole structure matter before choosing "
        "the order of your first step?"
    ),
}


def g01_without_supplied_option():
    value = request(G01_NO_SUPPLIED_OPTION)
    value.question = "Help me with the current practice step without giving the answer."
    value.teaching_context["practice_context"]["concepts"] = [
        "equality-preserving inverse operations"
    ]
    return value


def no_supplied_option_check(messages):
    value = judgment(G01_NO_SUPPLIED_OPTION)(messages)
    from test_teaching_plan_v9 import data

    actual = data(messages)
    assert actual["TEACHING_ACTION_PLAN"]["original_problem"] == G01_NO_SUPPLIED_OPTION["problem"]
    assert actual["PRACTICE_CONTEXT"]["conditions"] == G01_NO_SUPPLIED_OPTION["conditions"]
    value["specific_help"] = False
    value["non_repetitive_next_action"] = False
    value["scope_ok"] = False
    value["tutor_question_ok"] = False
    value["complete_answer"] = False
    value["reason"] = (
        "The question pretends an inverse-operation option was supplied, but none was."
    )
    return value


@pytest.mark.parametrize("still_invents_option", [False, True])
def test_absent_supplied_option_repairs_to_whole_structure_and_fresh_check(
    still_invents_option,
):
    original = g01_without_supplied_option()
    wrong = hint(
        "Consider the supplied candidate for the first step.",
        "Does that supplied candidate fit the whole left side, and why check before transforming?",
    )
    corrected = hint("Look at the complete left side.", G01_NO_SUPPLIED_OPTION["useful"])
    script = Script(
        [
            wrong,
            no_supplied_option_check,
            wrong if still_invents_option else corrected,
            no_supplied_option_check if still_invents_option else judgment(G01_NO_SUPPLIED_OPTION),
        ]
    )
    outcome = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=4)
    )
    assert outcome.succeeded is (not still_invents_option), outcome.error
    assert outcome.budget["consumed_calls"] == len(script.calls) == 4
    assert [row["stage"] for row in outcome.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    first = generated_context(script.calls[0][0])
    repaired = generated_context(script.calls[2][0])
    assert (
        first["PRACTICE_CONTEXT"]
        == repaired["PRACTICE_CONTEXT"]
        == original.teaching_context["practice_context"]
    )
    assert first["TEACHING_ACTION_PLAN"] == repaired["TEACHING_ACTION_PLAN"]
    assert first["TEACHING_ACTION_PLAN"]["original_problem"] == G01_NO_SUPPLIED_OPTION["problem"]
    assert (
        first["TEACHING_ACTION_PLAN"]["recorded_step_goal"]["operation"]
        == G01_NO_SUPPLIED_OPTION["goal"]
    )
    assert original.evidence[0]["text"] == G01_NO_SUPPLIED_OPTION["source"]
    feedback = json.loads(script.calls[2][0][-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    boundary = feedback["teaching_repair_boundary"]
    assert {
        "specific_help",
        "non_repetitive_next_action",
        "scope_ok",
        "tutor_question_ok",
    } <= set(boundary["failed_global_gate_names"])
    assert boundary["release_source_supported_claims_for_repair"] is True
    assert boundary["final_full_check_required"] is True
    if still_invents_option:
        assert outcome.response is None
        assert not any(row["published"] for row in outcome.drafts)
    else:
        assert outcome.response["answer_text"] == corrected["answer_text"]
        assert outcome.response["citations"] == []
        assert outcome.checks[-1]["accepted"] is True
        assert outcome.drafts[-1]["tutor_question"]["expected_response_kind"] == "explanation"


def test_absent_supplied_option_without_repair_and_fresh_check_budget_cannot_publish():
    original = g01_without_supplied_option()
    wrong = hint("Consider the supplied candidate.", "Does that supplied candidate fit, and why?")
    script = Script([wrong, no_supplied_option_check])
    outcome = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=2)
    )
    assert outcome.response is None and not outcome.succeeded
    assert outcome.budget["consumed_calls"] == len(script.calls) == 2
    assert outcome.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert [row["stage"] for row in outcome.attempts] == ["generation", "joint_check"]
    assert not any(row["published"] for row in outcome.drafts)


S11_TASK_LINKED_OPTION = {
    "id": "s11_option_in_current_evidence",
    "problem": (
        "An ideal gas initially has pressure 100 kPa and volume 2 L. Its volume "
        "changes to 4 L at constant temperature and fixed amount of gas."
    ),
    "step": 1,
    "goal": "Choose the supplied pressure-volume relation before substituting values.",
    "source": "For a fixed amount of ideal gas at constant temperature, P1 * V1 = P2 * V2.",
    "given": "Its volume changes to 4 L at constant temperature and fixed amount of gas.",
    "conditions": [
        "The amount of gas is fixed.",
        "The temperature remains constant.",
        "The initial pressure is 100 kPa and the initial volume is 2 L.",
        "The final volume is 4 L.",
    ],
    "useful": (
        "Does the supplied candidate fit these given conditions, what connection "
        "supports your judgment, and why check its fit before substituting values?"
    ),
}


@pytest.mark.parametrize("still_uses_generic_hypothesis", [False, True])
def test_task_linked_evidence_option_requires_actual_fit_and_fresh_check(
    still_uses_generic_hypothesis,
):
    original = request(S11_TASK_LINKED_OPTION)
    wrong = hint(
        "Consider the whole structure.",
        "What features must a proposed relation account for, and how would you decide it fits?",
    )
    corrected = hint(
        "Its volume changes to 4 L at constant temperature and fixed amount of gas. Comparing "
        "these conditions with prerequisites helps you decide whether using the supplied "
        "candidate would be justified before applying it.",
        S11_TASK_LINKED_OPTION["useful"],
    )
    check = judgment(S11_TASK_LINKED_OPTION)

    def generic_hypothesis_check(messages):
        value = check(messages)
        value["specific_help"] = False
        value["non_repetitive_next_action"] = False
        value["scope_ok"] = False
        value["tutor_question_ok"] = False
        value["complete_answer"] = False
        value["reason"] = (
            "The task-linked candidate is in current evidence; a generic proposed "
            "relation does not ask about that candidate's condition-based fit."
        )
        return value

    script = Script(
        [
            wrong,
            generic_hypothesis_check,
            wrong if still_uses_generic_hypothesis else corrected,
            generic_hypothesis_check if still_uses_generic_hypothesis else check,
        ]
    )
    outcome = GenerationService(script, checker_adapter=script).generate(
        original, RequestBudget(max_calls=4)
    )
    assert outcome.succeeded is (not still_uses_generic_hypothesis), outcome.error
    assert outcome.budget["consumed_calls"] == len(script.calls) == 4
    assert [row["stage"] for row in outcome.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    first = generated_context(script.calls[0][0])
    repaired = generated_context(script.calls[2][0])
    assert first["TEACHING_ACTION_PLAN"] == repaired["TEACHING_ACTION_PLAN"]
    assert first["PRACTICE_CONTEXT"] == repaired["PRACTICE_CONTEXT"]
    assert first["PRACTICE_CONTEXT"]["conditions"] == S11_TASK_LINKED_OPTION["conditions"]
    assert original.evidence[0]["text"] == S11_TASK_LINKED_OPTION["source"]
    assert (
        first["TEACHING_ACTION_PLAN"]["recorded_step_goal"]["operation"]
        == S11_TASK_LINKED_OPTION["goal"]
    )
    feedback = json.loads(script.calls[2][0][-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    assert feedback["teaching_repair_boundary"]["final_full_check_required"] is True
    if still_uses_generic_hypothesis:
        assert outcome.response is None
        assert not any(row["published"] for row in outcome.drafts)
    else:
        assert outcome.response["answer_text"] == corrected["answer_text"]
        assert outcome.response["citations"] == []
        assert outcome.checks[-1]["accepted"] is True
