"""Actual-citation and provider boundary regressions; authored judgments only."""

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from generation import GenerationService, RequestBudget
from generation.adapters import chat_value
from generation.reliability_v4 import (
    ReliableCheckV4,
    TeachingDraftV4,
    compact_schema,
    normalize_judgment,
    unchanged_claims,
    coverage_context,
)
from generation.teaching_plan import freeze_generation_policy
from generation.types import ProviderResult, failure
from generation.providers import decode_response
from test_enhancement_generation import Script, answer, request


def req(**values):
    return request(reliability_policy="evidence_reliability_v4", **values)


def hint(**values):
    return req(teaching_context={"teaching_mode": "hint", "help_level": 1, **values})


def check(messages, **updates):
    data = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
    bindings = {b["claim_id"]: b["citations"] for b in data["ACTUAL_CITATION_BINDINGS"]}
    claims = []
    for c in data["CLAIMS"]:
        value = {"claim_id": c["claim_id"], "reason": "Authored contract judgment."}
        if data["answer_mode"] == "general_knowledge":
            value.update(basis="general_knowledge", status="supported")
        elif c["evidence_ids"]:
            value.update(
                basis="textbook",
                status="supported",
                citations=[
                    {
                        "evidence_id": b["evidence_id"],
                        "fragment_ids": b["allowed_fragment_ids"][:1],
                        "relation": "supporting",
                    }
                    for b in bindings[c["claim_id"]]
                ],
            )
        else:
            value.update(basis="nonfactual")
        claims.append(value)
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
        "limitations_explicit": True,
        "reason": "Authored compatibility receipt.",
        "repair_fragment_ids": [],
        "attempt_evaluation_ok": True,
        "tutor_question_ok": True,
        **updates,
    }


def run(values, value=None, max_calls=4):
    return GenerationService(Script(values)).generate(
        value or req(), RequestBudget(max_calls=max_calls)
    )


def test_direct_full_answer_uses_typed_actual_citations_and_immutable_projection():
    out = run([answer(), check])
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 2
    assert out.checks[0]["actual_citation_bindings"][0]["citations"][0]["evidence_id"] == "ev_001"
    assert "factual" not in out.checks[0]["typed_judgment_raw_aliases"]["claims"][0]
    assert out.attribution["claims"][0]["support"]["factual"] is True
    assert out.attribution["claims"][0]["support"]["human_rating"] is None


@pytest.mark.parametrize("mode", ["direct", "hint"])
def test_general_knowledge_never_receives_textbook_certification(mode):
    out = run(
        [chat_value("answer", "General knowledge: particles move."), check],
        req(
            answer_mode="general_knowledge",
            evidence=[],
            source_map={},
            teaching_context={"teaching_mode": mode, "help_level": 1},
        ),
    )
    assert out.succeeded, out.error
    support = out.attribution["claims"][0]["support"]
    assert support["status"] is None and support["general_knowledge_status"] == "supported"
    assert not out.delivered_projection["citation_views"]


def test_citation_free_guidance_requires_independent_classification():
    out = run([chat_value("answer", "Identify the requested quantity."), check], hint())
    assert out.succeeded and out.attribution["claims"][0]["support"]["basis"] == "nonfactual"


def test_hidden_science_in_uncited_guidance_cannot_skip_independent_support():
    def factual(messages):
        value = check(messages, body_ok=False)
        value["claims"][0] = {
            "claim_id": value["claims"][0]["claim_id"],
            "basis": "textbook",
            "status": "unsupported",
            "citations": [],
            "reason": "Science needs actual sources.",
        }
        return value

    out = run(
        [chat_value("answer", "Photosynthesis uses light energy."), factual], hint(), max_calls=2
    )
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"


def test_missing_draft_citation_routes_to_answer_repair_and_retains_final_gate():
    def factual(messages):
        value = check(messages)
        value["claims"][0] = {
            "claim_id": value["claims"][0]["claim_id"],
            "basis": "textbook",
            "status": "supported",
            "citations": [],
            "reason": "The fact is correct but its draft has no actual citation.",
        }
        return value

    uncited = chat_value("answer", "Photosynthesis uses light energy.")
    rejected = run([uncited, factual], hint(), max_calls=2)
    assert rejected.error["code"] == "SEMANTIC_CHECK_FAILED" and rejected.response is None
    out = run([uncited, factual, answer(), check], hint())
    assert out.succeeded, out.error
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.checks[0]["structural_issues"][0]["code"] == "CHECK_SUPPORT_WITHOUT_SOURCE"
    assert out.response["citations"] == ["ev_001"]


