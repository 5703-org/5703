"""Finite H1 task/routing controls; scripted judgments do not measure model quality."""

from copy import deepcopy
import json

import pytest

from generation import GenerationService, RequestBudget, teaching_plan_v9, teaching_plan_v10
from generation.hint_progression_v10 import selection_goal
from test_enhancement_generation import Script
from test_teaching_plan_v9 import data, hint, judgment, request as previous_request


CASES = [
    {
        "id": "algebra_inverse_structure",
        "problem": "Solve 5x - 4 = 21. Choose the first inverse step without carrying it out.",
        "step": 1,
        "goal": "Choose the first inverse operation that starts isolating x before transforming either side.",
        "source": "An equation remains equal when the same operation is applied to both sides. Inverse operations can undo the operations in an expression.",
        "given": "Solve 5x - 4 = 21.",
        "conditions": ["The left side has a scaled variable term and a separate constant term."],
        "useful": "If you treat the whole left side as just a multiple of x, what part would that ignore, and why does it matter before choosing an inverse step?",
        "readback": "What is the coefficient of x and what constant is on the left?",
    },
    {
        "id": "physics_fixed_variable_fit",
        "problem": "A sealed flexible balloon containing a fixed amount of ideal gas warms from 280 K to 320 K while pressure is held at 90 kPa. Initially its volume is 1.2 L.",
        "step": 1,
        "goal": "Choose a supplied gas relation for the volume and temperature change before numerical substitution.",
        "source": "Candidate gas relations have different prerequisites: fixed temperature, fixed pressure, or fixed volume. Compare a candidate's prerequisites with the stated process.",
        "given": "The pressure is held at 90 kPa.",
        "conditions": [
            "The gas amount is fixed.",
            "Pressure is held constant; the flexible balloon's volume may change.",
        ],
        "useful": "Compare a candidate requiring fixed pressure with one requiring fixed volume: which prerequisite does the setup provide, and which candidate would that help rule out?",
        "readback": "Which variable is held at 90 kPa, and what temperatures are given?",
    },
    {
        "id": "chemistry_explicit_mathematical_selection",
        "problem": "The supplied reaction is 2H2 + O2 -> 2H2O. Hydrogen amount is 4 mol and oxygen is in excess. Choose a mole-to-mole conversion before calculation.",
        "step": 1,
        "goal": "Choose a mathematical relation for the mole-to-mole conversion before substitution.",
        "source": "Balanced coefficients count matching reaction batches, not masses in grams. A mole-to-mole conversion must match the supplied reactant and requested reactant.",
        "given": "Hydrogen amount is 4 mol and oxygen is in excess.",
        "conditions": ["The supplied and requested reactant amounts are in moles."],
        "useful": "Would a mass-based comparison or a reaction-batch comparison fit this mole-to-mole request, and what must the units and reactant roles match before you choose a ratio?",
        "readback": "How many moles of hydrogen are supplied, and which gas is in excess?",
    },
]


def request(case=CASES[0], *, arm="D", **context_changes):
    value = previous_request(case)
    value.generation_policy = teaching_plan_v10.freeze_generation_policy(arm)
    value.teaching_context["practice_context"]["conditions"] = list(case["conditions"])
    value.teaching_context.update(context_changes)
    return value


def plan(value):
    return teaching_plan_v10.build_teaching_plan(
        value.question,
        value.teaching_context,
        value.understanding,
        policy=value.generation_policy,
        answer_mode=value.answer_mode,
    )


