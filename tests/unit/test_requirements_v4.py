"""Reader metadata must not become a factual answer requirement."""

from conversation.query import prepare_query
from conversation.requirements import describe_requirements as legacy_requirements
from conversation.requirements_v4 import describe_requirements
from generation.coverage_v3 import assess_evidence_coverage


def reading_prepared(question):
    prepared = prepare_query(question, []).model_dump()
    return {
        **prepared,
        "standalone_query": question
        + "\nTextbook section: Chapter 5 Photosynthesis / 5.1 Overview",
        "fallback_reason": "verified_reading_selection",
    }


def test_selected_passage_locator_is_not_a_second_required_topic():
    question = "What is photosynthesis in this selected passage?"
    prepared = reading_prepared(question)
    old = legacy_requirements(question, prepared)
    new = describe_requirements(question, prepared)
    assert len(old["required_knowledge"]) == 2
    assert len(new["required_knowledge"]) == 1
    assert new["version"] == "question_requirements_v4"
    assert new["required_knowledge"][0]["request"] == "What is photosynthesis"
    assert new["required_knowledge"][0]["terms"] == ["photosynthesis"]
    assert new["original_message"] == question
    assert new["reader_reference_resolution"]["status"] == "adjunct_removed"
    assert prepared["standalone_query"].endswith("5.1 Overview")


def test_reader_locator_removal_keeps_actual_numeric_condition():
    question = "According to this selected passage, how does osmosis change at 0.5 mol/L?"
    new = describe_requirements(question, reading_prepared(question))
    assert len(new["required_knowledge"]) == 1
    assert "osmosis" in new["required_knowledge"][0]["terms"]
    assert "0.5" in new["required_knowledge"][0]["terms"]
    assert "5.1" not in new["required_knowledge"][0]["terms"]
    assert new["preserved_constraints"]["quantities_and_units"]


def test_common_leading_reading_reference_is_removed_without_losing_subject():
    question = "In this selected passage, what is photosynthesis?"
    new = describe_requirements(question, reading_prepared(question))
    assert new["required_knowledge"][0]["request"] == "what is photosynthesis"
    assert new["required_knowledge"][0]["terms"] == ["photosynthesis"]


def test_reader_core_reference_is_not_silently_rewritten():
    question = "Explain this paragraph."
    new = describe_requirements(question, reading_prepared(question))
    assert new["reader_reference_resolution"]["status"] == "source_bound"
    assert new["required_knowledge"][0]["request"] == "Explain this paragraph"
    assert new["required_knowledge"][0]["terms"] == []
    assert new["required_knowledge"][0]["origin"] == "verified_selected_source_referent_v1"
    coverage = assess_evidence_coverage(
        question,
        [
            {
                "chunk_id": "published-selection",
                "evidence_id": "ev_001",
                "text": "Photosynthesis converts solar energy into chemical energy.",
            }
        ],
        new,
    )
    assert coverage["targeted_query"] is None
    assert coverage["locatable_missing"] == []
    assert coverage["source_bound_requirement_ids"] == ["requirement_01"]
    assert "read that exact source" in coverage["response_guidance"]


def test_nonreading_questions_keep_v3_content_under_new_identity():
    question = "Compare DNA and RNA."
    prepared = prepare_query(question, []).model_dump()
    old = legacy_requirements(question, prepared)
    new = describe_requirements(question, prepared)
    assert new["version"] == "question_requirements_v4"
    assert new["required_knowledge"] == old["required_knowledge"]
    assert new["original_question_hash"] == old["original_question_hash"]
