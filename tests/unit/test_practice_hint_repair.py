"""Source support is separate from permission to disclose a practice result.

These authored transport judgments verify policy execution, not hint quality.
"""

import json

import pytest

from generation import GenerationService, RequestBudget
from generation.adapters import chat_value
from generation.joint_policy import policy
from generation.local_repair import (
    PRACTICE_HINT_NEXT_VERSION,
    PRACTICE_HINT_VERSION,
    VERSION,
    practice_teaching_repair_boundary,
)
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer


def practice_request(**updates):
    context = {
        "teaching_mode": "hint",
        "help_level": 2,
        "current_step": 1,
        "current_problem": "What energy input does photosynthesis use?",
        "practice_context": {
            "version": "practice_tutor_context_v1",
            "current_step": 1,
            "prompt": "What energy input does photosynthesis use?",
            "shown_hints": ["Locate the sentence about the energy input."],
            "recent_attempts": [],
            "progress_authority": "saved_practice_attempt",
        },
    }
    values = {
        "repair_policy": PRACTICE_HINT_VERSION,
        "teaching_context": context,
        "teaching_condition": "T2",
    }
    values.update(updates)
    return req(**values)


def leaked_draft():
    question = "Which input is light energy?"
    value = answer(
        "Photosynthesis uses light energy. [ev_001] " + question,
    )
    value["tutor_question"] = {
        "question": question,
        "expected_response_kind": "choice",
    }
    return value


def safe_draft():
    question = "Which sentence states the required input?"
    value = chat_value(
        "answer",
        "Find the sentence about the required input. " + question,
    )
    value["tutor_question"] = {
        "question": question,
        "expected_response_kind": "explanation",
    }
    return value


def test_failed_teaching_gate_releases_facts_and_rewrites_question_then_full_rechecks():
    adapter = Script(
        [
            leaked_draft(),
            lambda m: checker(m, non_repetitive_next_action=False),
            safe_draft(),
            checker,
        ]
    )
    out = GenerationService(adapter).generate(practice_request(), RequestBudget(max_calls=4))
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4 and len(out.checks) == 2
    assert adapter.calls[2][1]["response_schema_name"] == "chat_response_teaching_v5"
    feedback = json.loads(adapter.calls[2][0][-1]["content"].split("REPAIR_DATA_JSON:\n")[1])
    boundary = feedback["teaching_repair_boundary"]
    assert boundary["failed_global_gate_names"] == ["non_repetitive_next_action"]
    assert boundary["previously_source_approved_claim_ids"]
    assert boundary["release_source_supported_claims_for_repair"]
    assert not boundary["publication_override"] and boundary["final_full_check_required"]
    assert feedback["protected_exact_claims"] == []
    assert out.response == {k: v for k, v in safe_draft().items() if k != "tutor_question"}
    assert "Which input is light energy?" not in out.response["answer_text"]
    assert out.teaching_context["tutor_question"] == safe_draft()["tutor_question"]
    assert out.delivered_projection["citation_views"] == []
    assert "LINKED PRACTICE HINT V1" in adapter.calls[0][0][0]["content"]
    assert "including an updated tutor_question" in adapter.calls[2][0][-1]["content"]


def test_repaired_fact_support_cannot_override_final_disclosure_failure():
    adapter = Script(
        [
            leaked_draft(),
            lambda m: checker(m, non_repetitive_next_action=False),
            leaked_draft(),
            lambda m: checker(m, scope_ok=False, cumulative_ok=False),
        ]
    )
    out = GenerationService(adapter).generate(practice_request(), RequestBudget(max_calls=4))
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 4 and len(out.checks) == 2
    assert out.delivered_projection == {}


