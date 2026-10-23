"""Fixed teaching regressions with authored checker receipts, not quality scores."""

import json

import pytest

from generation import GenerationService, RequestBudget
from generation.adapters import chat_value
from generation.reliability import checker_inconsistencies
from test_enhancement_generation import Script, answer, request


def req(**values):
    return request(reliability_policy="evidence_reliability_v3", **values)


def hint(**values):
    return req(teaching_context={"teaching_mode": "hint", "help_level": 1, **values})


def guide(text="Identify one useful comparison dimension before filling its values.", **fields):
    return {**chat_value("answer", text), **fields}


def check(messages, *, basis=None, **updates):
    data = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
    general = data["answer_mode"] == "general_knowledge"
    claims = []
    for item in data["CLAIMS"]:
        chosen = basis or (
            "general_knowledge" if general else "textbook" if item["evidence_ids"] else "nonfactual"
        )
        claims.append(
            {
                "claim_id": item["claim_id"],
                "factual": chosen not in {"nonfactual", "evidence_limitation"},
                "status": "supported",
                "fragment_ids": [data["SOURCE_FRAGMENTS"][0]["fragment_id"]]
                if chosen == "textbook"
                else [],
                "basis": chosen,
                "problem_quote": None,
                "derivation": None,
                "reason": "Authored contract verdict; no measured semantic accuracy.",
            }
        )
    return {
        "claims": claims,
        "body_ok": True,
        "specific_help": True,
        "scope_ok": True,
        "suggestions_ok": True,
        "evidence_display_ok": True,
        "cumulative_ok": True,
        "complete_answer": True,
        "coverage": "full",
        "missing_facets": [],
        "limitations_explicit": False,
        "reason": "Authored checker result.",
        "repair_fragment_ids": [],
        "attempt_evaluation_ok": True,
        "tutor_question_ok": True,
        **updates,
    }


def run(values, request_value=None, max_calls=4):
    return GenerationService(Script(values)).generate(
        request_value or hint(), RequestBudget(max_calls=max_calls)
    )


def test_pure_textbook_guidance_is_checked_then_published_without_sources():
    out = run([guide(), check])
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 2
    assert not out.response["citations"] and not out.delivered_projection["citation_views"]
    assert out.attribution["claims"][0]["support"]["basis"] == "nonfactual"
    assert out.checks[0]["accepted"]
    assert all(a["reliability_policy"] == "evidence_reliability_v3" for a in out.attempts)


def test_uncited_science_cannot_use_guidance_parser_admission_to_skip_check():
    out = run(
        [
            guide("Remember that photosynthesis uses light energy."),
            lambda m: check(m, basis="textbook"),
        ],
        max_calls=2,
    )
    assert not out.succeeded and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.response is None and not out.delivered_projection
    assert out.checks[0]["structural_issues"][0]["code"] == "CHECK_CITATION_SOURCE_MISMATCH"


def test_model_response_label_cannot_hide_factual_hint_from_claim_checker():
    draft = guide("Since photosynthesis uses light energy, which stage would you inspect?")
    draft["response_type"] = "clarification"
    out = run([draft, lambda m: check(m, basis="textbook")], max_calls=2)
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.checks[0]["judgment"]["claims"]


@pytest.mark.parametrize(
    "field",
    [
        "body_ok",
        "specific_help",
        "scope_ok",
        "evidence_display_ok",
        "cumulative_ok",
        "suggestions_ok",
    ],
)
def test_all_enabled_hint_controls_still_gate_uncited_guidance(field):
    out = run([guide(), lambda m: check(m, **{field: False})], max_calls=2)
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED" and not out.response


def test_correct_fact_with_answer_revealing_visible_source_is_rejected():
    out = run([answer(), lambda m: check(m, evidence_display_ok=False)], max_calls=2)
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.drafts[0]["projection"]["citation_views"]


def test_full_textbook_answer_retains_citations_and_exact_support():
    out = run([answer(), check], req())
    assert out.succeeded and out.response["citations"] == ["ev_001"]
    assert out.attribution["claims"][0]["support"]["status"] == "supported"


def test_direct_and_unchecked_hints_cannot_waive_missing_citations():
    for value in [
        req(),
        req(teaching_condition="T0", teaching_context={"teaching_mode": "hint", "help_level": 1}),
    ]:
        out = run([guide(), guide()], value, max_calls=2)
        assert out.error["code"] == "MISSING_CITATIONS" and not out.response


