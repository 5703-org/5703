"""Authored step-goal controls; fake judgments do not measure model teaching quality."""

import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest

from generation import GenerationService, RequestBudget
from generation import (
    coverage_v3,
    coverage_v4,
    coverage_v5,
    teaching_plan,
    teaching_plan_v2,
    teaching_plan_v3,
    teaching_plan_v4,
    teaching_plan_v5,
    teaching_plan_v6,
    teaching_plan_v7,
    teaching_plan_v8,
    teaching_plan_v9,
    teaching_plan_v10,
)
from generation.adapters import chat_value
from generation.coverage_query_policy_v1 import freeze_policy, resolve_coverage
from retrieval.source_spans import text_hash
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script


CASES = [
    {
        "problem": "The gas initially has pressure 100 kPa and volume 2 L. Determine its final pressure at volume 4 L with constant temperature and amount.",
        "step": 1,
        "goal": "Choose the supplied pressure-volume relation before substituting values.",
        "source": "For a fixed amount of ideal gas at constant temperature, P1 * V1 = P2 * V2.",
        "given": "The gas initially has pressure 100 kPa and volume 2 L.",
        "repeat": "What is the initial pressure of the gas?",
        "good": "Read the supplied relation. Which two quantities does it connect across the states?",
    },
    {
        "problem": "Solve 3x + 5 = 20.",
        "step": 2,
        "goal": "Choose the inverse operation that removes the added constant before changing the coefficient.",
        "source": "An equation remains equal when the same operation is applied to both sides. Subtraction undoes addition; division undoes multiplication.",
        "given": "Solve 3x + 5 = 20.",
        "repeat": "What number is added to 3x?",
        "good": "Look at the added term. Which inverse operation would remove it on both sides?",
    },
    {
        "problem": "Compare enzyme activity at 20 C and 30 C without changing substrate concentration.",
        "step": 3,
        "goal": "Identify the controlled condition needed for this comparison before explaining the results.",
        "source": "A fair comparison changes one factor while keeping other relevant conditions constant.",
        "given": "Compare enzyme activity at 20 C and 30 C without changing substrate concentration.",
        "repeat": "What are the two temperatures?",
        "good": "Which stated condition must stay unchanged so the comparison tests only one factor?",
    },
]


def context(case, **changes):
    return {
        "teaching_mode": "hint",
        "help_level": 1,
        "turn_role": "user_question",
        "current_problem": case["problem"],
        "current_step": case["step"],
        "delivered_turns": [],
        "disclosure_events": [],
        "practice_context": {
            "version": "practice_tutor_context_v1",
            "current_step": case["step"],
            "current_step_prompt": case["goal"],
        },
        **changes,
    }


def request(case, *, arm="D", **changes):
    value = req(
        question="Help me with the current step without giving the answer.",
        generation_policy=teaching_plan_v9.freeze_generation_policy(arm),
        teaching_context=context(case),
        **changes,
    )
    text = case["source"]
    value.evidence[0].update(text=text, text_hash=text_hash(text))
    mapping = value.source_map["c1"]
    mapping.update(chunk_text=text, chunk_hash=text_hash(text))
    mapping["units"][0].update(cleaned_text=text, text_hash=text_hash(text))
    mapping["spans"][0].update(end=len(text), chunk_end=len(text))
    return value


def data(messages):
    return next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))


def hint(text, question):
    return {
        **chat_value("answer", text + " " + question),
        "tutor_question": {"question": question, "expected_response_kind": "explanation"},
        "learner_attempt_evaluation": None,
    }


def judgment(case, *, repetitive=False):
    def authored(messages):
        value = checker(
            messages,
            non_repetitive_next_action=not repetitive,
            specific_help=not repetitive,
            complete_answer=not repetitive,
        )
        for row in value["requirements"]:
            row["response_coverage"] = "deferred_for_hint"
        for claim, proposed in zip(value["claims"], data(messages)["CLAIMS"]):
            if proposed["text"] == case["given"]:
                claim.update(basis="problem_input", status="supported", problem_quote=case["given"])
        return value

    return authored


