"""Fresh current-context eligibility keeps full text and existing semantic fences."""

import pytest

from conversation import query_v22
from conversation import query_v23 as candidate
from conversation.query import evidence_strategy


class BeforePreparation:
    @staticmethod
    def prepare_query(message, **kwargs):
        value = query_v22.prepare_query(message, **kwargs)
        return value.model_copy(update={"preparation_version": candidate.VERSION})


before = BeforePreparation()

CASE05 = (
    "Model a fixed amount of gas as ideal. It occupies 0.450 L at 300 K and is "
    "heated to 400 K while pressure stays constant. What final volume is expected, "
    "and why must the temperature be on the kelvin scale? If pressure were also "
    "allowed to change without its new value being given, would these "
    "temperatures alone determine the final volume?"
)
CASE08 = (
    "In a well-insulated bomb calorimeter, a reaction raises the temperature of "
    "its surrounding water by 5.0 °C. Taking the reacting material as the system, "
    "what sign should the reaction heat q have? Can its numerical heat in joules "
    "be obtained from this temperature change alone? Explain what additional "
    "calorimeter quantity is needed and why calibration matters."
)


@pytest.mark.parametrize("message", [CASE05, CASE08])
def test_actual_fresh_current_setup_preserves_all_requirements_and_constraints(message):
    old = before.prepare_query(message).model_dump()
    assert old["needs_clarification"] and old["fallback_reason"] == "missing_referent"
    prepared = candidate.prepare_query(message).model_dump()
    assert not prepared["needs_clarification"]
    assert prepared["standalone_query"] == prepared["original_message"] == message
    assert prepared["referenced_message_ids"] == []
    assert prepared["topic_relation"] == "new_topic"
    assert prepared["fallback_reason"] == candidate.CURRENT_MESSAGE_ELIGIBILITY_VERSION
    assert evidence_strategy(message, prepared) == "retrieve"
    actual = candidate.describe_requirements(message, prepared)
    delegated = query_v22.describe_requirements(
        message, {**prepared, "preparation_version": query_v22.VERSION}
    )
    assert {
        k: v
        for k, v in actual.items()
        if k not in {"preparation_dependency", "current_message_eligibility"}
    } == {k: v for k, v in delegated.items() if k != "preparation_dependency"}
    metadata = actual["current_message_eligibility"]
    assert metadata["source_text"] == message
    assert len(metadata["dependent_spans"]) == 3
    for field in ("coreference_resolution", "semantic_equivalence", "semantic_sufficiency"):
        assert metadata[field] is None
    for span in [metadata["context_prefix_span"], *metadata["dependent_spans"]]:
        assert message[span["start"] : span["end"]] == span["text"]
    assert "current_event_resolution" not in actual


@pytest.mark.parametrize(
    "message",
    [
        "Consider a sealed vessel. It contains 2.5 L of water at 20 °C. "
        "What changes if its volume cannot increase without external work?",
        "Consider a zorb vessel. It transfers entropy to a reservoir. "
        "Why must its heat capacity equal -3.5 J/K unless temperature changes?",
    ],
)
def test_supported_or_unverified_setup_gets_no_local_scientific_verdict(message):
    assert before.prepare_query(message).needs_clarification
    prepared = candidate.prepare_query(message).model_dump()
    assert prepared["standalone_query"] == message
    assert not prepared["needs_clarification"]
    requirements = candidate.describe_requirements(message, prepared)
    assert requirements["requirement_source_text"] == message
    metadata = requirements["current_message_eligibility"]
    assert metadata["semantic_sufficiency"] is None
    assert metadata["coreference_resolution"] is None
    assert "supported" not in metadata


@pytest.mark.parametrize(
    "message",
    [
        "Consider the previous vessel. It contains 2 L. What is its pressure?",
        "Consider the selected vessel. It contains 2 L. What is its pressure?",
        "Consider the attached vessel. It contains 2 L. What is its pressure?",
        "It contains 2 L of water. What is its temperature?",
        "Consider RAG. It stores evidence. What is its mechanism?",
        "Consider a vessel and a reservoir. It contains 2 L. What is its pressure?",
        "A pump can move liquid. A valve can close. Does this require energy?",
        "Consider a mechanism. Why does it happen?",
    ],
)
def test_external_missing_subject_abbreviation_and_competing_setup_remain_unchanged(message):
    actual = candidate.prepare_query(message).model_dump()
    assert actual == before.prepare_query(message).model_dump()
    assert actual["needs_clarification"]
    assert candidate._current_message_eligibility(message) is None or (
        actual["fallback_reason"] == "ambiguous_abbreviation:RAG"
    )


def test_history_and_summary_cannot_activate_fresh_eligibility():
    history = [{"role": "user", "message_id": "old1", "content": "Explain a steel beam."}]
    summary = "[old1] Explain a steel beam."
    for context in [{"history": history}, {"summary": summary}]:
        assert candidate._current_message_eligibility(CASE05, **context) is None
        assert (
            candidate.prepare_query(CASE05, **context).model_dump()
            == before.prepare_query(CASE05, **context).model_dump()
        )


def test_frozen_current_eligibility_rejects_rewritten_quantity():
    prepared = candidate.prepare_query(CASE05).model_dump()
    prepared["standalone_query"] = prepared["standalone_query"].replace("0.450", "450")
    with pytest.raises(ValueError, match="frozen current retrieval eligibility"):
        candidate.describe_requirements(CASE05, prepared)