def generated_context(messages):
    return next(
        json.loads(row["content"].removeprefix("CONTEXT_DATA_JSON:\n"))
        for row in messages
        if row["content"].startswith("CONTEXT_DATA_JSON:\n")
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
@pytest.mark.parametrize("arm", ["B", "D"])
def test_h1_task_references_the_owned_operation_and_conditions_without_solving(case, arm):
    value = request(case, arm=arm)
    before = deepcopy(value.teaching_context)
    result = plan(value)
    assert selection_goal(case["goal"])
    assert result["action"] == "support_recorded_practice_step"
    assert result["hint_task"] == {
        "operation_ref": "recorded_step_goal.operation",
        "conditions_ref": "original_problem/PRACTICE_CONTEXT",
        "task": "judge_candidate_applicability_or_local_structural_fit",
        "reply": "judgment_and_reason",
    }
    assert result["recorded_step_goal"]["operation"] == case["goal"]
    assert result["recorded_step_goal"]["answer_key_used"] is False
    assert result["allowed_disclosure"]["complete_answer_allowed"] is False
    assert result["hint_stage"]["level"] == 1 and result["current_step"] == case["step"]
    assert result["action_instruction"] == teaching_plan_v10.H1_TASK_ACTION
    assert result["next_reply_requirement"] == result["expected_learner_reply"]["instruction"]
    assert result["provider_calls"] == 0 and result["mastery_inference"] is None
    assert value.teaching_context == before


@pytest.mark.parametrize(
    "operation",
    [
        "Choose the current search-interval update that preserves all possible target locations before writing the assignment.",
        "Choose a claim strength supported by the report before rewriting the headline.",
        "Identify the controlled condition needed for this comparison before explaining the results.",
        "Choose a mole-to-mole relation that converts the supplied hydrogen amount to the oxygen needed before calculation.",
        "Choose the relation between pressure and volume.",
    ],
)
def test_nonmatching_goals_are_not_forced_into_the_finite_math_task(operation):
    case = {**CASES[0], "goal": operation}
    assert not selection_goal(operation)
    result = plan(request(case))
    assert "hint_task" not in result
    assert result["action_instruction"] == teaching_plan_v10.STAGE_CUES[1]


@pytest.mark.parametrize("level", [2, 3])
@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_higher_hint_levels_keep_their_stage_and_reply_contract(case, level):
    value = request(case, help_level=level)
    old = teaching_plan_v9.build_teaching_plan(value.question, value.teaching_context)
    result = plan(value)
    assert "hint_task" not in result
    assert result["hint_stage"]["level"] == level
    assert result["action_instruction"] == teaching_plan_v10.STAGE_CUES[level]
    assert result["next_reply_requirement"] == old["next_reply_requirement"]
    assert result["expected_learner_reply"] == old["expected_learner_reply"]
    assert result["current_step"] == case["step"]


@pytest.mark.parametrize("arm", ["A", "C"])
def test_content_planning_off_does_not_add_a_task(arm):
    result = plan(request(arm=arm))
    assert result["policy_flags"]["content_plan"] is False
    assert "hint_task" not in result
    assert result["action_instruction"] == teaching_plan_v10.STAGE_CUES[1]


@pytest.mark.parametrize("level", [0, 1, 2, 3])
def test_full_direct_help_keeps_its_complete_answer_behavior(level):
    result = plan(request(teaching_mode="direct", help_level=level))
    assert result["enabled"] is False
    assert result["allowed_disclosure"]["complete_answer_allowed"] is True
    assert "hint_task" not in result and "hint_stage" not in result


@pytest.mark.parametrize("level", [1, 2])
def test_real_attempt_feedback_keeps_precedence(level):
    value = request(
        turn_role="learner_attempt",
        help_level=level,
        pending_tutor_question="Choose an inverse operation consistent with the expression.",
        attempt_history=[{"status": "partial"}, {"status": "incorrect"}],
    )
    old = teaching_plan_v9.build_teaching_plan(value.question, value.teaching_context)
    result = plan(value)
    assert "hint_task" not in result
    assert result["action"] == old["action"] == "assess_then_guarded_small_step"
    assert result["action_instruction"] == old["action_instruction"]
    assert result["expected_learner_reply"] == old["expected_learner_reply"]
    assert result["hint_stage"]["level"] == level


def test_pending_math_selection_uses_the_narrower_current_question_reference():
    pending = "Choose an inverse operation that can account for the separate constant term."
    value = request(pending_tutor_question=pending)
    result = plan(value)
    assert result["action"] == "support_pending_question"
    assert result["hint_task"]["operation_ref"] == "current_question"
    assert result["current_question"] == pending != result["recorded_step_goal"]["operation"]
    assert result["recorded_step_goal"]["operation"] == CASES[0]["goal"]
    assert result["current_step"] == CASES[0]["step"]


@pytest.mark.parametrize(
    "pending",
    ["What constant is written on the left?", "Choose a claim strength supported by the report."],
)
def test_pending_nonselection_does_not_fall_back_to_the_saved_math_goal(pending):
    result = plan(request(pending_tutor_question=pending))
    assert selection_goal(result["recorded_step_goal"]["operation"])
    assert result["action"] == "support_pending_question" and result["current_question"] == pending
    assert "hint_task" not in result
    assert result["action_instruction"] == teaching_plan_v10.STAGE_CUES[1]


@pytest.mark.parametrize("field", ["operation_ref", "conditions_ref", "task", "reply"])
def test_forged_hint_task_cannot_change_the_owned_reply_contract(field):
    value = request()
    forged = deepcopy(plan(value))
    forged["hint_task"][field] = "forged"
    with pytest.raises(ValueError, match="HINT_PROGRESSION_PLAN_MISMATCH"):
        teaching_plan_v10.validate_plan(
            forged,
            value.question,
            value.teaching_context,
            value.understanding,
            policy=value.generation_policy,
            answer_mode=value.answer_mode,
        )


def test_legacy_v9_does_not_receive_the_v10_task():
    value = request()
    legacy = teaching_plan_v9.build_teaching_plan(value.question, value.teaching_context)
    assert "hint_task" not in legacy
    with pytest.raises(ValueError, match="UNKNOWN_GENERATION_POLICY"):
        teaching_plan_v10.validate_generation_policy(teaching_plan_v9.freeze_generation_policy())


def test_compact_checker_transport_preserves_the_full_plan_and_original_strings():
    value = request()
    payload = {
        "TEACHING_ACTION_PLAN": plan(value),
        "PRACTICE_CONTEXT": value.teaching_context["practice_context"],
        "opaque": "Original Unicode: \u0394\nspacing stays.",
    }
    wire = teaching_plan_v10.serialize_checker_input(payload)
    assert json.loads(wire) == payload
    assert wire == json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    task_wire = teaching_plan_v10.serialize_checker_input(
        payload["TEACHING_ACTION_PLAN"]["hint_task"]
    )
    assert len(task_wire.encode("utf-8")) <= 260


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_same_task_reaches_generation_and_checker_without_review_labels(case):
    value = request(case)
    script = Script([hint("Use the supplied conditions.", case["useful"]), judgment(case)])
    out = GenerationService(script, checker_adapter=script).generate(
        value, RequestBudget(max_calls=2)
    )
    assert out.succeeded, out.error
    generated = generated_context(script.calls[0][0])
    checked = data(script.calls[1][0])
    assert generated["TEACHING_ACTION_PLAN"] == checked["TEACHING_ACTION_PLAN"] == plan(value)
    assert (
        generated["PRACTICE_CONTEXT"]
        == checked["PRACTICE_CONTEXT"]
        == value.teaching_context["practice_context"]
    )
    assert teaching_plan_v10.GENERATION_INSTRUCTION in script.calls[0][0][0]["content"]
    assert teaching_plan_v10.CHECKER_INSTRUCTION in script.calls[1][0][0]["content"]
    assert set(generated["TEACHING_ACTION_PLAN"]["hint_task"]) == {
        "operation_ref",
        "conditions_ref",
        "task",
        "reply",
    }
    assert "expected_label" not in json.dumps(generated) and "variants" not in json.dumps(generated)
    assert out.budget["consumed_calls"] == 2 and out.response["short_answer"] is None


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_existing_false_specific_help_gate_blocks_readback_without_a_new_detector(case):
    def insufficient(messages):
        result = judgment(case)(messages)
        result["specific_help"] = False
        return result

    script = Script([hint("Use the supplied conditions.", case["readback"]), insufficient])
    out = GenerationService(script, checker_adapter=script).generate(
        request(case), RequestBudget(max_calls=2)
    )
    assert not out.succeeded and out.response is None
    assert out.checks[0]["accepted"] is False
    assert out.budget["consumed_calls"] == 2
    assert out.checks[0]["typed_judgment_raw_aliases"]["specific_help"] is False
