"""Guarded current hint action and frozen historical behavior."""

from generation import teaching_plan_v3, teaching_plan_v4, teaching_plan_v5
from test_answer_core_v5 import checker, req, run
from test_enhancement_generation import answer
from test_teaching_plan_v4 import REPEATED_ATTEMPTS


def test_current_repeated_attempt_uses_guarded_pre_generation_action():
    frozen = teaching_plan_v5.freeze_generation_policy()
    plan = teaching_plan_v5.build_teaching_plan(
        "I think the membrane moves.", REPEATED_ATTEMPTS, policy=frozen
    )
    assert plan["version"] == "progress_action_plan_v5"
    assert plan["policy_flags"] == frozen
    assert plan["action"] == "assess_then_guarded_small_step"
    assert plan["repeated_difficulty"] is True
    assert plan["allowed_disclosure"]["help_level"] == 1
    assert "current learner attempt first" in plan["action_instruction"]
    assert "Do not state, quote, paraphrase or list" in plan["action_instruction"]
    assert "visible citations" in plan["action_instruction"]
    assert "never truncate or alter the source" in plan["action_instruction"]
    assert plan["mastery_inference"] is None


def test_prior_v3_and_v4_action_and_default_direct_answer_are_preserved():
    assert (
        teaching_plan_v3.build_teaching_plan("I think the membrane moves.", REPEATED_ATTEMPTS)[
            "action"
        ]
        == "assess_then_adapt"
    )
    assert (
        teaching_plan_v4.build_teaching_plan("I think the membrane moves.", REPEATED_ATTEMPTS)[
            "action"
        ]
        == "assess_then_reduce_step"
    )
    direct = teaching_plan_v5.build_teaching_plan("Explain osmosis.", None)
    assert direct["action"] == "complete_explanation"
    assert direct["allowed_disclosure"]["complete_answer_allowed"] is True
    assert teaching_plan_v5.freeze_generation_policy()["coverage_version"] == "context_coverage_v3"


def test_current_v5_policy_reaches_checked_generation_without_changing_coverage():
    output = run(
        [answer(), checker],
        req(generation_policy=teaching_plan_v5.freeze_generation_policy()),
    )
    assert output.succeeded, output.error
    assert output.token_budget["progress_plan"]["version"] == "progress_action_plan_v5"
    assert output.token_budget["context_coverage"]["version"] == "context_coverage_v3"
    assert output.checks[0]["accepted"] is True