def capture(record_property, name, outcome, script):
    record_property(
        "authored_step_goal_control",
        json.dumps(
            {
                "control": name,
                "stages": [kw["request_context"]["purpose"] for _m, kw in script.calls],
                "consumed_calls": outcome.budget["consumed_calls"],
                "native_accepted": outcome.succeeded,
                "error_code": (outcome.error or {}).get("code"),
                "human_rating": None,
                "semantic_accuracy_measured": False,
            }
        ),
    )


@pytest.mark.parametrize("case", CASES)
def test_saved_operation_is_verbatim_and_does_not_replace_problem_or_evidence_needs(case):
    original = context(case)
    prior = teaching_plan_v7.build_teaching_plan("One clue, please.", original)
    plan = teaching_plan_v9.build_teaching_plan("One clue, please.", original)
    assert plan["current_question"] == case["goal"]
    assert plan["current_step"] == case["step"]
    assert plan["action"] == "support_recorded_practice_step"
    assert plan["original_problem"] == prior["original_problem"] == case["problem"]
    assert plan["evidence_needs"] == prior["evidence_needs"]
    assert plan["allowed_disclosure"]["help_level"] == 1
    assert plan["allowed_disclosure"]["complete_answer_allowed"] is False
    assert plan["provider_calls"] == 0 and plan["mastery_inference"] is None
    assert plan["recorded_step_goal"]["answer_key_used"] is False
    assert original == context(case)


@pytest.mark.parametrize("case", CASES)
def test_pending_suboperation_keeps_priority_without_requiring_goal_text_equality(case):
    pending = case["good"]
    value = context(case, pending_tutor_question=pending)
    plan = teaching_plan_v9.build_teaching_plan("One clue, please.", value)
    assert plan["action"] == "support_pending_question"
    assert plan["current_question"] == pending != case["goal"]
    assert plan["recorded_step_goal"]["operation"] == case["goal"]
    assert plan["current_step"] == case["step"]
    value.pop("current_step")
    without_outer_step = teaching_plan_v9.build_teaching_plan("One clue, please.", value)
    assert without_outer_step["current_step"] == case["step"]
    assert without_outer_step["current_question"] == pending


def test_learner_attempt_and_direct_help_keep_their_inherited_actions():
    case = CASES[1]
    for value in (
        context(case, turn_role="learner_attempt", pending_tutor_question=case["good"]),
        context(case, teaching_mode="direct"),
    ):
        old = teaching_plan_v7.build_teaching_plan("My response.", value)
        new = teaching_plan_v9.build_teaching_plan("My response.", value)
        assert "recorded_step_goal" not in new
        assert new == {
            **old,
            "version": teaching_plan_v9.PLAN_VERSION,
            "policy_flags": teaching_plan_v9.freeze_generation_policy(),
        }


@pytest.mark.parametrize("bad", [True, 0, -1, "2"])
def test_invalid_saved_step_numbers_fail_closed(bad):
    value = context(CASES[0])
    value["practice_context"]["current_step"] = bad
    with pytest.raises(ValueError, match="INVALID_RECORDED_PRACTICE_STEP"):
        teaching_plan_v9.build_teaching_plan("One clue.", value)


def test_mismatched_owned_step_fails_including_with_a_pending_subquestion():
    for pending in (None, CASES[0]["good"]):
        value = context(CASES[0], current_step=2, pending_tutor_question=pending)
        with pytest.raises(ValueError, match="RECORDED_PRACTICE_STEP_MISMATCH"):
            teaching_plan_v9.build_teaching_plan("One clue.", value)


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("arm", ["A", "B", "C", "D"])
def test_native_generation_and_checker_receive_identical_goal_across_factor_arms(
    case, arm, record_property
):
    script = Script([hint("Use the stated current step.", case["good"]), judgment(case)])
    out = GenerationService(script, checker_adapter=script).generate(request(case, arm=arm))
    assert out.succeeded, out.error
    generated = next(
        json.loads(m["content"].removeprefix("CONTEXT_DATA_JSON:\n"))
        for m in script.calls[0][0]
        if m["content"].startswith("CONTEXT_DATA_JSON:\n")
    )
    checked = data(script.calls[1][0])
    assert generated["CURRENT_STEP_GOAL"] == checked["CURRENT_STEP_GOAL"]
    assert generated["CURRENT_STEP_GOAL"]["operation"] == case["goal"]
    assert ("TEACHING_ACTION_PLAN" in generated) == (arm in {"B", "D"})
    assert teaching_plan_v9.GENERATION_INSTRUCTION in script.calls[0][0][0]["content"]
    assert teaching_plan_v9.CHECKER_INSTRUCTION in script.calls[1][0][0]["content"]
    assert out.response["short_answer"] is None
    assert out.checks[-1]["accepted"] is True
    capture(record_property, "two_stage_goal_" + str(case["step"]) + arm, out, script)


