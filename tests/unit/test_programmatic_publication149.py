"""A no-source programmatic clarification must publish without factual pair bypass."""

import pytest
from app.core.exceptions import AppError
from app.modules.learning_state import sources
from app.modules.learning_state.models import AnswerPresentation
from test_prerequisite_publication147 import outcome


def clarification():
    db, request, answer, result = outcome()
    request.mode = "interactive_chat"
    result.response = {
        **result.response,
        "response_type": "clarification",
        "answer_text": "Which subject or relationship should I clarify?",
        "short_answer": None,
        "citations": [],
        "confidence": None,
    }
    result.response_origin = "programmatic_ambiguity_clarification"
    result.evidence = []
    result.attribution = {"fragments": [], "claims": [], "evidence_ranges": []}
    result.delivered_projection = {"response": result.response, "citation_views": []}
    result.token_budget = {}
    return db, request, answer, result


def test_actual_programmatic_clarification_can_publish_without_a_source_pair():
    db, request, answer, result = clarification()
    sources.persist_result(db, request, answer, result)
    saved = next(r for r in db.rows if isinstance(r, AnswerPresentation))
    assert saved.payload["response"] == result.response
    assert saved.payload["citation_views"] == []


@pytest.mark.parametrize(
    "variant",
    [
        "factual",
        "provider_origin",
        "noninteractive",
        "evidence",
        "claim",
        "fragment",
        "citation",
        "view",
        "source_attribute",
        "unknown_policy",
        "half_pair",
    ],
)
def test_non_source_pair_exception_cannot_admit_factual_or_source_bearing_outputs(variant):
    db, request, answer, result = clarification()
    if variant == "factual":
        result.response["response_type"] = "answer"
    elif variant == "provider_origin":
        result.response_origin = "model_generation"
    elif variant == "noninteractive":
        request.mode = "benchmark_mcq"
    elif variant == "evidence":
        result.evidence = [{"evidence_id": "ev_001"}]
    elif variant == "claim":
        result.attribution["claims"] = [{"text": "A factual claim"}]
    elif variant == "fragment":
        result.attribution["fragments"] = [{"fragment_id": "F001"}]
    elif variant == "citation":
        result.response["citations"] = ["ev_001"]
    elif variant == "view":
        result.delivered_projection["citation_views"] = [{"evidence_id": "ev_001"}]
    elif variant == "source_attribute":
        result.attribution["source_map"] = {"foreign": "forged"}
    elif variant == "unknown_policy":
        request.command["source_block_policy"] = "unknown"
    else:
        request.command["generation_context_policy"] = "complementary_context_v2"
    with pytest.raises(AppError):
        sources.persist_result(db, request, answer, result)
    assert not db.rows
