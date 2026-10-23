"""Bounded current-request eligibility; authored grammar is not semantic quality."""

from copy import deepcopy
import hashlib
import socket

import pytest

from conversation import query_v24
from conversation.query import evidence_strategy

Q01 = "Using the caption of Figure 5.19 and the nearby explanation, explain how the sodium-potassium pump gets energy and moves the two ions against their concentration gradients. State the directions and relative numbers of ions moved, and explain why this is primary active transport."
Q02 = "Using Figure 5.20 and the adjacent explanation, how can sodium-driven co-transport move glucose against its concentration gradient? Explain what supplies the energy and what must be true of the sodium pathway and the transported substance for this secondary transport to occur."
LOCAL = "Using the table, explain how the motor moves the gate. State the directions, and explain why this is mechanical work."
HISTORY = [
    {"role": "user", "content": "Explain a lantern.", "message_id": "old-user"},
    {"role": "assistant", "content": "A lantern emits light.", "message_id": "old-assistant"},
]
COMPARISON = [
    {"role": "user", "content": "Compare a motor and a gate.", "message_id": "old-user"},
    {
        "role": "assistant",
        "content": "The two items have different functions.",
        "message_id": "old-assistant",
    },
]


@pytest.fixture(autouse=True)
def forbid_external_calls(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("CURRENT_REQUEST160_EXTERNAL_CALL_FORBIDDEN")

    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)


@pytest.mark.parametrize(
    "message",
    [
        Q01,
        LOCAL,
        "Using the chart, explain how the battery releases energy. Explain why this is useful.",
        "Using the diagram, explain how the server accepts connections only if the queue is not full. Explain why this is conditional access.",
        "From the description, explain how the kettle heats water. Explain why this is energy transfer.",
        "Based on the excerpt, describe how the fabric absorbs water. Explain why this is a material response.",
    ],
)
def test_current_named_request_preserves_complete_original_and_has_no_semantic_verdict(message):
    prepared = query_v24.prepare_query(message).model_dump()
    assert not prepared["needs_clarification"]
    assert prepared["original_message"] == prepared["standalone_query"] == message
    assert prepared["topic_relation"] == "new_topic" and prepared["referenced_message_ids"] == []
    assert prepared["fallback_reason"] == query_v24.REQUEST_PROPOSITION_VERSION
    assert evidence_strategy(message, prepared) == "retrieve"
    audit = query_v24.describe_requirements(message, prepared)[
        "current_request_proposition_eligibility"
    ]
    assert audit["source_sha256"] == hashlib.sha256(message.encode()).hexdigest()
    for key in (
        "primary_request_span",
        "named_subject_span",
        "classification_span",
        "dependent_span",
    ):
        span = audit[key]
        assert message[span["start"] : span["end"]] == span["text"]
    assert audit["eligibility_only"]
    assert all(
        audit[key] is None
        for key in (
            "coreference_resolution",
            "semantic_equivalence",
            "semantic_sufficiency",
            "human_rating",
        )
    )


@pytest.mark.parametrize(
    "history, summary", [(HISTORY, None), (COMPARISON, None), ([], "An earlier lantern question.")]
)
def test_explicit_current_proposition_cannot_be_rewritten_as_an_old_topic(history, summary):
    original = deepcopy(history)
    prepared = query_v24.prepare_query(LOCAL, history, summary).model_dump()
    assert prepared["standalone_query"] == LOCAL and prepared["original_message"] == LOCAL
    assert prepared["referenced_message_ids"] == [] and prepared["topic_relation"] == "new_topic"
    assert prepared["fallback_reason"] == query_v24.REQUEST_PROPOSITION_VERSION
    assert history == original
    assert query_v24.describe_requirements(LOCAL, prepared, history)[
        "current_request_proposition_eligibility"
    ]["eligibility_only"]