def test_existing_null_summary_gate_allows_full_repair_without_a_support_override():
    original = leaked_draft()
    original["short_answer"] = "Photosynthesis uses light energy. [ev_001]"
    adapter = Script([original, checker, safe_draft(), checker])
    out = GenerationService(adapter).generate(practice_request(), RequestBudget(max_calls=4))
    assert out.succeeded, out.error
    boundary = out.token_budget["teaching_repair_boundaries"][0]
    assert boundary["failed_global_gate_names"] == []
    assert boundary["failed_surface_gate_names"] == ["HINT_SHORT_ANSWER_PRESENT"]
    assert out.response["short_answer"] is None
    assert adapter.calls[2][1]["response_schema_name"] == "chat_response_teaching_v5"
    assert out.budget["consumed_calls"] == 4 and len(out.checks) == 2


def test_saved_v3_policy_keeps_factual_protection_and_does_not_gain_practice_prompt():
    def unchanged_patch(messages):
        feedback = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[1])
        assert feedback["protected_exact_claims"]
        assert "teaching_repair_boundary" not in feedback
        kept = {row["claim_id"] for row in feedback["protected_exact_claims"]}
        return {
            "edits": [
                {"claim_id": row["claim_id"], "replacement_text": row["text"]}
                for row in feedback["original_claims"]
                if row["claim_id"] not in kept
            ],
            "append_answer_text": "",
        }

    adapter = Script(
        [
            leaked_draft(),
            lambda m: checker(m, non_repetitive_next_action=False),
            unchanged_patch,
            lambda m: checker(m, non_repetitive_next_action=False),
        ]
    )
    out = GenerationService(adapter).generate(
        practice_request(repair_policy=VERSION), RequestBudget(max_calls=4)
    )
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert "LINKED PRACTICE HINT V1" not in adapter.calls[0][0][0]["content"]
    assert out.drafts[1]["response"]["answer_text"] == leaked_draft()["answer_text"]


@pytest.mark.parametrize(
    "context", [{"teaching_mode": "direct"}, {"teaching_mode": "hint", "help_level": 1}]
)
def test_new_policy_requires_a_linked_practice_hint(context):
    adapter = Script([])
    out = GenerationService(adapter).generate(practice_request(teaching_context=context))
    assert out.response is None and out.error["code"] == "ENHANCEMENT_VALIDATION_ERROR"
    assert "PRACTICE_HINT_POLICY_CONTEXT_REQUIRED" in str(out.error["details"])
    assert adapter.calls == []


@pytest.mark.parametrize(
    "gate",
    [
        "specific_help",
        "scope_ok",
        "attempt_evaluation_ok",
        "tutor_question_ok",
        "non_repetitive_next_action",
        "suggestions_ok",
        "evidence_display_ok",
        "cumulative_ok",
    ],
)
def test_each_active_global_teaching_failure_releases_only_for_fresh_final_check(gate):
    gates = {
        name: True
        for name in (
            "specific_help",
            "scope_ok",
            "attempt_evaluation_ok",
            "tutor_question_ok",
            "non_repetitive_next_action",
            "suggestions_ok",
            "evidence_display_ok",
            "cumulative_ok",
        )
    }
    gates[gate] = False
    boundary = practice_teaching_repair_boundary(gates, policy("T2", {"teaching_mode": "hint"}))
    assert boundary["failed_global_gate_names"] == [gate]
    assert boundary["release_source_supported_claims_for_repair"]
    assert boundary["per_claim_teaching_safe_binding_available"] is False
    assert boundary["final_full_check_required"] and not boundary["publication_override"]


def test_disabled_display_gates_do_not_release_claims_in_a_body_only_condition():
    gates = dict.fromkeys(
        [
            "specific_help",
            "scope_ok",
            "attempt_evaluation_ok",
            "tutor_question_ok",
            "non_repetitive_next_action",
        ],
        True,
    )
    gates.update(suggestions_ok=False, evidence_display_ok=False, cumulative_ok=False)
    boundary = practice_teaching_repair_boundary(gates, policy("T1", {"teaching_mode": "hint"}))
    assert boundary["failed_global_gate_names"] == []
    assert not boundary["release_source_supported_claims_for_repair"]


