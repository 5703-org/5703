"""Pure controls for current-event ownership and frozen query boundaries."""

import pytest

from conversation import query_v22 as previous
from conversation import query_v23 as query
from conversation.query import evidence_strategy


WATER = (
    "Rainwater can leave a tank through a drain. Does this change the water level, "
    "and in which direction does the water move? Explain the role of the drain."
)


def test_one_current_event_preserves_the_whole_request_and_retrieves():
    assert previous.prepare_query(WATER).needs_clarification
    prepared = query.prepare_query(WATER).model_dump()
    assert prepared["original_message"] == prepared["standalone_query"] == WATER
    assert prepared["preparation_version"] == query.VERSION
    assert prepared["fallback_reason"] == query.RESOLUTION_VERSION
    assert not prepared["needs_clarification"]
    assert prepared["intent"] == "factual"
    assert prepared["topic_relation"] == "new_topic"
    assert prepared["referenced_message_ids"] == []
    assert evidence_strategy(WATER, prepared) == "retrieve"
    requirements = query.describe_requirements(WATER, prepared)
    assert requirements["requirement_source_text"] == WATER
    assert requirements["rewrite_audit"]["missing"] == []
    resolution = requirements["current_event_resolution"]
    assert resolution["source_text"] == WATER
    assert resolution["semantic_sufficiency"] is None
    for span in resolution["referent_spans"]:
        assert WATER[span["start"] : span["end"]] == "this"


def test_competing_complete_statements_keep_the_existing_clarification():
    message = "A pump can move liquid. A valve can close. Does this require energy?"
    old = previous.prepare_query(message).model_dump()
    assert old["needs_clarification"]
    assert old["standalone_query"] is None
    current = query.prepare_query(message).model_dump()
    assert current == {**old, "preparation_version": query.VERSION}
    assert current["fallback_reason"] != query.RESOLUTION_VERSION
    assert evidence_strategy(message, current) == "none"


def test_current_syntax_cannot_override_an_unresolved_term_domain():
    message = "RAG can operate in a system. Does this require energy?"
    old = previous.prepare_query(message).model_dump()
    assert old["needs_clarification"]
    assert old["fallback_reason"] == "ambiguous_abbreviation:RAG"
    current = query.prepare_query(message).model_dump()
    assert current == {**old, "preparation_version": query.VERSION}
    assert current["standalone_query"] is None
    assert evidence_strategy(message, current) == "none"


@pytest.mark.parametrize(
    "field,value",
    [
        ("standalone_query", "Changed question"),
        ("topic_relation", "same_topic"),
        ("referenced_message_ids", ["unowned-history"]),
    ],
)
def test_tampered_preparation_cannot_acquire_frozen_event_requirements(field, value):
    prepared = query.prepare_query(WATER).model_dump()
    assert prepared["fallback_reason"] == query.RESOLUTION_VERSION
    prepared[field] = value
    with pytest.raises(ValueError, match="reference is unavailable"):
        query.describe_requirements(WATER, prepared)
