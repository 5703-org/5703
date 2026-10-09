"""Topic preservation and grounded refusal without paid provider calls."""

from copy import deepcopy
from unittest.mock import Mock
import pytest
from conversation.query import prepare_query, evidence_strategy
from retrieval.relevance import MODEL, REVISION, freeze_policy, screen
from generation import GenerationRequest, GenerationService


def row(text, score=5.0, id="chunk1"):
    return {
        "chunk_id": id,
        "text": text,
        "section": "Topic",
        "score": score,
        "score_type": "cross_encoder",
        "reranker_model": MODEL,
        "reranker_revision": REVISION,
    }


POLICY = freeze_policy({"reranker_model": MODEL, "reranker_revision": REVISION})


def test_bare_rag_clarifies_without_retrieval_or_model_call():
    for history in ([], [{"role": "assistant", "content": "You mean ragweed pollen."}]):
        prepared = prepare_query("Do you know what is rag", history).model_dump()
        assert prepared["needs_clarification"]
        assert evidence_strategy("rag", prepared) == "none"
        adapter = Mock()
        result = GenerationService(adapter).generate(
            GenerationRequest(
                request_id="ambiguity",
                mode="interactive_chat",
                condition="E1",
                question="Do you know what is rag",
                evidence=[],
                prepared_query=prepared,
            )
        )
        assert result.response["response_type"] == "clarification"
        assert result.response["citations"] == []
        adapter.generate.assert_not_called()
        assert result.budget["consumed_calls"] == 0


def test_user_ai_context_and_explicit_correction_never_reuse_guessed_evidence():
    history = [{"role": "user", "content": "Explain AI chatbots", "message_id": "u1"}]
    prepared = prepare_query("What is rag?", history)
    assert "retrieval-augmented generation (RAG)" in prepared.standalone_query
    history = [
        {"role": "user", "content": "What is rag?", "message_id": "u1"},
        {"role": "assistant", "content": "Ragweed pollen causes allergies."},
    ]
    prepared = prepare_query("I mean retrieval-augmented generation", history)
    assert prepared.standalone_query == "What is retrieval-augmented generation (RAG)?"
    assert evidence_strategy(prepared.original_message, prepared.model_dump()) == "retrieve"
    assert prepared.referenced_message_ids == ["u1"]


@pytest.mark.parametrize(
    "question",
    [
        "What causes ragweed allergy?",
        "What does RAG1 do?",
        "Explain recombination-activating RAG genes",
    ],
)
def test_biology_topics_are_preserved(question):
    prepared = prepare_query(question)
    assert not prepared.needs_clarification
    assert "retrieval-augmented" not in prepared.standalone_query


def test_whole_term_gate_blocks_ragweed_even_with_high_authored_score():
    # This score is a deliberate unit fixture, not a reported model measurement.
    query = prepare_query("Explain RAG in AI").standalone_query
    rows = [
        row("Ragweed pollen produces allergic reactions."),
        row("Retrieval-augmented generation uses retrieved context.", id="chunk2"),
    ]
    before = deepcopy(rows)
    accepted, trace = screen(query, rows, POLICY)
    assert [r["chunk_id"] for r in accepted] == ["chunk2"]
    assert trace["excluded"][0]["reason"] == "expanded_concept_absent"
    assert rows == before


def test_threshold_can_return_no_evidence_and_rejects_wrong_score_scale():
    accepted, trace = screen("Explain a computer deployment", [row("Cell division", -10)], POLICY)
    assert not accepted and trace["accepted_count"] == 0
    with pytest.raises(ValueError, match="pinned"):
        screen("cells", [{**row("cells"), "score_type": "cosine"}], POLICY)
    with pytest.raises(ValueError, match="Nonfinite"):
        screen("cells", [row("cells", float("nan"))], POLICY)
    assert freeze_policy(None)["minimum_logit"] is None


def test_mock_alias_equivalence_keeps_negation_and_whole_word_boundaries():
    from generation.adapters import mock_terms

    assert mock_terms("ATP") == mock_terms("adenosine triphosphate (ATP)")
    assert mock_terms("not ATP") != mock_terms("ATP")
    assert mock_terms("RAG") != mock_terms("ragweed")
    assert mock_terms("RAG1") != mock_terms("RAG")


def test_comparison_keeps_complementary_passages_and_genuine_ragweed():
    query = prepare_query("Compare DNA and RNA").standalone_query
    accepted, _ = screen(
        query,
        [
            row("DNA stores genetic information."),
            row("RNA participates in translation.", id="chunk2"),
        ],
        POLICY,
    )
    assert len(accepted) == 2
    assert screen("What causes ragweed allergy?", [row("Ragweed pollen is an allergen.")], POLICY)[
        0
    ]
