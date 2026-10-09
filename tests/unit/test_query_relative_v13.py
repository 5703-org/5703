"""Current-subject relative questions retrieve without importing old topics."""

import pytest

from conversation.query import POSSESSIVE_VERSION, VERSION, evidence_strategy, prepare_query


@pytest.mark.parametrize(
    "message",
    [
        "How does a plant turn sunlight into food it can use?",
        "How does a battery store energy it can release later?",
        "Why does a plant not convert energy into food it cannot use at 5 degrees?",
    ],
)
def test_single_current_subject_preserves_original_and_retrieves(message):
    prepared = prepare_query(
        message,
        [{"role": "user", "content": "What is an enzyme?", "id": "previous"}],
    ).model_dump()
    assert prepared["preparation_version"] == VERSION
    assert prepared["standalone_query"] == message
    assert prepared["referenced_message_ids"] == []
    assert not prepared["needs_clarification"]
    assert evidence_strategy(message, prepared) == "retrieve"


def test_historical_v12_keeps_its_recorded_clarification():
    message = "How does a plant turn sunlight into food it can use?"
    prepared = prepare_query(message, version=POSSESSIVE_VERSION).model_dump()
    assert prepared["needs_clarification"]
    assert prepared["fallback_reason"] == "missing_referent"
    assert evidence_strategy(message, prepared) == "none"


@pytest.mark.parametrize(
    "message",
    [
        "How does it turn sunlight into food?",
        "How does a plant and a fungus turn sunlight into food it can use?",
        "How does a plant produce food for a fungus it can use?",
        "How does a plant turn sunlight into food it can use, and where does it store it?",
        "Compare a plant and a fungus. How does it obtain food?",
    ],
)
def test_missing_or_competing_current_subjects_still_clarify(message):
    prepared = prepare_query(message).model_dump()
    assert prepared["needs_clarification"]
    assert evidence_strategy(message, prepared) == "none"
