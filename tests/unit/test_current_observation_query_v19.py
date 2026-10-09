"""Pure current-reference regressions; no application, SQL or provider imports."""

import hashlib

import pytest
from conversation import query_v18, query_v19 as query

QUESTION = (
    "A breeding male stickleback attacks a red-bottomed object that does "
    "not resemble a fish. What does this illustrate about a fixed action pattern, "
    "its triggering stimulus and completion after the stimulus is removed?"
)


@pytest.mark.parametrize("suffix", ["", " Please give me one hint for this step."])
def test_exact_frozen_g009_self_contained_input(suffix):
    text = QUESTION + suffix
    prior = query_v18.prepare_query(text, []).model_dump()
    assert prior["needs_clarification"] and prior["fallback_reason"] == "missing_referent"
    result = query.prepare_query(text, []).model_dump()
    assert result["standalone_query"] == result["original_message"] == text
    assert result["needs_clarification"] is False
    assert result["topic_relation"] == "new_topic"
    assert result["referenced_message_ids"] == []
    requirements = query.describe_requirements(text, result, [])
    original_requirements = query_v18.describe_requirements(
        text, {**result, "preparation_version": query_v18.VERSION}, []
    )
    for key in (
        "version",
        "required_knowledge",
        "requested_facets",
        "preserved_constraints",
        "requirement_source_text",
        "presentation_requests",
    ):
        assert requirements[key] == original_requirements[key]
    proof = requirements["current_message_resolution"]
    assert proof["source_text"] == text
    assert proof["source_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert {text[s["start"] : s["end"]] for s in proof["referent_spans"]} == {"that", "this", "its"}
    assert len(proof["referent_spans"]) == len(list(query_v18.DEPENDENT.finditer(text)))
    assert (
        proof["semantic_equivalence"]
        is proof["semantic_sufficiency"]
        is proof["human_rating"]
        is None
    )
    assert "not" in text and "after the stimulus is removed" in text
    for field, spans in requirements["preserved_constraints"].items():
        for span in spans:
            assert text[span["start"] : span["end"]] == span["text"], field


@pytest.mark.parametrize(
    "text",
    [
        "A leaf absorbs light. What does this show about photosynthesis?",
        "A balloon expands when air warms. What does this demonstrate about thermal expansion compared with contraction under constant pressure?",
        "A metal rod contracts at 0 degrees. What does this reveal about thermal contraction, its dependence on temperature without changing pressure?",
        "A particle responds to a field that is not uniform. What does this show about electric force?",
    ],
)
def test_rule_is_current_syntax_across_named_objects(text):
    result = query.prepare_query(text, []).model_dump()
    assert not result["needs_clarification"]
    assert result["original_message"] == result["standalone_query"] == text
    assert not result["referenced_message_ids"]
    requirements = query.describe_requirements(text, result, [])
    assert requirements["requirement_source_text"] == text
    assert not requirements["needs_clarification"]
    previous = query_v18.describe_requirements(
        text, {**result, "preparation_version": query_v18.VERSION}, []
    )
    for key in (
        "required_knowledge",
        "requested_facets",
        "preserved_constraints",
        "presentation_requests",
    ):
        assert requirements[key] == previous[key]


@pytest.mark.parametrize(
    "text",
    [
        "What does this illustrate about a fixed action pattern?",
        "Explain this.",
        "A fish attacks it. What does this show about a fixed action pattern?",
        "A fish attacks that object. What does this show about a fixed action pattern?",
        "A fish attacks an object that it sees. What does this show about a fixed action pattern?",
        "A strange thing moves. What does this show about a fixed action pattern?",
        "A fish attacks a target. What does this show about the previous comparison?",
        "A fish attacks a target. What does this show about a strange process?",
        "A fish attacks a target. What does this show about DNA and RNA, its sugar?",
        "A fish attacks a target. What does this show about its triggering stimulus?",
        "A fish attacks a target. What does this show about a fixed action pattern and them?",
        "A fish attacks a target. What does that show about a fixed action pattern?",
        "A fish attacks a target. What does this illustrate?",
        "A fish attacks a target. What does this show about a fixed action pattern? Explain it further.",
        "A fish attacks a target. What does this show about a fixed action pattern? Give me the answer to the previous step.",
        "A fish attacks a target. Another fish moves. What does this show about a fixed action pattern?",
    ],
)
def test_uncovered_inputs_retain_exact_v18_behavior(text):
    old = query_v18.prepare_query(text, []).model_dump()
    new = query.prepare_query(text, []).model_dump()
    assert new == {**old, "preparation_version": query.VERSION}
    assert new["fallback_reason"] != query.RESOLUTION_VERSION


@pytest.mark.parametrize("old_question", ["Compare DNA and RNA.", "Explain DNA replication."])
def test_explicit_current_observation_does_not_import_history_or_summary(old_question):
    history = [
        {"role": "user", "content": old_question, "message_id": "old-user"},
        {
            "role": "assistant",
            "content": "A prior answer about nucleic acids.",
            "message_id": "old-assistant",
        },
    ]
    result = query.prepare_query(
        QUESTION, history, "The learner previously studied nucleic acids."
    ).model_dump()
    assert result["standalone_query"] == QUESTION
    assert result["referenced_message_ids"] == []


def test_v18_owned_comparison_axis_is_preserved():
    history = [
        {
            "role": "user",
            "content": "Compare DNA and RNA in their sugars, nitrogenous bases and usual strand structure.",
            "message_id": "user-id",
        },
        {
            "role": "assistant",
            "content": "A retained refusal.",
            "message_id": "assistant-id",
            "answer_id": "answer-id",
            "answer_response_type": "refusal",
            "latest_exchange_available": True,
        },
    ]
    text = "Explain the sugar difference in simpler language."
    old = query_v18.prepare_query(text, history).model_dump()
    assert old["fallback_reason"] == query_v18.RESOLUTION_VERSION
    new = query.prepare_query(text, history).model_dump()
    assert new == {**old, "preparation_version": query.VERSION}
    requirement = query.describe_requirements(text, new, history)
    assert requirement["comparison_axis_resolution"]["objects"] == ["DNA", "RNA"]
    assert requirement["comparison_axis_resolution"]["requested_axis"] == "sugars"


def test_coordinate_spans_with_surrounding_whitespace():
    original = "  " + QUESTION + "  "
    prepared = query.prepare_query(original, []).model_dump()
    requirements = query.describe_requirements(original, prepared, [])
    proof = requirements["current_message_resolution"]
    assert proof["source_text"] == prepared["original_message"] == QUESTION
    assert proof["coordinate_space"] == "current_original_message"
    assert requirements["requirement_source_text"] == original.strip()


def test_corrupted_preparation_is_rejected():
    result = query.prepare_query(QUESTION, []).model_dump()
    with pytest.raises(ValueError):
        query.describe_requirements(QUESTION, {**result, "standalone_query": "Different text"}, [])
    with pytest.raises(ValueError):
        query.describe_requirements(QUESTION, {**result, "topic_relation": "same_topic"}, [])
    with pytest.raises(ValueError):
        query.prepare_query(QUESTION, [], version=query_v18.VERSION)
    with pytest.raises(ValueError):
        query.describe_requirements(
            QUESTION, {**result, "preparation_version": query_v18.VERSION}, []
        )
