"""Pending-action provenance/repair regressions; authored judgments are not quality scores."""

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from generation import GenerationService, RequestBudget
from generation import (
    coverage_v3,
    coverage_v4,
    coverage_v5,
    pending_action_v8,
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
from generation.checker_encoding import decode
from generation.coverage_query_policy_v1 import freeze_policy, resolve_coverage
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer


PENDING = {
    "teaching_mode": "hint",
    "help_level": 1,
    "turn_role": "user_question",
    "current_step": 1,
    "current_problem": "Explain photosynthesis and its conditions.",
    "pending_tutor_question": "Which energy source should you locate in the opening statement?",
    "expected_response_kind": "explanation",
    "delivered_turns": [],
    "disclosure_events": [],
}


def hint_request(arm="D", **updates):
    values = {
        "generation_policy": teaching_plan_v8.freeze_generation_policy(arm),
        "joint_checker_policy": pending_action_v8.POLICY,
        "teaching_context": deepcopy(PENDING),
        "repair_policy": "claim_patch_repair_v3",
    }
    return req(**{**values, **updates})


def procedural(question=None):
    question = question or PENDING["pending_tutor_question"]
    return {
        **chat_value(
            "answer", "Read the opening statement and locate the requested input. " + question
        ),
        "tutor_question": {"question": question, "expected_response_kind": "explanation"},
        "learner_attempt_evaluation": None,
    }


def data_from(messages):
    value = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
    return decode(value) if "CHECKER_INPUT_ENCODING" in value else value


def pending_checker(messages, **changes):
    value = checker(messages)
    context = data_from(messages)["PENDING_ACTION_CONTEXT"]
    value["pending_action"] = {
        "context_sha256": context["context_sha256"],
        "pending_question": context["pending_question"],
        "useful_learner_action": True,
        "reason": "Authored action judgment, not independent semantic acceptance.",
        "cumulative_target_withheld": True,
        "cumulative_scope_ok": True,
        "cumulative_reason": "Authored current-plus-prior assessment.",
        "cumulative_quotes": [],
        "surfaces": [
            {
                "surface_id": row["surface_id"],
                "same_operation": True,
                "target_withheld": True,
                "learner_progress_not_assumed": True,
                "quotes": [row["exact_text"][:3000]],
                "reason": "Authored whole-surface assessment.",
            }
            for row in context["surfaces"]
        ],
    }
    return {**value, **changes}


def negative(field, *, surface_id="answer_text", useful=True):
    def check(messages):
        value = pending_checker(messages)
        row = next(
            row for row in value["pending_action"]["surfaces"] if row["surface_id"] == surface_id
        )
        row[field] = False
        value["pending_action"]["useful_learner_action"] = useful
        return value

    return check


@pytest.mark.parametrize("arm", ["A", "B", "C", "D"])
def test_new_pending_plan_and_pipeline_keep_all_factors_and_exact_question(arm):
    frozen = teaching_plan_v8.freeze_generation_policy(arm)
    expected = teaching_plan_v7.freeze_generation_policy(arm)
    assert frozen == {
        **expected,
        "version": teaching_plan_v8.VERSION,
        "teaching_plan_version": teaching_plan_v8.PLAN_VERSION,
    }
    plan = teaching_plan_v8.build_teaching_plan("One hint, please.", PENDING, policy=frozen)
    assert plan["current_question"] == PENDING["pending_tutor_question"]
    assert plan["allowed_disclosure"]["pending_target_must_remain_withheld"] is True
    assert plan["exact_given_guard"] is True
    assert plan["provider_calls"] == 0 and plan["mastery_inference"] is None
    script = Script([procedural(), pending_checker])
    out = GenerationService(script).generate(hint_request(arm), RequestBudget())
    assert out.succeeded, out.error
    assert len(script.calls) == 2
    assert script.calls[1][1]["response_schema_name"] == pending_action_v8.SCHEMA
    schema = script.calls[1][1]["response_schema"]
    assert "pending_action" in schema["required"]
    assert schema["additionalProperties"] is False
    assert "cumulative_target_withheld" in schema["$defs"]["PendingActionCheck"]["required"]
    assert out.token_budget["pending_action_contract_revision"] == pending_action_v8.VERSION
    generated = next(
        json.loads(m["content"].removeprefix("CONTEXT_DATA_JSON:\n"))
        for m in script.calls[0][0]
        if m["content"].startswith("CONTEXT_DATA_JSON:\n")
    )
    checked = data_from(script.calls[1][0])
    assert ("TEACHING_ACTION_PLAN" in generated) == (arm in {"B", "D"})
    assert ("TEACHING_ACTION_PLAN" in checked) == (arm in {"B", "D"})
    assert (
        generated["PENDING_ACTION_SCOPE"]["pending_question"] == PENDING["pending_tutor_question"]
    )
    assert (
        checked["PENDING_ACTION_CONTEXT"]["pending_question"] == PENDING["pending_tutor_question"]
    )
    assert out.checks[-1]["pending_action_context"] == checked["PENDING_ACTION_CONTEXT"]
    assert out.token_budget["pending_action_support"]["local_semantic_certification"] is False
    assert out.token_budget["pending_action_support"]["human_rating"] is None
    assert out.response["citations"] == []


@pytest.mark.parametrize(
    "updates",
    [
        {"generation_policy": teaching_plan_v7.freeze_generation_policy()},
        {"joint_checker_policy": "typed_joint_v5"},
        {"teaching_context": {"teaching_mode": "direct"}},
        {"teaching_context": {"teaching_mode": "hint", "turn_role": "user_question"}},
        {"teaching_context": {**PENDING, "turn_role": "learner_attempt"}},
        {"source_relation_policy": "source_relation_contract_v1"},
        {"enhancement_version": None},
        {"teaching_condition": "T0"},
        {"joint_checker_policy": "scoped_compact_v7"},
    ],
)
def test_invalid_pending_policy_pairing_fails_before_provider_submission(updates):
    script = Script([])
    out = GenerationService(script).generate(hint_request(**updates), RequestBudget())
    assert out.response is None
    assert out.error["code"] in {
        "PENDING_ACTION_POLICY_INCOMPATIBLE",
        "JOINT_CHECKER_POLICY_INCOMPATIBLE",
    }
    assert script.calls == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(current_question="A later mechanism?"),
        lambda p: p["allowed_disclosure"].update(pending_target_must_remain_withheld=False),
        lambda p: p.update(version=teaching_plan_v7.PLAN_VERSION),
        lambda p: p.clear(),
    ],
)
def test_stale_or_modified_saved_plan_fails_without_a_generation_call(mutate):
    request = hint_request()
    plan = teaching_plan_v8.build_teaching_plan(
        request.question,
        request.teaching_context,
        request.understanding,
        policy=request.generation_policy,
    )
    mutate(plan)
    request.teaching_plan = plan
    script = Script([])
    out = GenerationService(script).generate(request, RequestBudget())
    assert out.response is None and script.calls == []
    assert out.error["details"]["validation_code"] == "PENDING_ACTION_PLAN_MISMATCH"


