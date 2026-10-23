"""Named propositional confirmation stays faithful without scientific word lists."""

import pytest
from conversation import query_v24

HISTORY = [
    {"role": "user", "content": "Compare the two mechanisms.", "message_id": "owned-user"},
    {
        "role": "assistant",
        "content": "The mechanisms differ in their scope.",
        "message_id": "owned-assistant",
    },
]


@pytest.mark.parametrize(
    "message",
    [
        "Does that mean solutes also move by osmosis? Explain using the textbook.",
        "Does that mean batteries also store energy?",
        "Does this mean servers can accept connections?",
        "Does that mean flour also absorbs water?",
        "Does this mean heat is also transferred?",
        "Does this mean markets also respond?",
        "Does that mean entropy is increasing?",
        "Does that mean the queue is empty?",
    ],
)
def test_explicit_named_proposition_preserves_question_and_owned_context(message):
    prepared = query_v24.prepare_query(message, HISTORY).model_dump()
    assert prepared["original_message"] == message
    assert prepared["standalone_query"] == message
    assert prepared["needs_clarification"] is False
    assert prepared["fallback_reason"] == "explicit_proposition_confirmation_v1"
    assert prepared["referenced_message_ids"] == ["owned-user", "owned-assistant"]
    requirements = query_v24.describe_requirements(message, prepared, HISTORY)
    assert requirements["explicit_proposition_confirmation"]["source_text"] == message
    assert requirements["explicit_proposition_confirmation"]["semantic_sufficiency"] is None


@pytest.mark.parametrize(
    "message",
    [
        "Does that mean it also moves?",
        "Does that mean they are also larger?",
        "Does that mean solutes move there?",
        "Does that mean the process also changes?",
        "Does that mean that also changes?",
        "Does that mean the other one expands?",
        "Does that mean solutes also?",
        "Does that mean both expand?",
        "Does that mean a new question?",
        "Does that mean a higher volume?",
        "Does that mean the cell membrane?",
        "Does that mean batteries can charge them?",
    ],
)
def test_ambiguous_referents_remain_clarifications(message):
    prepared = query_v24.prepare_query(message, HISTORY).model_dump()
    assert prepared["needs_clarification"] is True
    assert prepared["fallback_reason"] != "explicit_proposition_confirmation_v1"


def test_confirmation_without_an_owned_completed_exchange_remains_unresolved():
    prepared = query_v24.prepare_query("Does that mean solutes also move by osmosis?").model_dump()
    assert prepared["needs_clarification"] is True


def test_confirmation_audit_rejects_another_history_identity():
    message = "Does that mean batteries also store energy?"
    prepared = query_v24.prepare_query(message, HISTORY).model_dump()
    with pytest.raises(ValueError):
        query_v24.describe_requirements(
            message, prepared, [{**h, "message_id": "foreign"} for h in HISTORY]
        )