def test_optimistic_aggregate_with_unsupported_claim_never_publishes_and_keeps_raw():
    def contradictory(messages):
        value = check(messages)
        value["claims"][0]["status"] = "unsupported"
        return value

    blocked = run([answer(), contradictory], max_calls=2)
    assert blocked.error["code"] == "SEMANTIC_CHECK_FAILED" and blocked.response is None
    receipt = blocked.checks[0]
    assert receipt["typed_judgment_raw_aliases"]["body_ok"] is True
    assert receipt["judgment"]["body_ok"] is True and receipt["effective_body_ok"] is False
    assert receipt["repairable_verdict_inconsistencies"][0]["code"] == "BODY_SUPPORT_CONTRADICTION"
    assert not receipt["accepted"]


def test_aggregate_conflict_uses_one_bounded_draft_repair_and_exact_final_check():
    def contradictory(messages):
        value = check(messages)
        value["claims"][0]["status"] = "partial"
        return value

    corrected = answer("Photosynthesis uses light energy. [ev_001]")
    out = run([answer("Photosynthesis uses energy. [ev_001]"), contradictory, corrected, check])
    assert out.succeeded, out.error
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.budget["consumed_calls"] == 4 and len(out.drafts) == 2
    assert out.checks[-1]["effective_body_ok"] is True
    blocked = run([corrected, contradictory, corrected, contradictory])
    assert blocked.error["code"] == "SEMANTIC_CHECK_FAILED" and blocked.response is None
    assert blocked.budget["consumed_calls"] == 4


def test_wrong_source_hash_does_not_publish_a_supported_receipt():
    value = req()
    value.source_map["c1"]["chunk_hash"] = "0" * 64
    out = run([answer(), check], value)
    assert not out.succeeded and not out.delivered_projection


@pytest.mark.parametrize(
    "gate",
    [
        "body_ok",
        "scope_ok",
        "evidence_display_ok",
        "cumulative_ok",
        "tutor_question_ok",
        "attempt_evaluation_ok",
    ],
)
def test_teaching_gates_keep_rejecting_unsafe_guidance(gate):
    out = run(
        [chat_value("answer", "Identify a quantity."), lambda m: check(m, **{gate: False})],
        hint(),
        max_calls=2,
    )
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED" and out.response is None


def typed_claim(basis="textbook", **updates):
    value = {"claim_id": "c", "basis": basis, "reason": "Authored."}
    if basis == "textbook":
        value.update(
            status="supported",
            citations=[{"evidence_id": "ev_001", "fragment_ids": ["F1"], "relation": "supporting"}],
        )
    return {**value, **updates}


def shell(claim):
    return {
        "claims": [claim],
        "body_ok": True,
        "specific_help": True,
        "scope_ok": True,
        "suggestions_ok": True,
        "evidence_display_ok": True,
        "cumulative_ok": True,
        "complete_answer": True,
        "coverage": "full",
        "missing_facets": [],
        "limitations_explicit": True,
        "reason": "Authored.",
        "repair_fragment_ids": [],
        "attempt_evaluation_ok": True,
        "tutor_question_ok": True,
    }


@pytest.mark.parametrize(
    "claim",
    [
        typed_claim(factual=False),
        typed_claim(problem_quote="x"),
        typed_claim("nonfactual", status="supported"),
        typed_claim("general_knowledge", status="supported", citations=[]),
    ],
)
def test_typed_variants_forbid_contradictory_or_inapplicable_fields(claim):
    with pytest.raises(ValidationError):
        ReliableCheckV4.model_validate(shell(claim))


def test_actual_complementary_sources_need_not_match_a_preferred_subset():
    claim = typed_claim()
    claim["citations"].append(
        {"evidence_id": "ev_002", "fragment_ids": ["F2"], "relation": "supporting"}
    )
    bindings = [
        {
            "claim_id": "c",
            "citations": [
                {"evidence_id": "ev_001", "allowed_fragment_ids": ["F1", "F3"]},
                {"evidence_id": "ev_002", "allowed_fragment_ids": ["F2"]},
            ],
        }
    ]
    normalized, issues = normalize_judgment(shell(claim), bindings)
    assert not issues and normalized["claims"][0]["fragment_ids"] == ["F1", "F2"]
    claim["citations"][0]["fragment_ids"] = ["F3"]
    assert not normalize_judgment(shell(claim), bindings)[1]


