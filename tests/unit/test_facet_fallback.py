"""Authored relevance scores verify mechanics, never semantic model quality."""

from copy import deepcopy
import pytest
from conversation.query import prepare_query, LOCAL_QUESTION_VERSION
from conversation.understanding import describe_question
from retrieval.relevance import (
    MODEL,
    REVISION,
    freeze_policy,
    freeze_facet_fallback,
    facet_fallback,
)

POLICY = {"reranker_model": MODEL, "reranker_revision": REVISION, "candidate_count": 20}
PARTIAL = "Explain photosynthesis. Also give tomorrow’s exact Bitcoin price."


def understanding(question):
    return describe_question(question, prepare_query(question).model_dump())


def ranked(row, score=1.0):
    return {
        **row,
        "score": score,
        "score_type": "cross_encoder",
        "reranker_model": MODEL,
        "reranker_revision": REVISION,
    }


def execute(question=PARTIAL, *, accept=True, whole_accepted=None, policy=None, checkpoint=None):
    calls = []
    source = [
        {"chunk_id": str(i), "text": "Photosynthesis captures light energy.", "text_hash": str(i)}
        for i in range(20)
    ]
    before = deepcopy(source)

    def retrieve(query, limit):
        calls.append(("retrieve", query, limit))
        return deepcopy(source[:limit])

    def rerank(query, rows):
        calls.append(("rerank", query, len(rows)))
        return [ranked(row, 1 if accept and "photosynthesis" in query else -10) for row in rows]

    result = facet_fallback(
        understanding(question),
        [ranked(row, -10) for row in source],
        whole_accepted or [],
        policy or freeze_facet_fallback(POLICY),
        POLICY,
        freeze_policy(POLICY),
        retrieve_facet=retrieve,
        rerank_facet=rerank,
        checkpoint=checkpoint or (lambda phase, trace: None),
    )
    assert source == before
    return result, calls


def test_exact_partial_question_uses_actual_facet_scores_and_unique_final_counts():
    (accepted, trace, selection), calls = execute()
    assert len(accepted) == 10
    assert [call[1] for call in calls if call[0] == "retrieve"] == [
        "Explain photosynthesis",
        "Also give tomorrow’s exact Bitcoin price",
    ]
    assert sum(call[2] for call in calls if call[0] == "rerank") == 20
    assert trace["whole_query_candidate_count"] == 20 and trace["whole_query_accepted_count"] == 0
    assert trace["candidate_slots_used"] == 20 and trace["reason"] == "fallback_completed"
    assert [item["accepted_count"] for item in trace["attempted_facets"]] == [10, 0]
    assert selection["candidate_count"] == selection["accepted_count"] == 10
    assert selection["source"] == "facet_fallback"
    assert understanding(PARTIAL)["original_message"] == PARTIAL


def test_both_out_of_scope_facets_remain_empty_and_three_facets_bound_to_two():
    (accepted, trace, selection), calls = execute(
        "Give tomorrow’s Bitcoin price. Also write a deployment workflow. Then predict the lottery.",
        accept=False,
    )
    assert not accepted and selection["accepted_count"] == 0
    assert len(trace["attempted_facets"]) == 2
    assert len(calls) == 4 and sum(call[2] for call in calls if call[0] == "rerank") == 20
    assert (
        len(
            understanding(
                "Give tomorrow’s Bitcoin price. Also write a deployment workflow. Then predict the lottery."
            )["requested_facets"]
        )
        == 3
    )


@pytest.mark.parametrize(
    "question",
    ["Compare DNA and RNA.", "Explain photosynthesis.", "What is it? Also explain that process."],
)
def test_no_fallback_for_single_question_synthetic_operands_or_ambiguous_generic_parts(question):
    (_, trace, _), calls = execute(question)
    assert not trace["triggered"] and not calls


def test_whole_question_success_skips_fallback_and_policy_tampering_fails():
    (_, trace, _), calls = execute(whole_accepted=[ranked({"chunk_id": "yes", "text": "source"})])
    assert trace["reason"] == "whole_query_accepted" and not calls
    with pytest.raises(ValueError, match="frozen facet"):
        execute(policy={**freeze_facet_fallback(POLICY), "candidate_slots": 40})