@pytest.mark.parametrize("repair_policy", [PRACTICE_HINT_VERSION, PRACTICE_HINT_NEXT_VERSION])
def test_source_only_defect_keeps_approved_byte_spans_under_new_policy(repair_policy):
    initial = answer(
        "Photosynthesis uses light energy. [ev_001] Plants create matter from nothing. [ev_001]"
    )

    def rejected(messages):
        value = checker(messages, body_ok=False)
        value["claims"][1]["status"] = "unsupported"
        return value

    def patch(messages):
        feedback = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[1])
        assert not feedback["teaching_repair_boundary"][
            "release_source_supported_claims_for_repair"
        ]
        kept = {row["claim_id"] for row in feedback["protected_exact_claims"]}
        return {
            "edits": [
                {
                    "claim_id": row["claim_id"],
                    "replacement_text": "Carbon dioxide supplies carbon for sugar. [ev_001]",
                }
                for row in feedback["original_claims"]
                if row["claim_id"] not in kept
            ],
            "append_answer_text": "",
        }

    adapter = Script([initial, rejected, patch, checker])
    out = GenerationService(adapter).generate(
        practice_request(repair_policy=repair_policy), RequestBudget(max_calls=4)
    )
    assert out.succeeded, out.error
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert out.response["answer_text"].startswith("Photosynthesis uses light energy. [ev_001]")


def test_v5_hint_first_prompt_and_full_pedagogical_repair_replace_leaked_result():
    adapter = Script(
        [
            leaked_draft(),
            lambda m: checker(m, non_repetitive_next_action=False),
            safe_draft(),
            checker,
        ]
    )
    out = GenerationService(adapter).generate(
        practice_request(repair_policy=PRACTICE_HINT_NEXT_VERSION), RequestBudget(max_calls=4)
    )
    assert out.succeeded, out.error
    initial_prompt = adapter.calls[0][0][0]["content"]
    assert "LINKED PRACTICE HINT V2" in initial_prompt
    assert "LOCAL CLAIM BINDING V1" not in initial_prompt
    assert "LINKED PRACTICE HINT V1" not in initial_prompt
    repair_prompt = adapter.calls[2][0][-1]["content"]
    assert repair_prompt.startswith("PRACTICE PEDAGOGICAL REPAIR V1")
    assert "Return one complete chat_response_v1" not in repair_prompt
    assert "including an updated tutor_question" not in repair_prompt
    assert adapter.calls[2][1]["response_schema_name"] == "chat_response_teaching_v5"
    assert "light energy" not in out.response["answer_text"]
    assert out.teaching_context["tutor_question"] == safe_draft()["tutor_question"]
    assert out.budget["consumed_calls"] == 4 and len(out.checks) == 2


def test_v4_saved_hint_keeps_original_generation_and_repair_instruction():
    adapter = Script(
        [
            leaked_draft(),
            lambda m: checker(m, non_repetitive_next_action=False),
            safe_draft(),
            checker,
        ]
    )
    out = GenerationService(adapter).generate(practice_request(), RequestBudget(max_calls=4))
    assert out.succeeded, out.error
    assert "LOCAL CLAIM BINDING V1" in adapter.calls[0][0][0]["content"]
    assert "LINKED PRACTICE HINT V1" in adapter.calls[0][0][0]["content"]
    assert "LINKED PRACTICE HINT V2" not in adapter.calls[0][0][0]["content"]
    assert not adapter.calls[2][0][-1]["content"].startswith("PRACTICE PEDAGOGICAL REPAIR V1")


def test_v5_full_repair_cannot_publish_another_leaked_result():
    adapter = Script(
        [
            leaked_draft(),
            lambda m: checker(m, non_repetitive_next_action=False),
            leaked_draft(),
            lambda m: checker(m, non_repetitive_next_action=False),
        ]
    )
    out = GenerationService(adapter).generate(
        practice_request(repair_policy=PRACTICE_HINT_NEXT_VERSION), RequestBudget(max_calls=4)
    )
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 4 and len(out.checks) == 2
