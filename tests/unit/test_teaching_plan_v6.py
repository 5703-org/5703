"""Current exact-given hint plan with frozen V5 replay."""

from generation import GenerationService, RequestBudget, teaching_plan_v5, teaching_plan_v6
from generation.adapters import chat_value
from test_answer_core_v5 import checker, req, run
from test_enhancement_generation import Script, answer
from test_teaching_plan_v4 import REPEATED_ATTEMPTS


def test_current_repeated_attempt_adds_exact_given_restraint_without_inferring_target():
    context = dict(REPEATED_ATTEMPTS)
    assert "pending_answer" not in context
    plan = teaching_plan_v6.build_teaching_plan("The membrane moves.", context)
    assert plan["version"] == "progress_action_plan_v6"
    assert plan["action"] == "assess_then_guarded_small_step"
    assert plan["exact_given_guard"] is True
    assert "cardinal count" in plan["action_instruction"]
    assert "inferred count of listed features" in plan["action_instruction"]
    assert "Keep the pending target undisclosed" in plan["action_instruction"]
    assert plan["allowed_disclosure"]["help_level"] == 1
    assert plan["mastery_inference"] is None


def test_frozen_v5_action_and_ordinary_direct_answer_are_unchanged():
    frozen = teaching_plan_v5.build_teaching_plan("The membrane moves.", REPEATED_ATTEMPTS)
    assert frozen["version"] == "progress_action_plan_v5"
    assert frozen["action"] == "assess_then_guarded_small_step"
    assert "cardinal count" not in frozen["action_instruction"]
    direct = teaching_plan_v6.build_teaching_plan("Explain osmosis.", None)
    assert direct["action"] == "complete_explanation"
    assert direct["exact_given_guard"] is False
    assert direct["allowed_disclosure"]["complete_answer_allowed"] is True


def test_current_v6_reaches_checked_generation_with_same_coverage_policy():
    output = run(
        [answer(), checker],
        req(generation_policy=teaching_plan_v6.freeze_generation_policy()),
    )
    assert output.succeeded, output.error
    assert output.token_budget["progress_plan"]["version"] == "progress_action_plan_v6"
    assert output.token_budget["context_coverage"]["version"] == "context_coverage_v3"
    assert output.checks[0]["accepted"] is True


def test_exact_given_restraint_is_in_v6_semantic_repair_only():
    feedback = "That does not address the requested step."
    next_step = "What feature should you locate in the problem?"
    draft = {
        **chat_value("answer", feedback + " " + next_step),
        "tutor_question": {"question": next_step, "expected_response_kind": "concept"},
        "learner_attempt_evaluation": {"status": "incorrect", "feedback": feedback},
    }

    def calls_for(freeze):
        adapter = Script(
            [draft, lambda messages: checker(messages, scope_ok=False), draft, checker]
        )
        GenerationService(adapter).generate(
            req(
                question="The membrane moves.",
                teaching_context=REPEATED_ATTEMPTS,
                generation_policy=freeze(),
            ),
            RequestBudget(max_calls=4),
        )
        return adapter.calls

    current_calls = calls_for(teaching_plan_v6.freeze_generation_policy)
    historical_calls = calls_for(teaching_plan_v5.freeze_generation_policy)
    assert len(current_calls) >= 3 and len(historical_calls) >= 3
    assert teaching_plan_v6.EXACT_GIVEN_INSTRUCTION in current_calls[2][0][-1]["content"]
    assert teaching_plan_v6.EXACT_GIVEN_INSTRUCTION not in historical_calls[2][0][-1]["content"]