def test_budget_checkpoint_stops_before_second_local_call_and_never_retries():
    phases = []

    def checkpoint(phase, trace):
        phases.append(phase)
        if phase == "reranking":
            raise TimeoutError("shared active budget exhausted")

    with pytest.raises(TimeoutError):
        execute(checkpoint=checkpoint)
    assert phases == ["retrieving", "reranking"]


def test_facet_score_requires_the_exact_frozen_model_revision():
    with pytest.raises(ValueError, match="pinned learned reranker"):
        facet_fallback(
            understanding(PARTIAL),
            [],
            [],
            freeze_facet_fallback(POLICY),
            POLICY,
            freeze_policy(POLICY),
            retrieve_facet=lambda query, limit: [{"chunk_id": "x", "text": "Photosynthesis."}],
            rerank_facet=lambda query, rows: [{**ranked(rows[0]), "reranker_revision": "0" * 40}],
            checkpoint=lambda phase, trace: None,
        )


def test_v9_explicit_sentence_split_preserves_decimal_condition_and_v8_identity():
    question = "Explain osmosis at 0.5 mol/L. Also describe diffusion at 1.25 mol/L."
    current = understanding(question)
    assert current["explicit_clause_count"] == 2
    assert current["requested_facets"][0]["request"] == "Explain osmosis at 0.5 mol/L"
    old = describe_question(
        question, prepare_query(question, version=LOCAL_QUESTION_VERSION).model_dump()
    )
    assert old["version"] == "question_understanding_v1" and len(old["requested_facets"]) == 1


def test_current_comparison_topic_is_not_a_single_operand_pronoun():
    question = "Compare the sugars, bases and usual structures of DNA and RNA? Also explain how to configure Kubernetes for this topic."
    current = prepare_query(question)
    assert not current.needs_clarification
    assert (
        "sugars, bases" in current.standalone_query
        and "Kubernetes for this topic" in current.standalone_query
    )
    assert prepare_query(question, version=LOCAL_QUESTION_VERSION).needs_clarification
    assert prepare_query("Compare DNA and RNA? How does it work?").needs_clarification


def test_interrogative_only_antecedent_falls_back_to_full_prior_conditional_question():
    prior = "What happens to chemical equilibrium when a reactant concentration increases?"
    question = "What conditions limit that explanation?"
    history = [{"role": "user", "message_id": "u1", "content": prior}]
    current = prepare_query(question, history)
    assert not current.needs_clarification
    assert current.standalone_query == question + " Prior learner question: " + prior
    assert current.referenced_message_ids == ["u1"]
    old = prepare_query(question, history, version=LOCAL_QUESTION_VERSION)
    assert old.standalone_query == "What conditions limit What explanation?"


def test_named_subject_performing_predicate_keeps_complete_hint_problem():
    question = "Give me only one first hint, without solving: an ideal gas doubles its absolute temperature at constant volume; what happens to pressure?"
    current = prepare_query(question)
    assert not current.needs_clarification and current.standalone_query == question
    assert prepare_query(question, version=LOCAL_QUESTION_VERSION).needs_clarification
    assert not prepare_query(
        "Explain why a cell changes its volume in dilute solution."
    ).needs_clarification
    assert prepare_query("Give me a hint: what changes its volume?").needs_clarification


def test_same_chunk_cannot_change_processing_identity_between_facets():
    calls = 0

    def retrieve(query, limit):
        nonlocal calls
        calls += 1
        return [{"chunk_id": "same", "text": "Photosynthesis.", "processing_id": str(calls)}]

    with pytest.raises(ValueError, match="immutable source identity"):
        facet_fallback(
            understanding(PARTIAL),
            [],
            [],
            freeze_facet_fallback(POLICY),
            POLICY,
            freeze_policy(POLICY),
            retrieve_facet=retrieve,
            rerank_facet=lambda query, rows: [ranked(rows[0])],
            checkpoint=lambda phase, trace: None,
        )