@pytest.mark.parametrize("teaching_mode", ["direct", "hint"])
def test_general_knowledge_fact_has_separate_factual_status_and_no_textbook_support(teaching_mode):
    value = req(
        answer_mode="general_knowledge",
        evidence=[],
        source_map={},
        teaching_context={
            "teaching_mode": teaching_mode,
            "help_level": 1 if teaching_mode == "hint" else 0,
        },
    )
    out = run([guide("General knowledge: diffusion involves particle movement."), check], value)
    assert out.succeeded, out.error
    support = out.attribution["claims"][0]["support"]
    assert support["basis"] == "general_knowledge" and support["status"] is None
    assert support["general_knowledge_status"] == "supported"
    assert support["check_state"] == "general_knowledge_model_checked"
    assert not out.response["citations"] and not out.delivered_projection["citation_views"]


def test_general_hint_incorrect_factual_status_is_not_accepted():
    def wrong(messages):
        result = check(messages, body_ok=False)
        result["claims"][0]["status"] = "unsupported"
        return result

    value = req(
        answer_mode="general_knowledge",
        evidence=[],
        source_map={},
        teaching_context={"teaching_mode": "hint", "help_level": 2},
    )
    out = run([guide("General knowledge: incorrect fixture assertion."), wrong], value, max_calls=2)
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"


def test_general_checker_cannot_assign_textbook_or_nonfactual_basis_to_a_fact():
    base = {
        "claims": [
            {
                "claim_id": "c1",
                "factual": True,
                "status": "supported",
                "basis": "textbook",
                "fragment_ids": [],
                "derivation": None,
            }
        ],
        "body_ok": True,
        "coverage": "full",
        "missing_facets": [],
        "complete_answer": True,
        "limitations_explicit": True,
    }
    issues = checker_inconsistencies(base, answer_mode="general_knowledge")
    assert "GENERAL_KNOWLEDGE_TEXTBOOK_CERTIFICATION" in {i["code"] for i in issues}
    base["claims"][0]["basis"] = "nonfactual"
    assert "FACTUAL_NONFACTUAL_CONTRADICTION" in {
        i["code"] for i in checker_inconsistencies(base, answer_mode="general_knowledge")
    }
    base["claims"][0]["basis"] = "general_knowledge"
    assert not checker_inconsistencies(base, answer_mode="general_knowledge")
    assert (
        checker_inconsistencies(base, answer_mode="textbook")[0]["code"]
        == "GENERAL_KNOWLEDGE_BASIS_INVALID"
    )


def test_contract_repair_only_changes_judgment_and_is_timed_once():
    def inconsistent(messages):
        value = check(messages)
        value["claims"][0]["fragment_ids"] = []
        return value

    adapter = Script([answer(), inconsistent, check])
    original = adapter.generate

    def timed(*args, **kwargs):
        result = original(*args, **kwargs)
        result.latency_ms = [11, 17, 23][len(adapter.calls) - 1]
        return result

    adapter.generate = timed
    out = GenerationService(adapter).generate(req())
    assert out.succeeded and len(out.drafts) == 1
    assert out.checks[0]["projection_hash"] == out.checks[1]["projection_hash"]
    assert out.timing["generation_ms"] == 11
    assert out.timing["checking_ms"] == 40 and out.timing["model_total_ms"] == 51
    assert out.attempts[-1]["stage"] == "checker_contract_repair"


def test_checked_tutor_question_is_exact_visible_metadata_without_public_schema_change():
    question = "Which comparison dimension would you examine first?"
    out = run(
        [
            guide(
                question, tutor_question={"question": question, "expected_response_kind": "concept"}
            ),
            check,
        ]
    )
    assert out.succeeded
    assert out.teaching_context["tutor_question"]["question"] == question
    assert "tutor_question" not in out.response


def test_model_question_is_materialized_before_check_with_exact_raw_draft_retained():
    value = guide(
        tutor_question={
            "question": "Which dimension would you examine next?",
            "expected_response_kind": "concept",
        }
    )
    out = run([value, check], max_calls=2)
    assert out.succeeded and out.budget["consumed_calls"] == 2
    assert json.loads(out.drafts[0]["raw_model_output"]) == value
    assert out.drafts[0]["precheck_transformations"][0]["requires_full_check"]
    assert out.response["answer_text"].endswith(value["tutor_question"]["question"])
    assert out.delivered_projection["response"] == out.response