@pytest.mark.parametrize("case", CASES[:2])
def test_repetition_negative_repairs_only_question_and_requires_fresh_check(case, record_property):
    bad = hint(case["given"], case["repeat"])
    repaired = hint(case["given"], case["good"])
    script = Script([bad, judgment(case, repetitive=True), repaired, judgment(case)])
    out = GenerationService(script, checker_adapter=script).generate(
        request(case), RequestBudget(max_calls=4, max_active_seconds=180)
    )
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4
    assert [kw["request_context"]["purpose"] for _m, kw in script.calls] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.checks[0]["accepted"] is False
    assert out.checks[0]["judgment_raw_aliases"]["non_repetitive_next_action"] is False
    assert case["given"] in out.response["answer_text"]
    assert out.response["answer_text"] == repaired["answer_text"]
    assert out.checks[-1]["accepted"] is True
    assert out.delivered_projection["response"] == out.response
    capture(record_property, "repetition_repair_" + str(case["step"]), out, script)


def test_persistent_repetition_and_unrelated_pending_action_never_publish(record_property):
    case = CASES[0]
    value = request(case)
    value.teaching_context["pending_tutor_question"] = case["repeat"]
    script = Script([hint(case["given"], case["repeat"]), judgment(case, repetitive=True)])
    out = GenerationService(script, checker_adapter=script).generate(
        value, RequestBudget(max_calls=2)
    )
    assert not out.succeeded and out.response is None and not out.delivered_projection
    assert (
        "TUTOR_ACTION_REPEATS_DISCLOSED_ANSWER"
        in out.token_budget["claim_support"]["structural_issue_codes"]
    )
    assert data(script.calls[1][0])["CURRENT_STEP_GOAL"]["operation"] == case["goal"]
    capture(record_property, "negative_nonrepeat_gate", out, script)


def test_stale_supplied_plan_is_rejected_before_any_adapter_call():
    case = CASES[0]
    value = request(case)
    value.teaching_plan = teaching_plan_v9.build_teaching_plan(
        value.question, value.teaching_context
    )
    value.teaching_plan["current_question"] = "A stale different operation."
    script = Script([])
    out = GenerationService(script).generate(value)
    assert not out.succeeded and out.response is None
    assert not script.calls
    assert out.error["code"] == "ENHANCEMENT_VALIDATION_ERROR"


@pytest.mark.parametrize("module", [coverage_v3, coverage_v4, coverage_v5])
def test_supplement_dispatch_accepts_exact_v9_policy_without_extra_provider_work(module):
    value = request(CASES[0])
    kwargs = {"base_version": coverage_v3.VERSION} if module is coverage_v5 else {}
    _, _, trace = module.supplement_once(
        CASES[0]["source"],
        value.evidence,
        None,
        teaching_plan_v9.freeze_generation_policy(),
        retrieve=lambda *_a, **_k: pytest.fail("No retrieval is needed for this greeting."),
        rerank=lambda values, *_a, **_k: values,
        screen=lambda values, *_a, **_k: values,
        checkpoint=lambda *_a, **_k: None,
        **kwargs,
    )
    assert trace["retrieval_passes"] == 0