@pytest.mark.parametrize("relation", ["irrelevant", "contradictory"])
def test_every_actual_citation_must_contribute_without_contradiction(relation):
    def wrong(messages):
        value = check(messages)
        value["claims"][0]["citations"][0]["relation"] = relation
        return value

    out = run([answer(), wrong], max_calls=2)
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.checks[0]["structural_issues"][0]["code"] == "ACTUAL_CITATION_" + relation.upper()


def test_cross_evidence_fragment_swap_is_rejected():
    bindings = [
        {"claim_id": "c", "citations": [{"evidence_id": "ev_001", "allowed_fragment_ids": ["F2"]}]}
    ]
    assert (
        normalize_judgment(shell(typed_claim()), bindings)[1][0]["code"]
        == "ACTUAL_CITATION_FRAGMENT_INVALID"
    )


@pytest.mark.parametrize(
    "arm,content,display",
    [("A", False, False), ("B", True, False), ("C", False, True), ("D", True, True)],
)
def test_factorial_plan_context_and_display_are_independent(arm, content, display):
    adapter = Script([answer(), check])
    value = hint()
    value.generation_policy = freeze_generation_policy(arm)
    out = GenerationService(adapter).generate(value)
    assert out.succeeded, out.error
    for messages, _ in adapter.calls:
        contexts = [
            json.loads(m["content"].removeprefix("CONTEXT_DATA_JSON:\n"))
            for m in messages
            if m["content"].startswith(("{", "CONTEXT_DATA_JSON:\n"))
        ]
        assert any("TEACHING_ACTION_PLAN" in context for context in contexts) is content
    assert out.token_budget["progress_display"][0]["applied"] is display


def test_ordinary_direct_answer_has_no_hint_plan_for_any_arm():
    adapter = Script([answer(), check])
    assert GenerationService(adapter).generate(req()).succeeded
    for messages, _ in adapter.calls:
        contexts = [
            json.loads(m["content"].removeprefix("CONTEXT_DATA_JSON:\n"))
            for m in messages
            if m["content"].startswith(("{", "CONTEXT_DATA_JSON:\n"))
        ]
        assert not any("TEACHING_ACTION_PLAN" in context for context in contexts)


def test_checker_contract_repair_preserves_draft_and_counts_check_time_once():
    def invalid(messages):
        value = check(messages)
        value["claims"][0]["factual"] = False
        return value

    adapter = Script([answer(), invalid, check])
    original = adapter.generate

    def timed(*args, **kwargs):
        result = original(*args, **kwargs)
        result.latency_ms = [11, 17, 23][len(adapter.calls) - 1]
        return result

    adapter.generate = timed
    out = GenerationService(adapter).generate(req())
    assert out.succeeded, out.error
    assert (
        len(out.drafts) == 1
        and out.checks[0]["projection_hash"] == out.checks[1]["projection_hash"]
    )
    assert out.timing["checking_ms"] == 40 and out.timing["model_total_ms"] == 51


def test_targeted_repair_preserves_accepted_claims_and_rechecks_final_body():
    initial = answer(
        "Photosynthesis uses light energy. [ev_001] Plants create matter from nothing. [ev_001]"
    )
    final = answer(
        "Photosynthesis uses light energy. [ev_001] Carbon dioxide supplies carbon for sugar. [ev_001]"
    )

    def partial(messages):
        value = check(messages, body_ok=False)
        value["claims"][-1]["status"] = "unsupported"
        return value

    out = run([initial, partial, final, check])
    assert out.succeeded, out.error
    assert len(out.drafts) == 2 and len(out.checks) == 2 and out.budget["consumed_calls"] == 4
    assert (
        out.drafts[0]["projection"]["content_hash"] != out.drafts[1]["projection"]["content_hash"]
    )
    assert not unchanged_claims(
        [{"answer_field": "answer_text", "text": "Kept."}], {"answer_text": "Changed."}
    )