def test_materialized_question_cannot_disclose_the_protected_solution():
    value = guide(
        tutor_question={
            "question": "Since the final solution is already stated here, can you repeat it?",
            "expected_response_kind": "concept",
        }
    )
    out = run([value, lambda m: check(m, scope_ok=False, cumulative_ok=False)], max_calls=2)
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED" and not out.response
    assert out.drafts[0]["response"]["answer_text"].endswith(value["tutor_question"]["question"])


def test_missing_actionable_question_metadata_requires_bounded_answer_repair():
    question = "Which comparison dimension would you examine next?"
    draft = guide(question)
    repaired = {
        **draft,
        "tutor_question": {"question": question, "expected_response_kind": "concept"},
    }
    out = run([draft, lambda m: check(m, tutor_question_ok=False), repaired, check])
    assert out.succeeded and out.budget["consumed_calls"] == 4
    assert out.checks[0]["accepted"] is False and out.checks[1]["accepted"] is True
    assert any(a["code"] == "tutor_question_ok" for a in out.checks[0]["repair_plan"]["actions"])
    assert out.teaching_context["tutor_question"]["question"] == question


def test_unchecked_condition_cannot_materialize_an_unchecked_question():
    draft = answer()
    draft["tutor_question"] = {
        "question": "Which condition applies?",
        "expected_response_kind": "concept",
    }
    out = run(
        [draft, draft],
        req(teaching_condition="T0", teaching_context={"teaching_mode": "hint", "help_level": 1}),
        max_calls=2,
    )
    assert out.error["code"] == "TUTOR_QUESTION_NOT_VISIBLE" and not out.response


def test_factual_assertion_in_attempt_feedback_cannot_be_smuggled_as_guidance():
    value = hint(
        turn_role="learner_attempt",
        pending_tutor_question="Which process?",
        current_problem="Explain photosynthesis.",
    )
    draft = guide(
        "Correct: photosynthesis creates energy.",
        learner_attempt_evaluation={
            "status": "correct",
            "feedback": "Correct: photosynthesis creates energy.",
        },
    )
    out = run(
        [draft, lambda m: check(m, basis="textbook", body_ok=False, attempt_evaluation_ok=False)],
        value,
        max_calls=2,
    )
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED" and not out.response


def test_learner_attempt_feedback_must_be_visible_and_independently_accepted():
    value = hint(
        turn_role="learner_attempt",
        pending_tutor_question="Which process specifically involves water?",
        current_problem="Compare diffusion and osmosis.",
    )
    value.question = "Osmosis."
    draft = guide(
        "That identifies the requested process. What comparison dimension would you examine next?",
        learner_attempt_evaluation={
            "status": "correct",
            "feedback": "That identifies the requested process.",
        },
        tutor_question={
            "question": "What comparison dimension would you examine next?",
            "expected_response_kind": "explanation",
        },
    )
    out = run([draft, check], value)
    assert out.succeeded and out.teaching_context["help_level"] == 1
    assert out.teaching_context["learner_attempt_evaluation"]["status"] == "correct"
    failed = run([draft, lambda m: check(m, attempt_evaluation_ok=False)], value, max_calls=2)
    assert failed.error["code"] == "SEMANTIC_CHECK_FAILED" and not failed.response
    assert any(
        action["code"] == "attempt_evaluation_ok"
        for action in failed.checks[0]["repair_plan"]["actions"]
    )


def test_missing_learner_attempt_evaluation_is_not_ordinary_new_question():
    value = hint(
        turn_role="learner_attempt",
        pending_tutor_question="Which process?",
        current_problem="Compare the processes.",
    )
    out = run([guide(), guide()], value, max_calls=2)
    assert out.error["code"] == "ATTEMPT_FEEDBACK_INVALID"


def test_stable_policy_prefix_preserves_dynamic_context_in_separate_message():
    one, two = Script([guide(), check]), Script([guide(), check])
    GenerationService(one).generate(hint())
    other = hint()
    other.question = "Explain a different aspect of photosynthesis."
    GenerationService(two).generate(other)
    assert one.calls[0][0][0] == two.calls[0][0][0]
    assert one.calls[0][0][-1] != two.calls[0][0][-1]
    assert "CURRENT_EVIDENCE" in one.calls[0][0][1]["content"]


def test_historical_v2_keeps_original_schema_and_frozen_policy():
    from test_generation_reliability_v2 import check as v2_check

    adapter = Script([answer(), v2_check])
    out = GenerationService(adapter).generate(request(reliability_policy="evidence_reliability_v2"))
    assert out.succeeded and out.token_budget["reliability_policy"] == "evidence_reliability_v2"
    assert adapter.calls[1][1]["response_schema_name"] == "joint_check_v2"
