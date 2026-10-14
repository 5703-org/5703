"""Authored V7 engineering controls; independent model quality remains separate."""

import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest

from generation import (
    GenerationService,
    RequestBudget,
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
from generation import coverage_v3
from generation.reliability_v3 import repair_plan
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer


PENDING = {
    "teaching_mode": "hint",
    "help_level": 1,
    "turn_role": "user_question",
    "current_step": 1,
    "current_problem": "Explain the process and its conditions.",
    "pending_tutor_question": "Which starting condition should you locate first?",
    "expected_response_kind": "explanation",
    "delivered_turns": [],
    "disclosure_events": [],
}


def procedural():
    question = "Which starting condition should you locate first?"
    return {
        **chat_value("answer", "Read the opening condition. " + question),
        "tutor_question": {"question": question, "expected_response_kind": "explanation"},
        "learner_attempt_evaluation": None,
    }


def hint_request(arm="D", **updates):
    return req(
        generation_policy=teaching_plan_v7.freeze_generation_policy(arm),
        teaching_context=PENDING,
        **updates,
    )


@pytest.mark.parametrize("arm", ["A", "B", "C", "D"])
def test_pending_action_preserves_recorded_question_and_frozen_factor_flags(arm):
    old = teaching_plan_v6.build_teaching_plan("Please give one hint.", PENDING)
    frozen = teaching_plan_v7.freeze_generation_policy(arm)
    plan = teaching_plan_v7.build_teaching_plan("Please give one hint.", PENDING, policy=frozen)
    assert old["action"] == "recall_concept"
    assert plan["action"] == "support_pending_question"
    assert plan["current_question"] == PENDING["pending_tutor_question"]
    assert plan["current_step"] == PENDING["current_step"]
    assert plan["expected_learner_reply"]["kind"] == "explanation"
    assert plan["observed_attempts"] == []
    assert plan["mastery_inference"] is None
    expected = teaching_plan_v6.freeze_generation_policy(arm)
    assert frozen == {
        **expected,
        "version": teaching_plan_v7.VERSION,
        "teaching_plan_version": teaching_plan_v7.PLAN_VERSION,
    }
    assert frozen["content_plan"] == (arm in {"B", "D"})
    assert frozen["display_selection"] == (arm in {"C", "D"})
    assert plan["provider_calls"] == 0


@pytest.mark.parametrize("arm", ["A", "B", "C", "D"])
def test_pipeline_keeps_factor_separation_and_adds_only_shared_hint_contract(arm):
    adapter = Script([procedural(), checker])
    out = GenerationService(adapter).generate(hint_request(arm), RequestBudget(max_calls=4))
    assert out.succeeded, out.error
    assert len(adapter.calls) == 2
    messages = adapter.calls[0][0]
    data = next(
        json.loads(m["content"].removeprefix("CONTEXT_DATA_JSON:\n"))
        for m in messages
        if m["content"].startswith("CONTEXT_DATA_JSON:\n")
    )
    assert ("TEACHING_ACTION_PLAN" in data) == (arm in {"B", "D"})
    assert teaching_plan_v7.GENERATION_INSTRUCTION in messages[0]["content"]
    checking = adapter.calls[1][0]
    assert teaching_plan_v7.CHECKER_INSTRUCTION in checking[0]["content"]
    assert out.token_budget["progress_plan"]["version"] == teaching_plan_v7.PLAN_VERSION
    assert out.checks[-1]["joint_checker_policy"] == "typed_joint_v5"


def test_incomplete_hint_repair_changes_scope_without_erasing_defects_or_mutating_legacy_plan():
    judgment = {"claims": [], "complete_answer": False, "scope_ok": False}
    structural = [
        {"code": "ACTUAL_CITATION_ASSESSMENT_MISSING", "claim_id": "authored_claim"},
        {"code": "CHECK_UNDISPLAYED_SUPPORT", "claim_id": "authored_claim"},
    ]
    legacy = repair_plan(judgment, structural)
    before = deepcopy(legacy)
    scoped = teaching_plan_v7.scope_repair_plan(legacy, teaching_mode="hint")
    assert legacy == before
    assert scoped["remaining_repair_pairs"] == 1
    assert scoped["actions"][:-1] == before["actions"][:-1]
    assert scoped["actions"][-1]["code"] == "INCOMPLETE_REQUEST"
    assert scoped["actions"][-1]["action"] == (
        "complete_current_permitted_hint_action_without_later_solution"
    )
    assert teaching_plan_v7.scope_repair_plan(legacy, teaching_mode="direct") is legacy
    assert legacy["actions"][-1]["action"] == (
        "cover_supported_facets_and_state_exact_evidence_limits"
    )


def test_genuine_incomplete_hint_requires_repair_and_fresh_independent_check():
    first_check = lambda messages: checker(messages, complete_answer=False, specific_help=False)
    adapter = Script([procedural(), first_check, procedural(), checker])
    out = GenerationService(adapter).generate(
        hint_request(repair_policy="cause_specific_repair_v2"), RequestBudget(max_calls=4)
    )
    assert out.succeeded, out.error
    assert len(adapter.calls) == 4
    assert len(out.checks) == 2
    assert out.checks[0]["accepted"] is False and out.checks[1]["accepted"] is True
    incomplete = next(
        action
        for action in out.checks[0]["repair_plan"]["actions"]
        if action["code"] == "INCOMPLETE_REQUEST"
    )
    assert incomplete["response_scope"] == "current_allowed_hint_action"
    assert out.budget["consumed_calls"] == 4


def test_failed_final_scope_check_still_withholds_hint_within_same_budget():
    bad = lambda messages: checker(messages, scope_ok=False)
    adapter = Script([procedural(), bad, procedural(), bad])
    out = GenerationService(adapter).generate(hint_request(), RequestBudget(max_calls=4))
    assert out.response is None
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(adapter.calls) == 4
    assert out.checks[-1]["accepted"] is False


def test_source_sufficiency_contradiction_is_not_normalized_into_hint_acceptance():
    def contradictory(messages):
        value = checker(messages)
        for row in value["requirements"]:
            row["response_coverage"] = "deferred_for_hint"
            row["missing_information"] = "A mechanism is deliberately withheld from this hint."
        return value

    adapter = Script([procedural(), contradictory, contradictory])
    out = GenerationService(adapter).generate(hint_request(), RequestBudget(max_calls=4))
    assert out.response is None
    assert out.error["code"] == "CHECKER_INCONSISTENT"
    assert "REQUIREMENT_SUFFICIENCY_CONTRADICTION" in out.error["details"]["issue_codes"]
    assert len(adapter.calls) == 3


def test_uncited_source_substitution_cannot_pass_actual_binding_guard():
    def substituted(messages):
        value = checker(messages)
        source = value["requirements"][0]["evidence"][0]
        value["claims"][0] = {
            "claim_id": value["claims"][0]["claim_id"],
            "basis": "textbook",
            "status": "supported",
            "reason": "Authored invalid substitution control.",
            "citations": [
                {
                    "evidence_id": source["evidence_id"],
                    "fragment_ids": [source["fragment_id"]],
                    "relation": "supporting",
                }
            ],
        }
        return value

    adapter = Script([procedural(), substituted])
    out = GenerationService(adapter).generate(hint_request(), RequestBudget(max_calls=2))
    assert out.response is None
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert any(
        issue["code"] == "ACTUAL_CITATION_ASSESSMENT_MISSING"
        for issue in out.checks[-1]["structural_issues"]
    )


def test_full_QA_and_historical_V6_keep_existing_prompts_and_coverage_repairs():
    for policy in [
        teaching_plan_v6.freeze_generation_policy(),
        teaching_plan_v7.freeze_generation_policy(),
    ]:
        adapter = Script([answer(), checker])
        out = GenerationService(adapter).generate(req(generation_policy=policy), RequestBudget())
        assert out.succeeded, out.error
        assert teaching_plan_v7.GENERATION_INSTRUCTION not in adapter.calls[0][0][0]["content"]
        assert teaching_plan_v7.CHECKER_INSTRUCTION not in adapter.calls[1][0][0]["content"]
        assert out.checks[-1]["judgment"]["complete_answer"] is True
    old = Script([procedural(), checker])
    GenerationService(old).generate(
        req(
            generation_policy=teaching_plan_v6.freeze_generation_policy(), teaching_context=PENDING
        ),
        RequestBudget(),
    )
    assert teaching_plan_v7.GENERATION_INSTRUCTION not in old.calls[0][0][0]["content"]
    assert teaching_plan_v7.CHECKER_INSTRUCTION not in old.calls[1][0][0]["content"]


def test_incomplete_full_QA_still_requires_all_requested_facets_and_final_check():
    incomplete = lambda messages: checker(messages, complete_answer=False)
    adapter = Script([answer(), incomplete, answer(), checker])
    out = GenerationService(adapter).generate(
        req(generation_policy=teaching_plan_v7.freeze_generation_policy()),
        RequestBudget(max_calls=4),
    )
    assert out.succeeded, out.error
    assert len(adapter.calls) == 4 and out.checks[-1]["accepted"] is True
    plan = out.checks[0]["repair_plan"]
    assert plan["version"] == "cause_specific_repair_v2"
    assert any(
        action["action"] == "cover_supported_facets_and_state_exact_evidence_limits"
        for action in plan["actions"]
    )


def test_explicit_V7_auxiliary_lookup_remains_frozen_and_rejects_changed_controls():
    resolved = resolve_coverage(
        freeze_policy(coverage_v3.VERSION),
        coverage_v3,
        mode="interactive_chat",
        condition="E1",
        answer_mode="textbook",
        enhancement_version="learning_enhancement_v1",
        reliability_policy="evidence_reliability_v5",
        generation_policy=teaching_plan_v7.freeze_generation_policy(),
    )
    assert resolved.base_version == coverage_v3.VERSION
    broken = {**teaching_plan_v7.freeze_generation_policy(), "provider_planning_calls": 1}
    with pytest.raises(ValueError, match="UNKNOWN_GENERATION_POLICY"):
        teaching_plan_v7.validate_generation_policy(broken)


def test_worker_dispatches_frozen_V7_while_new_request_default_is_V10_without_DB_import():
    source = Path(__file__).resolve().parents[2] / "backend/app/modules/answering/service.py"
    module = ast.parse(source.read_text(encoding="utf-8"))
    statements = []
    for node in ast.walk(module):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name)
            and target.id in {"distributed_coverage", "active_teaching_plan"}
            for target in node.targets
        ):
            statements.append(node)
    statements.sort(key=lambda node: node.lineno)
    assert len(statements) == 2
    imports = {
        "teaching_plan_v2": teaching_plan_v2,
        "teaching_plan_v3": teaching_plan_v3,
        "teaching_plan_v4": teaching_plan_v4,
        "teaching_plan_v5": teaching_plan_v5,
        "teaching_plan_v6": teaching_plan_v6,
        "teaching_plan_v7": teaching_plan_v7,
        "teaching_plan_v8": teaching_plan_v8,
        "teaching_plan_v9": teaching_plan_v9,
        "teaching_plan_v10": teaching_plan_v10,
    }
    for version, expected in [
        (teaching_plan_v7, teaching_plan_v7),
        (teaching_plan_v6, teaching_plan_v6),
    ]:
        scope = {
            **imports,
            "current_core": True,
            "generation_policy": version.freeze_generation_policy(),
        }
        exec(compile(ast.Module(body=statements, type_ignores=[]), str(source), "exec"), scope)
        assert scope["active_teaching_plan"] is expected
    defaults = [
        value
        for node in ast.walk(module)
        if isinstance(node, ast.Dict)
        for key, value in zip(node.keys, node.values)
        if isinstance(key, ast.Constant)
        and key.value == "generation_policy"
        and isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr == "freeze_generation_policy"
    ]
    assert len(defaults) == 1
    assert defaults[0].func.value.id == "teaching_plan_v10"