def test_query_coverage_v9_replay_and_current_v10_default_dispatch():
    resolve_coverage(
        freeze_policy(coverage_v3.VERSION),
        coverage_v3,
        mode="interactive_chat",
        condition="E1",
        answer_mode="textbook",
        enhancement_version="learning_enhancement_v1",
        reliability_policy="evidence_reliability_v5",
        generation_policy=teaching_plan_v9.freeze_generation_policy(),
    )
    path = Path(__file__).resolve().parents[2] / "backend/app/modules/answering/service.py"
    tree = ast.parse(path.read_text("utf-8"))
    selected = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id in {"distributed_coverage", "active_teaching_plan"}
            for t in node.targets
        )
    ]
    selected.sort(key=lambda node: node.lineno)
    modules = [
        teaching_plan_v2,
        teaching_plan_v3,
        teaching_plan_v4,
        teaching_plan_v5,
        teaching_plan_v6,
        teaching_plan_v7,
        teaching_plan_v8,
        teaching_plan_v9,
        teaching_plan_v10,
    ]
    for module in modules:
        scope = {m.__name__.split(".")[-1]: m for m in modules}
        scope.update(current_core=True, generation_policy=module.freeze_generation_policy())
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), scope)
        assert scope["active_teaching_plan"] is module
    defaults = [
        value
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        for key, value in zip(node.keys, node.values)
        if isinstance(key, ast.Constant)
        and key.value == "generation_policy"
        and isinstance(value, ast.Call)
    ]
    assert len(defaults) == 1 and defaults[0].func.value.id == "teaching_plan_v10"


@pytest.mark.parametrize(
    "module",
    [
        teaching_plan,
        teaching_plan_v2,
        teaching_plan_v3,
        teaching_plan_v4,
        teaching_plan_v5,
        teaching_plan_v6,
    ],
)
def test_frozen_legacy_plans_keep_their_original_non_saved_step_action(module):
    case = CASES[0]
    plan = module.build_teaching_plan("One clue.", context(case))
    assert "recorded_step_goal" not in plan and plan["current_question"] is None
    assert plan["action"] == "recall_concept"


@pytest.mark.parametrize("mode", ["direct", "hint"])
def test_direct_and_explicit_general_knowledge_keep_source_mode_boundaries(mode, record_property):
    case = CASES[0]
    value = request(case, answer_mode="general_knowledge")
    value.teaching_context["teaching_mode"] = mode
    value.evidence, value.source_map = [], {}
    script = Script(
        [chat_value("answer", "General knowledge: a process can be explained."), checker]
    )
    out = GenerationService(script).generate(value)
    assert out.succeeded, out.error
    assert ("CURRENT_STEP_GOAL" in data(script.calls[1][0])) == (mode == "hint")
    assert (teaching_plan_v9.GENERATION_INSTRUCTION in script.calls[0][0][0]["content"]) == (
        mode == "hint"
    )
    assert out.attribution["claims"][0]["support"]["basis"] == "general_knowledge"
    assert not out.delivered_projection["citation_views"]
    capture(record_property, mode + "_explicit_general_knowledge", out, script)


def test_negative_fresh_recheck_stops_at_four_calls_without_publication(record_property):
    case = CASES[0]
    script = Script(
        [
            hint(case["given"], case["repeat"]),
            judgment(case, repetitive=True),
            hint(case["given"], case["good"]),
            judgment(case, repetitive=True),
        ]
    )
    out = GenerationService(script).generate(request(case), RequestBudget(max_calls=4))
    assert not out.succeeded and out.response is None and not out.delivered_projection
    assert out.budget["consumed_calls"] == 4
    assert all(not row["accepted"] for row in out.checks)
    capture(record_property, "negative_final_fresh_check", out, script)


def test_repetition_repair_cannot_rewrite_supported_problem_givens(record_property):
    case = CASES[0]
    changed = case["given"].replace("100 kPa", "101 kPa")
    script = Script(
        [
            hint(case["given"], case["repeat"]),
            judgment(case, repetitive=True),
            hint(changed, case["good"]),
        ]
    )
    out = GenerationService(script).generate(request(case), RequestBudget(max_calls=4))
    assert not out.succeeded and out.response is None
    assert out.error["code"] == "REPAIR_CHANGED_APPROVED_CONTENT"
    assert out.budget["consumed_calls"] == 3 and len(script.calls) == 3
    capture(record_property, "protected_given_rewrite_rejected", out, script)
