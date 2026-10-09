"""Authored V10 routing controls; fake verdicts do not measure teaching quality."""

from copy import deepcopy
import json

import pytest

from generation import GenerationService, RequestBudget, teaching_plan_v9, teaching_plan_v10
from generation.adapters import chat_value
from generation.hint_progression_v10 import CODE, expression_issues
from retrieval.source_spans import text_hash
from test_answer_core_v5 import checker
from test_enhancement_generation import Script
from test_teaching_plan_v9 import CASES, data, hint, judgment, request as previous_request


def request(case=CASES[0], *, level=1, **changes):
    value = previous_request(case, **changes)
    value.generation_policy = teaching_plan_v10.freeze_generation_policy()
    value.teaching_context["help_level"] = level
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


def native(values, value, calls=2):
    script = Script(values)
    result = GenerationService(script, checker_adapter=script).generate(
        value, RequestBudget(max_calls=calls, max_active_seconds=180)
    )
    return result, script


@pytest.mark.parametrize("level", [1, 2, 3])
@pytest.mark.parametrize("case", CASES)
def test_owned_stage_is_frozen_with_goal_and_native_guidance_remains_acceptable(case, level):
    value = request(case, level=level)
    expected = plan(value)
    out, script = native(
        [hint("Use the conditions in the current step.", case["good"]), judgment(case)], value
    )
    assert out.succeeded, out.error
    generated = generated_context(script.calls[0][0])["TEACHING_ACTION_PLAN"]
    checked = data(script.calls[1][0])["TEACHING_ACTION_PLAN"]
    assert generated == checked == expected
    assert expected["hint_stage"]["level"] == level
    assert (
        expected["hint_stage"]["kind"]
        == {1: "question", 2: "guided_cue", 3: "strongest_goal_safe_cue"}[level]
    )
    assert expected["recorded_step_goal"]["operation"] == case["goal"]
    assert expected["allowed_disclosure"]["complete_answer_allowed"] is False
    assert expected["hint_stage"]["selection_expression_guard"] == (case in CASES[:2])
    assert out.checks[-1]["hint_progression_support"]["issue_codes"] == []


@pytest.mark.parametrize("level", [1, 2, 3])
@pytest.mark.parametrize(
    "case,formula",
    [
        (CASES[0], "P1 * V1 = P2 * V2"),
        (
            {**CASES[0], "goal": "Select a formula before substituting resistance and current."},
            "V = I * R",
        ),
        ({**CASES[0], "goal": "Choose a relation before substituting the givens."}, "F = m * a"),
    ],
)
def test_all_true_checker_cannot_publish_a_new_selection_expression(case, formula, level):
    question = "Which relation should you use?"
    draft = hint("Use " + formula + ".", question)
    out, _ = native([draft, judgment(case)], request(case, level=level))
    assert not out.succeeded and out.response is None
    raw = out.checks[0]["typed_judgment_raw_aliases"]
    assert all(
        raw[name] is True
        for name in (
            "body_ok",
            "specific_help",
            "scope_ok",
            "suggestions_ok",
            "evidence_display_ok",
            "cumulative_ok",
            "complete_answer",
            "attempt_evaluation_ok",
            "tutor_question_ok",
            "non_repetitive_next_action",
        )
    )
    assert out.checks[0]["hint_progression_support"]["issue_codes"] == [CODE]
    assert out.checks[0]["accepted"] is False
    assert out.budget["consumed_calls"] == 2


@pytest.mark.parametrize("mode", ["hint", "direct"])
def test_formula_for_saved_application_or_direct_help_remains_permitted(mode):
    case = {**CASES[0], "goal": "Apply the supplied relation to calculate the new pressure."}
    value = request(case)
    value.teaching_context["teaching_mode"] = mode
    draft = (
        chat_value("answer", "P1 * V1 = P2 * V2. [ev_001]", citations=["ev_001"])
        if mode == "direct"
        else {
            **hint("Use P1 * V1 = P2 * V2. [ev_001]", "Which value belongs to the final volume?"),
            "citations": ["ev_001"],
        }
    )
    out, _ = native([draft, checker if mode == "direct" else judgment(case)], value)
    assert out.succeeded, out.error
    expected = plan(value)
    if mode == "direct":
        assert not expected["enabled"] and "hint_stage" not in expected
    else:
        assert expected["hint_stage"]["selection_expression_guard"] is False


def test_whole_original_algebra_equation_is_not_a_new_selected_operation():
    case = CASES[1]
    out, _ = native([hint("Solve 3x + 5 = 20.", case["good"]), judgment(case)], request(case))
    assert out.succeeded, out.error
    assert out.checks[0]["hint_progression_support"]["issue_codes"] == []
    value = request(case)
    assert expression_issues(value, {"answer_text": "3x = 20 - 5"}, None, {}, plan(value))


