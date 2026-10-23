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


ASSIGNMENTS = (
    "For vinegar with a hydronium ion concentration of approximately 4 × 10^-3 M, "
    "a learner writes pH = 11.6 and pOH = 2.4. Are those assignments correct? "
    "Give the correct pair and identify which of the two quantities is normally "
    "measured directly with a pH meter."
)


def test_current_assignments_preserve_source_values_and_requirement_spans():
    assert previous.prepare_query(ASSIGNMENTS).needs_clarification
    prepared = query.prepare_query(ASSIGNMENTS).model_dump()
    assert not prepared["needs_clarification"]
    assert prepared["standalone_query"] == prepared["original_message"] == ASSIGNMENTS
    assert prepared["referenced_message_ids"] == []
    assert evidence_strategy(ASSIGNMENTS, prepared) == "retrieve"
    requirements = query.describe_requirements(ASSIGNMENTS, prepared)
    delegated = previous.describe_requirements(
        ASSIGNMENTS, {**prepared, "preparation_version": previous.VERSION}
    )
    assert {
        k: v
        for k, v in requirements.items()
        if k not in {"preparation_dependency", "current_event_resolution"}
    } == {k: v for k, v in delegated.items() if k != "preparation_dependency"}
    resolution = requirements["current_event_resolution"]
    assert resolution["version"] == query.ASSIGNMENT_RESOLUTION_VERSION
    assert resolution["semantic_equivalence"] is None
    assert resolution["semantic_sufficiency"] is None
    assert [
        (
            ASSIGNMENTS[s["name_start"] : s["name_end"]],
            ASSIGNMENTS[s["value_start"] : s["value_end"]],
        )
        for s in resolution["assignment_spans"]
    ] == [("pH", "11.6"), ("pOH", "2.4")]


def test_assignment_reference_preserves_signed_exponents_and_negative_condition():
    message = (
        "A learner records x = -1.25e-3 and y = +2.4. Are these values correct? "
        "Explain why the values must not be rounded."
    )
    prepared = query.prepare_query(message).model_dump()
    assert not prepared["needs_clarification"]
    assert prepared["standalone_query"] == message
    resolution = query.describe_requirements(message, prepared)["current_event_resolution"]
    assert [message[s["value_start"] : s["value_end"]] for s in resolution["assignment_spans"]] == [
        "-1.25e-3",
        "+2.4",
    ]


@pytest.mark.parametrize(
    "message",
    [
        "Are those assignments correct? Explain the result.",
        "Above, a learner records x = 1 and y = 2. Are those assignments correct?",
        "A learner records x = 1 and x = 2. Are those assignments correct?",
        "A learner records RAG = 1 and score = 2. Are those assignments correct?",
    ],
)
def test_assignment_syntax_keeps_missing_external_duplicate_and_semantic_fences(message):
    old = previous.prepare_query(message).model_dump()
    assert old["needs_clarification"]
    assert query.prepare_query(message).model_dump() == {
        **old,
        "preparation_version": query.VERSION,
    }


def test_assignment_requirement_provenance_rejects_added_history():
    prepared = query.prepare_query(ASSIGNMENTS).model_dump()
    prepared["referenced_message_ids"] = ["unowned-history"]
    with pytest.raises(ValueError, match="reference is unavailable"):
        query.describe_requirements(ASSIGNMENTS, prepared)