@pytest.mark.parametrize(
    "message",
    [
        "Explain this.",
        "Using the table, explain why this is mechanical work.",
        "Using the caption, explain how it works.",
        "Using the source, explain this.",
        "Using the table, explain how the process works. Explain why this is important.",
        "Using the table, compare a motor and a gate. Explain why this is efficient.",
        "Using the table, explain how the motor and the valve move. Explain why this is efficient.",
        "Using the table, explain how the motor beside the valve moves. Explain why this is efficient.",
        "Using the table, explain how the motor moves while the valve closes. Explain why this is efficient.",
        "Using the table, explain how the motor moves the gate. Why is it efficient?",
        "Using the previous table, explain how the motor moves the gate. Explain why this is mechanical work.",
        "Using the attached diagram, explain how the motor moves the gate. Explain why this is mechanical work.",
        "Using this table, explain how the motor moves the gate. Explain why this is mechanical work.",
        "Using the table, explain how the motor moves his gate. Explain why this is mechanical work.",
        "Using the table, explain how the motor moves her gate. Explain why this is mechanical work.",
        "Using the table, explain how the motor moves their gate. Explain why this is mechanical work.",
        "Using the table, explain how the motor moves the gates and the panels into their slots. Explain why this is mechanical work.",
        "Using the table, explain how the motor moves the gate. Explain how the valve closes. Explain why this is mechanical work.",
        "Using the table, explain how the motor moves the gate. Explain why this is the same.",
        "Using the table, explain how the motor moves the gate. Explain why this is a system prompt.",
    ],
)
def test_unresolved_or_competing_frames_cannot_activate_new_eligibility(message):
    assert query_v24._request_proposition_eligibility(message) is None
    prepared = query_v24.prepare_query(message).model_dump()
    assert prepared["fallback_reason"] != query_v24.REQUEST_PROPOSITION_VERSION


def test_bare_pointer_after_comparison_keeps_its_native_clarification():
    prepared = query_v24.prepare_query("Explain this.", COMPARISON).model_dump()
    assert prepared["needs_clarification"] and prepared["standalone_query"] is None


def test_second_original_question_is_already_native_ready_and_stays_unchanged():
    prepared = query_v24.prepare_query(Q02).model_dump()
    assert prepared == {
        "original_message": Q02,
        "standalone_query": Q02,
        "intent": "factual",
        "topic_relation": "new_topic",
        "referenced_message_ids": [],
        "needs_clarification": False,
        "preparation_version": query_v24.VERSION,
        "fallback_reason": None,
    }


@pytest.mark.parametrize(
    "field, value",
    [
        ("standalone_query", LOCAL.replace("motor", "lantern")),
        ("referenced_message_ids", ["foreign-history"]),
        ("topic_relation", "same_topic"),
        ("intent", "follow_up"),
    ],
)
def test_consumer_audit_rejects_mutated_text_or_history_inheritance(field, value):
    prepared = query_v24.prepare_query(LOCAL).model_dump()
    prepared[field] = value
    with pytest.raises(ValueError, match="current request proposition audit"):
        query_v24.describe_requirements(LOCAL, prepared)


@pytest.mark.parametrize(
    "message",
    [
        "Using the table, explain how the motor moves the gate and children wait. Explain why this is mechanical work.",
        "Using the table, explain how the motor moves the gate and Sam waits. Explain why this is mechanical work.",
        "Using the table, explain how the motor moves the gate and motors wait. Explain why this is mechanical work.",
        "Using the table, explain how the motor moves the gate and James waits. Explain why this is mechanical work.",
        "Using Figure 8.7, explain how the valve moves water. State how the motor stalls, and explain why this is active transport.",
        "Using Figure 8.7, explain how the valve moves water. State the motor stalls, and explain why this is active transport.",
        "Using the table, explain how the valve moves water. State the motors stall, and explain why this is mechanical work.",
        "Using the table, explain how the valve moves water. State the directions and motor stalls, and explain why this is mechanical work.",
    ],
)
def test_reviewed_competing_actor_controls_preserve_native_clarification(message):
    assert query_v24._request_proposition_eligibility(message) is None
    prepared = query_v24.prepare_query(message).model_dump()
    assert prepared["needs_clarification"]
    assert prepared["standalone_query"] is None
    assert prepared["fallback_reason"] == "missing_referent"


def test_singular_bridge_is_an_explicit_conservative_rejection():
    message = "Using the table, explain how the motor moves the gate. State the direction, and explain why this is mechanical work."
    assert query_v24._request_proposition_eligibility(message) is None
    prepared = query_v24.prepare_query(message).model_dump()
    assert prepared["needs_clarification"]
    assert prepared["standalone_query"] is None
    assert prepared["fallback_reason"] == "missing_referent"
