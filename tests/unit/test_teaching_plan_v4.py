"""Current teaching action and frozen historical-plan regressions."""

from generation import teaching_plan_v2, teaching_plan_v3, teaching_plan_v4
from test_answer_core_v5 import checker, req, run
from test_enhancement_generation import answer


REPEATED_ATTEMPTS = {
    "teaching_mode": "hint",
    "help_level": 1,
    "turn_role": "learner_attempt",
    "current_step": 2,
    "current_problem": "Explain osmosis.",
    "pending_tutor_question": "What moves across the membrane?",
    "attempt_history": [
        {"status": "incorrect", "feedback": "Review the substance that moves."},
        {"status": "partial", "feedback": "Explain the direction of movement."},
    ],
}


def test_repeated_learner_attempt_is_assessed_before_smaller_next_step():
    frozen = teaching_plan_v4.freeze_generation_policy()
    plan = teaching_plan_v4.build_teaching_plan(
        "I think the membrane moves.", REPEATED_ATTEMPTS, policy=frozen
    )
    assert plan["version"] == "progress_action_plan_v4"
    assert plan["policy_flags"] == frozen
    assert plan["repeated_difficulty"] is True
    assert plan["action"] == "assess_then_reduce_step"
    assert plan["action_selection_reason"] == "current_attempt_after_repeated_difficulty"
    assert "First evaluate this learner attempt" in plan["action_instruction"]
    assert "If it resolves the step" in plan["action_instruction"]
    assert "smaller concrete choice" in plan["action_instruction"]
    assert plan["allowed_disclosure"]["help_level"] == 1
    assert plan["mastery_inference"] is None


def test_single_learner_attempt_and_direct_default_keep_existing_actions():
    first = {
        **REPEATED_ATTEMPTS,
        "attempt_history": REPEATED_ATTEMPTS["attempt_history"][:1],
    }
    assert (
        teaching_plan_v4.build_teaching_plan("Water moves.", first)["action"] == "assess_then_adapt"
    )
    direct = teaching_plan_v4.build_teaching_plan("Explain osmosis.", None)
    assert direct["action"] == "complete_explanation"
    assert direct["allowed_disclosure"]["complete_answer_allowed"] is True


def test_frozen_v2_and_v3_policies_retain_historical_action_on_same_context():
    assert (
        teaching_plan_v2.build_teaching_plan("I think the membrane moves.", REPEATED_ATTEMPTS)[
            "action"
        ]
        == "assess_then_adapt"
    )
    assert (
        teaching_plan_v3.build_teaching_plan("I think the membrane moves.", REPEATED_ATTEMPTS)[
            "action"
        ]
        == "assess_then_adapt"
    )
    assert teaching_plan_v3.freeze_generation_policy()["version"] == "generation_controls_v3"
    assert teaching_plan_v4.freeze_generation_policy()["coverage_version"] == "context_coverage_v3"


def test_current_v4_policy_reaches_checked_generation_and_source_display():
    output = run(
        [answer(), checker],
        req(generation_policy=teaching_plan_v4.freeze_generation_policy()),
    )
    assert output.succeeded, output.error
    assert output.token_budget["progress_plan"]["version"] == "progress_action_plan_v4"
    assert output.token_budget["context_coverage"]["version"] == "context_coverage_v3"
    assert output.checks[0]["accepted"] is True