def test_repair_that_changes_unaffected_approved_claim_is_blocked_before_recheck():
    initial = answer(
        "Photosynthesis uses light energy. [ev_001] Plants create matter from nothing. [ev_001]"
    )
    changed = answer(
        "Light powers photosynthesis. [ev_001] Carbon dioxide supplies carbon for sugar. [ev_001]"
    )

    def partial(messages):
        value = check(messages, body_ok=False)
        value["claims"][-1]["status"] = "unsupported"
        return value

    out = run([initial, partial, changed])
    assert out.error["code"] == "REPAIR_CHANGED_APPROVED_CONTENT"
    assert out.response is None and out.budget["consumed_calls"] == 3


def empty():
    return ProviderResult(
        raw_text=" \n",
        error=failure("EMPTY_RESPONSE", "Empty fixture.", retryable=True),
        request_submitted=True,
    )


def test_strict_empty_policy_preserves_raw_and_does_not_blind_retry():
    records = []
    out = GenerationService(Script([empty()])).generate(req(), on_attempt=records.append)
    assert out.error["code"] == "EMPTY_RESPONSE" and out.budget["consumed_calls"] == 1
    assert records[-1]["raw_text"] == " \n"


def test_experimental_empty_recovery_uses_one_changed_prompt_and_final_check():
    adapter = Script([empty(), answer(), check])
    out = GenerationService(adapter).generate(req(provider_output_policy="json_example_once_v1"))
    assert out.succeeded, out.error
    assert (
        out.budget["consumed_calls"] == 3 and len(out.token_budget["empty_output_recoveries"]) == 1
    )
    assert adapter.calls[0][0] != adapter.calls[1][0]
    assert adapter.calls[0][1]["response_schema"] == adapter.calls[1][1]["response_schema"]


def test_second_empty_is_terminal_and_recovery_preserves_final_check_allowance():
    out = run([empty(), empty()], req(provider_output_policy="json_example_once_v1"))
    assert out.error["code"] == "EMPTY_RESPONSE" and out.budget["consumed_calls"] == 2
    out = run([empty()], req(provider_output_policy="json_example_once_v1"), max_calls=2)
    assert out.error["code"] == "EMPTY_RESPONSE" and out.budget["consumed_calls"] == 1


def test_empty_recovery_is_shared_across_draft_and_checker_stages():
    out = run([empty(), answer(), empty()], req(provider_output_policy="json_example_once_v1"))
    assert out.error["code"] == "EMPTY_RESPONSE" and out.budget["consumed_calls"] == 3
    assert not out.response and len(out.token_budget["empty_output_recoveries"]) == 1


def test_invalid_provider_content_retention_is_opt_in_for_frozen_legacy_behavior():
    envelope = {"choices": [{"message": {"content": " \n"}, "finish_reason": "stop"}]}
    old, new = ProviderResult(), ProviderResult()
    decode_response(envelope, old)
    decode_response(envelope, new, retain_invalid_output=True)
    assert old.raw_text == "" and new.raw_text == " \n"


def test_compact_schema_retains_constraints_and_mutually_exclusive_basis_variants():
    schema = compact_schema(ReliableCheckV4)
    encoded = json.dumps(schema)
    assert '"oneOf"' not in encoded and '"discriminator"' not in encoded and '"anyOf"' in encoded
    assert '"maxLength": 800' in encoded and '"additionalProperties": false' in encoded
    draft = chat_value("answer", "Identify the requested quantity.")
    assert TeachingDraftV4.model_validate(draft)


def test_coverage_transport_retains_requirements_and_packing_loss_without_source_edits():
    from generation.evidence_coverage import assess_evidence_coverage

    evidence = [
        {"chunk_id": "c", "evidence_id": "ev_001", "text": "DNA structure has two strands."}
    ]
    original = deepcopy(evidence)
    audit = assess_evidence_coverage(
        "Compare DNA and RNA structure.", evidence, selected_evidence=[]
    )
    compact = coverage_context(audit)
    assert evidence == original
    assert compact["budget_lost_requirement_ids"] == audit["budget_lost_requirement_ids"]
    assert {row["id"] for row in compact["requirements"]} == {
        row["id"] for row in audit["packed_coverage"]["requirements"]
    }
    assert all("missing_term_groups" in row for row in compact["requirements"])
    assert compact["semantic_sufficiency"] is None