@pytest.mark.parametrize(
    "field,code",
    [
        ("same_operation", "PENDING_ACTION_WRONG_OPERATION"),
        ("target_withheld", "PENDING_TARGET_DISCLOSED"),
        ("learner_progress_not_assumed", "PENDING_PROGRESS_INVENTED"),
    ],
)
def test_supported_facts_do_not_protect_a_defective_pending_action_from_whole_hint_repair(
    field, code
):
    next_question = "Which layer orientation should you identify next?"
    first = {
        **answer("Photosynthesis uses light energy. [ev_001] " + next_question),
        "tutor_question": {"question": next_question, "expected_response_kind": "concept"},
        "learner_attempt_evaluation": None,
    }
    script = Script([first, negative(field, useful=False), procedural(), pending_checker])
    out = GenerationService(script).generate(hint_request(), RequestBudget())
    assert out.succeeded, out.error
    assert len(script.calls) == 4
    assert [row["stage"] for row in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.checks[0]["accepted"] is False and out.checks[1]["accepted"] is True
    assert code in out.checks[0]["pending_action_assessment"]["semantic_defect_codes"]
    assert script.calls[2][1]["response_schema_name"] == "chat_response_teaching_v5"
    boundary = out.token_budget["teaching_repair_boundaries"][0]
    assert boundary["release_source_supported_claims_for_repair"] is True
    assert boundary["previously_source_approved_claim_ids"]
    assert out.teaching_context["tutor_question"] == procedural()["tutor_question"]
    assert out.response["answer_text"] == procedural()["answer_text"]
    assert out.response["citations"] == []
    assert (
        out.checks[0]["pending_action_context"]["context_sha256"]
        != out.checks[1]["pending_action_context"]["context_sha256"]
    )
    assert all(
        action["response_scope"] == "whole_current_pending_hint"
        for action in out.checks[0]["repair_plan"]["actions"]
        if action["code"].startswith("PENDING_")
    )


def test_non_repetition_negative_releases_supported_target_and_old_question_metadata():
    first = {
        **answer("Photosynthesis uses light energy. [ev_001] " + PENDING["pending_tutor_question"]),
        "tutor_question": procedural()["tutor_question"],
        "learner_attempt_evaluation": None,
    }

    def repeat(messages):
        return pending_checker(messages, non_repetitive_next_action=False)

    script = Script([first, repeat, procedural(), pending_checker])
    out = GenerationService(script).generate(hint_request(), RequestBudget())
    assert out.succeeded, out.error
    assert len(script.calls) == 4
    assert script.calls[2][1]["response_schema_name"] == "chat_response_teaching_v5"
    assert "light energy" not in out.response["answer_text"]
    assert (
        "non_repetitive_next_action"
        in out.token_budget["teaching_repair_boundaries"][0]["failed_global_gate_names"]
    )


@pytest.mark.parametrize("surface", ["tutor_question", "suggestion:0", "citation"])
def test_question_suggestion_and_actual_complete_source_display_negatives_block_publication(
    surface,
):
    first = {
        **answer("Use the opening source statement. [ev_001] " + PENDING["pending_tutor_question"]),
        "tutor_question": procedural()["tutor_question"],
        "learner_attempt_evaluation": None,
        "follow_up_questions": ["Name light energy."],
    }

    def bad_surface(messages):
        value = pending_checker(messages)
        identity = surface
        if surface == "citation":
            identity = next(
                row["surface_id"]
                for row in data_from(messages)["PENDING_ACTION_CONTEXT"]["surfaces"]
                if row["kind"] == "citation_text"
            )
        row = next(
            row for row in value["pending_action"]["surfaces"] if row["surface_id"] == identity
        )
        row["target_withheld"] = False
        return value

    script = Script([first, bad_surface, procedural(), pending_checker])
    out = GenerationService(script).generate(hint_request(), RequestBudget())
    assert out.succeeded, out.error
    assert len(script.calls) == 4
    context = out.checks[0]["pending_action_context"]
    assert any(
        row["kind"] == "citation_text" and "Photosynthesis uses light energy." in row["exact_text"]
        for row in context["surfaces"]
    )
    assert (
        "PENDING_TARGET_DISCLOSED"
        in out.checks[0]["pending_action_assessment"]["semantic_defect_codes"]
    )
    assert out.delivered_projection["citation_views"] == []


@pytest.mark.parametrize(
    "defect",
    [
        "pending",
        "hash",
        "missing_surface",
        "duplicate_surface",
        "quote",
        "strict_bool",
        "accepted_flag",
    ],
)
def test_invalid_pending_identity_or_quote_is_contract_failure_not_semantic_override(defect):
    def invalid(messages):
        value = pending_checker(messages)
        action = value["pending_action"]
        if defect == "pending":
            action["pending_question"] = "Another question?"
        elif defect == "hash":
            action["context_sha256"] = "0" * 64
        elif defect == "missing_surface":
            action["surfaces"].pop()
        elif defect == "duplicate_surface":
            action["surfaces"].append(deepcopy(action["surfaces"][0]))
        elif defect == "quote":
            action["surfaces"][0]["quotes"] = ["Unsubmitted invented quotation."]
        elif defect == "strict_bool":
            action["surfaces"][0]["target_withheld"] = 1
        else:
            value["accepted"] = True
        return value

    script = Script([procedural(), invalid, invalid])
    out = GenerationService(script).generate(hint_request(), RequestBudget())
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert len(script.calls) == 3
    assert not out.delivered_projection


def test_final_action_negative_is_withheld_at_original_four_call_ceiling():
    bad = negative("target_withheld", useful=False)
    script = Script([procedural(), bad, procedural(), bad])
    out = GenerationService(script).generate(hint_request(), RequestBudget())
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 4 and len(script.calls) == 4
    assert out.checks[-1]["accepted"] is False and not out.delivered_projection


def test_complete_partial_without_limits_remains_a_final_checker_blocker():
    def inconsistent(messages):
        return pending_checker(
            messages,
            complete_answer=True,
            coverage="supported_partial",
            missing_facets=["Actual missing facet."],
            limitations_explicit=False,
        )

    script = Script([procedural(), negative("same_operation"), procedural(), inconsistent])
    out = GenerationService(script).generate(hint_request(), RequestBudget())
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert "COMPLETE_PARTIAL_WITHOUT_LIMITS" in out.error["details"]["issue_codes"]
    assert len(script.calls) == 4


def test_pending_approval_cannot_override_irrelevant_actual_citation():
    def irrelevant(messages):
        value = pending_checker(messages, body_ok=False)
        value["claims"][0]["status"] = "partial"
        value["claims"][0]["citations"][0]["relation"] = "irrelevant"
        return value

    script = Script([answer(), irrelevant])
    out = GenerationService(script).generate(hint_request(), RequestBudget(max_calls=2))
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert "ACTUAL_CITATION_IRRELEVANT" in {
        row["code"] for row in out.checks[-1]["structural_issues"]
    }
    assert len(script.calls) == 2


def test_deferred_hint_does_not_change_source_sufficiency_or_waive_real_missing_information():
    def deferred(messages):
        value = pending_checker(messages)
        for row in value["requirements"]:
            row["response_coverage"] = "deferred_for_hint"
        return value

    script = Script([procedural(), deferred])
    out = GenerationService(script).generate(hint_request(), RequestBudget())
    assert out.succeeded, out.error
    assert out.token_budget["context_coverage"]["semantic_sufficiency"]["status"] == "sufficient"

    def contradictory(messages):
        value = deferred(messages)
        value["requirements"][0]["missing_information"] = "This is deliberate withholding."
        return value

    script = Script([procedural(), contradictory, contradictory])
    out = GenerationService(script).generate(hint_request(), RequestBudget())
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert "REQUIREMENT_SUFFICIENCY_CONTRADICTION" in out.error["details"]["issue_codes"]


@pytest.mark.parametrize("module", [teaching_plan_v6, teaching_plan_v7, teaching_plan_v8])
def test_ordinary_complete_answers_keep_existing_schema_and_full_question_gates(module):
    script = Script([answer(), checker])
    out = GenerationService(script).generate(
        req(generation_policy=module.freeze_generation_policy()), RequestBudget()
    )
    assert out.succeeded, out.error
    assert script.calls[1][1]["response_schema_name"] == "joint_check_v5"
    assert pending_action_v8.CHECKER_INSTRUCTION not in script.calls[1][0][0]["content"]
    assert "pending_action_assessment" not in out.checks[-1]
    assert out.checks[-1]["judgment"]["complete_answer"] is True


def test_frozen_V6_and_V7_hint_requests_do_not_select_the_new_schema():
    for module in (teaching_plan_v6, teaching_plan_v7):
        script = Script([procedural(), checker])
        out = GenerationService(script).generate(
            req(
                generation_policy=module.freeze_generation_policy(),
                teaching_context=deepcopy(PENDING),
            ),
            RequestBudget(),
        )
        assert out.succeeded, out.error
        assert script.calls[1][1]["response_schema_name"] == "joint_check_v5"
        assert "pending_action_context" not in out.checks[-1]


@pytest.mark.parametrize("module", [coverage_v3, coverage_v4, coverage_v5])
def test_native_coverage_dispatch_accepts_exact_V8_and_rejects_changed_limits(module):
    calls = []
    arguments = {
        "retrieve": lambda q, n: calls.append(n) or [],
        "rerank": lambda q, rows: rows,
        "screen": lambda q, rows: (rows, {}),
        "checkpoint": lambda phase, trace: None,
    }
    if module is coverage_v5:
        arguments["base_version"] = coverage_v3.VERSION
    module.supplement_once(
        "Explain photosynthesis.",
        [],
        None,
        teaching_plan_v8.freeze_generation_policy(),
        **arguments,
    )
    assert len(calls) <= 1 and all(n == 10 for n in calls)
    with pytest.raises(ValueError, match="UNKNOWN_GENERATION_POLICY"):
        module.supplement_once(
            "Explain photosynthesis.",
            [],
            None,
            {**teaching_plan_v8.freeze_generation_policy(), "provider_planning_calls": 1},
            **arguments,
        )
    resolved = resolve_coverage(
        freeze_policy(coverage_v3.VERSION),
        coverage_v3,
        mode="interactive_chat",
        condition="E1",
        answer_mode="textbook",
        enhancement_version="learning_enhancement_v1",
        reliability_policy="evidence_reliability_v5",
        generation_policy=teaching_plan_v8.freeze_generation_policy(),
    )
    assert resolved.base_version == coverage_v3.VERSION


def test_worker_explicit_V8_dispatch_and_new_submission_default_V10_without_database_import():
    source = Path(__file__).resolve().parents[2] / "backend/app/modules/answering/service.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id in {"distributed_coverage", "active_teaching_plan"}
            for target in node.targets
        )
    ]
    assignments.sort(key=lambda node: node.lineno)
    assert len(assignments) == 2
    imports = {
        module.__name__.split(".")[-1]: module
        for module in (
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
    }
    for module in (teaching_plan_v6, teaching_plan_v7, teaching_plan_v8):
        scope = {
            **imports,
            "current_core": True,
            "generation_policy": module.freeze_generation_policy(),
        }
        exec(compile(ast.Module(body=assignments, type_ignores=[]), str(source), "exec"), scope)
        assert scope["active_teaching_plan"] is module
    defaults = [
        value
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        for key, value in zip(node.keys, node.values)
        if isinstance(key, ast.Constant)
        and key.value == "generation_policy"
        and isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr == "freeze_generation_policy"
    ]
    assert len(defaults) == 1 and defaults[0].func.value.id == "teaching_plan_v10"


@pytest.mark.parametrize("arm", ["A", "B"])
@pytest.mark.parametrize("surface", ["suggestion:0", "citation_preview"])
def test_all_visible_surfaces_are_checked_when_legacy_surface_flags_are_off(arm, surface):
    first = {
        **answer("Use the opening source statement. [ev_001] " + PENDING["pending_tutor_question"]),
        "tutor_question": procedural()["tutor_question"],
        "learner_attempt_evaluation": None,
        "follow_up_questions": ["Name light energy."],
    }

    def displayed_negative(messages):
        value = pending_checker(messages)
        context = data_from(messages)["PENDING_ACTION_CONTEXT"]
        identity = surface
        if surface == "citation_preview":
            identity = next(
                row["surface_id"] for row in context["surfaces"] if row["kind"] == surface
            )
        next(row for row in value["pending_action"]["surfaces"] if row["surface_id"] == identity)[
            "target_withheld"
        ] = False
        return value

    script = Script([first, displayed_negative, procedural(), pending_checker])
    out = GenerationService(script).generate(
        hint_request(arm, teaching_condition="T1"), RequestBudget()
    )
    assert out.succeeded, out.error
    assert len(script.calls) == 4
    data = data_from(script.calls[1][0])
    assert data["CHECK_SCOPE"]["current_suggestions"] is False
    assert data["CHECK_SCOPE"]["current_evidence_display"] is False
    assert any(
        row["surface_id"] == "suggestion:0" for row in data["PENDING_ACTION_CONTEXT"]["surfaces"]
    )
    assert any(
        row["kind"] == "citation_preview"
        and "Photosynthesis uses light energy." in row["exact_text"]
        for row in data["PENDING_ACTION_CONTEXT"]["surfaces"]
    )
    assert out.checks[-1]["projection_hash"] == out.delivered_projection["content_hash"]
    assert out.checks[-1]["pending_action_context"]["surfaces"] == [
        {"surface_id": "answer_text", "kind": "body", "exact_text": out.response["answer_text"]},
        {
            "surface_id": "tutor_question",
            "kind": "question",
            "exact_text": out.teaching_context["tutor_question"]["question"],
        },
    ]


def test_caption_alt_and_empty_surfaces_have_exact_cardinality_and_quote_provenance():
    request = hint_request("A", teaching_condition="T1")
    response = {**procedural(), "follow_up_questions": [""]}
    projection = {
        "citation_views": [
            {
                "title": "",
                "caption": "Target caption.",
                "alt_text": "Target alt.",
                "segments": [{"text": "", "caption": "Segment caption.", "alt": "Segment alt."}],
                "preview": "",
            }
        ]
    }
    context = pending_action_v8.delivery_context(
        request, response, response["tutor_question"], None, projection, {}
    )
    metadata = [
        row["exact_text"] for row in context["surfaces"] if row["kind"] == "citation_metadata"
    ]
    assert any("Target caption." in row and "Target alt." in row for row in metadata)
    assert any("Segment caption." in row and "Segment alt." in row for row in metadata)
    value = {
        "pending_action": {
            "context_sha256": context["context_sha256"],
            "pending_question": context["pending_question"],
            "useful_learner_action": True,
            "reason": "Authored receipt.",
            "cumulative_target_withheld": True,
            "cumulative_scope_ok": True,
            "cumulative_reason": "Authored receipt.",
            "cumulative_quotes": [],
            "surfaces": [
                {
                    "surface_id": row["surface_id"],
                    "same_operation": True,
                    "target_withheld": True,
                    "learner_progress_not_assumed": True,
                    "quotes": [row["exact_text"]],
                    "reason": "Authored receipt.",
                }
                for row in context["surfaces"]
            ],
        }
    }
    assert pending_action_v8.assess(value, context)[:2] == ([], [])
    bad = deepcopy(value)
    bad["pending_action"]["surfaces"][0]["quotes"] = [""]
    assert pending_action_v8.assess(bad, context)[0][0]["code"] == "PENDING_ACTION_QUOTE_INVALID"
    missing = deepcopy(value)
    missing["pending_action"]["surfaces"] = [
        row for row in missing["pending_action"]["surfaces"] if row["surface_id"] != "suggestion:0"
    ]
    assert (
        pending_action_v8.assess(missing, context)[0][0]["code"]
        == "PENDING_ACTION_SURFACE_IDENTITY_MISMATCH"
    )


@pytest.mark.parametrize("arm", ["A", "B"])
def test_prior_and_current_joint_disclosure_negative_repairs_even_with_legacy_cumulative_off(arm):
    prior = "Focus on the second member of the pair you are about to inspect."
    context = {**PENDING, "delivered_turns": [{"answer_text": prior, "citation_views": []}]}
    first = {
        **answer(
            "Read this pair in order: carbon dioxide; light energy. [ev_001] "
            + PENDING["pending_tutor_question"]
        ),
        "tutor_question": procedural()["tutor_question"],
        "learner_attempt_evaluation": None,
    }

    def jointly_revealing(messages):
        value = pending_checker(messages)
        check_data = data_from(messages)
        assert check_data["PRIOR_EXPOSURE"] == {"disabled": True}
        assert prior in pending_action_v8.canonical(
            check_data["PENDING_ACTION_CONTEXT"]["prior_exposure"]
        )
        action = value["pending_action"]
        action["cumulative_target_withheld"] = False
        action["cumulative_reason"] = (
            "Authored semantic negative: the prior index and current pair jointly specify the target."
        )
        action["cumulative_quotes"] = [
            {"surface_id": "prior_exposure", "quote": prior},
            {
                "surface_id": "answer_text",
                "quote": "Read this pair in order: carbon dioxide; light energy.",
            },
        ]
        return value

    script = Script([first, jointly_revealing, procedural(), pending_checker])
    out = GenerationService(script).generate(
        hint_request(arm, teaching_condition="T1", teaching_context=context), RequestBudget()
    )
    assert out.succeeded, out.error
    assert len(script.calls) == 4
    assert (
        "PENDING_CUMULATIVE_TARGET_DISCLOSED"
        in out.checks[0]["pending_action_assessment"]["semantic_defect_codes"]
    )
    assert out.checks[0]["judgment"]["cumulative_ok"] is True
    assert all(
        row["target_withheld"]
        for row in out.checks[0]["pending_action_assessment"]["judgment"]["surfaces"]
    )
    assert out.response["answer_text"] == procedural()["answer_text"]
    assert (
        out.checks[0]["pending_action_context"]["prior_exposure"]
        == out.checks[1]["pending_action_context"]["prior_exposure"]
    )


@pytest.mark.parametrize(
    "defect", ["stale_history_hash", "invented_prior_quote", "missing_negative_quote"]
)
def test_stale_history_and_invalid_cumulative_provenance_fail_checker_contract(defect):
    context = {
        **PENDING,
        "delivered_turns": [{"answer_text": "A retained earlier clue.", "citation_views": []}],
    }

    def invalid(messages):
        value = pending_checker(messages)
        action = value["pending_action"]
        current = data_from(messages)["PENDING_ACTION_CONTEXT"]
        if defect == "stale_history_hash":
            old = {key: data for key, data in current.items() if key != "context_sha256"}
            old["prior_exposure"] = {"delivered_turns": [], "disclosure_events": []}
            action["context_sha256"] = hashlib.sha256(
                pending_action_v8.canonical(old).encode()
            ).hexdigest()
        else:
            action["cumulative_scope_ok"] = False
            action["cumulative_quotes"] = (
                []
                if defect == "missing_negative_quote"
                else [{"surface_id": "prior_exposure", "quote": "Invented historical quotation."}]
            )
        return value

    script = Script([procedural(), invalid, invalid])
    out = GenerationService(script).generate(
        hint_request("A", teaching_condition="T1", teaching_context=context), RequestBudget()
    )
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert len(script.calls) == 3 and not out.delivered_projection


@pytest.mark.parametrize("clarify", [False, True])
def test_programmatic_empty_source_and_ambiguity_remain_zero_call_with_original_policy_markers(
    clarify,
):
    prepared = {"intent": "factual", "needs_clarification": False}
    if clarify:
        prepared = {
            "preparation_version": "conversation_preparer_v21",
            "intent": "clarification",
            "needs_clarification": True,
            "fallback_reason": "missing_referent",
        }
    request = hint_request(evidence=[], source_map={}, prepared_query=prepared)
    original = deepcopy(request.generation_policy)
    script = Script([])
    out = GenerationService(script).generate(request, RequestBudget())
    assert out.succeeded, out.error
    assert script.calls == [] and out.budget["consumed_calls"] == 0
    assert out.response["response_type"] == ("clarification" if clarify else "refusal")
    assert out.response_origin == (
        "programmatic_ambiguity_clarification" if clarify else "programmatic_no_evidence"
    )
    assert out.attribution["check_state"] == "not_applicable_programmatic"
    marker = out.token_budget["pending_action_programmatic"]
    assert marker["original_generation_policy"] == request.generation_policy == original
    assert (
        marker["original_joint_checker_policy"]
        == request.joint_checker_policy
        == pending_action_v8.POLICY
    )
    assert marker["original_pending_question"] == PENDING["pending_tutor_question"]
    assert marker["generated_hint_bypass"] is False
    assert out.checks == []


def test_malformed_pending_judgment_correction_names_the_actual_schema_and_keeps_draft_unchanged():
    def missing(messages):
        value = pending_checker(messages)
        value.pop("pending_action")
        return value

    script = Script([procedural(), missing, pending_checker])
    out = GenerationService(script).generate(hint_request(), RequestBudget())
    assert out.succeeded, out.error
    assert len(script.calls) == 3
    assert out.attempts[-1]["stage"] == "checker_contract_repair"
    assert (
        "Return the complete joint_check_pending_action_v8 schema"
        in script.calls[-1][0][-1]["content"]
    )
    assert script.calls[-1][1]["response_schema_name"] == pending_action_v8.SCHEMA
    assert out.checks[0]["projection_hash"] == out.checks[1]["projection_hash"]
    assert out.response["answer_text"] == procedural()["answer_text"]


def test_unresolved_ambiguity_without_a_known_preparer_never_falls_through_to_provider():
    script = Script([])
    out = GenerationService(script).generate(
        hint_request(prepared_query={"intent": "clarification", "needs_clarification": True}),
        RequestBudget(),
    )
    assert out.succeeded, out.error
    assert out.response["response_type"] == "clarification"
    assert out.response_origin == "programmatic_ambiguity_clarification"
    assert script.calls == [] and out.budget["consumed_calls"] == 0


def test_internal_programmatic_only_flag_cannot_create_a_generated_hint_bypass():
    script = Script([])
    out = GenerationService(script).generate(req(), RequestBudget(), programmatic_only=True)
    assert out.response is None and out.error["code"] == "PROGRAMMATIC_STATE_INVALID"
    assert script.calls == [] and out.budget["consumed_calls"] == 0