def test_pending_and_learner_attempt_keep_precedence_at_owned_level():
    case = CASES[1]
    for role in ("user_question", "learner_attempt"):
        value = request(case, level=2)
        value.teaching_context.update(turn_role=role, pending_tutor_question=case["good"])
        value.teaching_context.pop("current_step")
        expected = plan(value)
        prior = teaching_plan_v9.build_teaching_plan(value.question, value.teaching_context)
        assert expected["action"] == prior["action"]
        assert expected["current_question"] == prior["current_question"]
        assert expected["current_step"] == case["step"]
        assert expected["recorded_step_goal"]["operation"] == case["goal"]
        assert expected["hint_stage"]["level"] == 2
        assert expected["hint_stage"]["selection_expression_guard"] is True


@pytest.mark.parametrize("field", ["hint_stage", "recorded_step_goal", "current_step"])
def test_model_cannot_change_owned_goal_stage_or_step(field):
    value = request()
    expected = plan(value)
    forged = deepcopy(expected)
    forged[field] = {} if field != "current_step" else 2
    with pytest.raises(ValueError, match="HINT_PROGRESSION_PLAN_MISMATCH"):
        teaching_plan_v10.validate_plan(
            forged,
            value.question,
            value.teaching_context,
            value.understanding,
            policy=value.generation_policy,
            answer_mode=value.answer_mode,
        )


def with_unrelated_source(value):
    text = "The temperature is held constant."
    evidence = deepcopy(value.evidence[0])
    evidence.update(evidence_id="ev_002", chunk_id="c2", text=text, text_hash=text_hash(text))
    mapping = deepcopy(value.source_map["c1"])
    mapping.update(chunk_text=text, chunk_hash=text_hash(text))
    mapping["units"][0].update(cleaned_text=text, text_hash=text_hash(text))
    mapping["spans"][0].update(end=len(text), chunk_end=len(text))
    value.evidence.append(evidence)
    value.source_map["c2"] = mapping
    return value


def factual_draft(*, unsafe):
    safe = "The temperature is held constant. [ev_002]"
    question = "Which two changing quantities should the relation connect?"
    text = ("P1 * V1 = P2 * V2. [ev_001] " if unsafe else "") + safe + " " + question
    return {
        **chat_value("answer", text, citations=["ev_001", "ev_002"] if unsafe else ["ev_002"]),
        "tutor_question": {"question": question, "expected_response_kind": "explanation"},
        "learner_attempt_evaluation": None,
    }


@pytest.mark.parametrize("still_unsafe", [False, True])
def test_local_negative_repairs_then_fresh_checks_same_stage_and_protects_other_facts(still_unsafe):
    value = with_unrelated_source(request(level=2))
    initial = factual_draft(unsafe=True)
    repaired = factual_draft(unsafe=still_unsafe)
    out, script = native(
        [initial, judgment(CASES[0]), repaired, judgment(CASES[0])], value, calls=4
    )
    assert out.succeeded is (not still_unsafe), out.error
    assert [row["stage"] for row in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.budget["consumed_calls"] == 4
    feedback = json.loads(script.calls[2][0][-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    assert feedback["teaching_repair_boundary"]["locally_defective_claim_ids"]
    assert feedback["protected_exact_claims"]
    assert all("P1 * V1" not in row["text"] for row in feedback["protected_exact_claims"])
    assert any(
        row["text"] == "The temperature is held constant. [ev_002]"
        for row in feedback["protected_exact_claims"]
    )
    assert (
        feedback["teaching_repair_boundary"]["release_source_supported_claims_for_repair"] is False
    )
    assert (
        data(script.calls[1][0])["TEACHING_ACTION_PLAN"]
        == data(script.calls[3][0])["TEACHING_ACTION_PLAN"]
    )
    assert out.checks[-1]["hint_progression_support"]["issue_codes"] == (
        [CODE] if still_unsafe else []
    )
    if out.succeeded:
        assert out.response["citations"] == ["ev_002"]


def test_repair_cannot_rewrite_an_unrelated_approved_fact_or_citation():
    value = with_unrelated_source(request())
    repaired = factual_draft(unsafe=False)
    repaired["answer_text"] = repaired["answer_text"].replace(
        "The temperature is held constant. [ev_002]", "The amount is held constant. [ev_002]"
    )
    out, _ = native([factual_draft(unsafe=True), judgment(CASES[0]), repaired], value, calls=4)
    assert not out.succeeded and out.error["code"] == "REPAIR_CHANGED_APPROVED_CONTENT"
    assert out.budget["consumed_calls"] == 3
