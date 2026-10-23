"""Whole-answer restatement across the real owned request and worker boundaries."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Message, Snapshot
from conversation import query_v15, query_v16

from .test_chat_runtime import corpus, finish, session, submit


def test_latest_answer_restatement_is_frozen_and_reuses_its_actual_sources(runtime):
    rt = runtime
    corpus(rt)
    # Explicitly retain the V16 request contract when the live default advances.
    rt.settings.chat_query_preparation_policy = "anchored_reference_v16"
    assert rt.settings.chat_query_preparation_policy == "anchored_reference_v16"
    conversation = session(rt)
    first_question = "What is photosynthesis?"
    first = finish(rt, submit(rt, conversation, first_question))
    assert first["response"]["response_type"] == "answer"
    second = submit(rt, conversation, "Explain it more simply.")
    with rt.db() as db:
        row = db.get(AnswerRequest, second["request_id"])
        frozen = deepcopy(row.command)
        snapshot = deepcopy(db.get(Snapshot, row.context_snapshot_id).payload)
        marker = frozen["restatement_context"]
        assert marker["answer_id"] == first["id"]
        assert marker["answer_response_type"] == "answer"
        assert marker["latest_exchange_available"] is True
        assert marker["context_snapshot_hash"] == service.digest(snapshot)
        assert not any("answer_response_type" in m for m in snapshot["messages"])
    rt.settings.chat_query_preparation_policy = "anchored_reference_v15"
    with (
        patch.object(service, "retrieve") as retrieval,
        patch.object(
            service.GenerationService, "generate", side_effect=RuntimeError("STOP")
        ) as generation,
    ):
        assert rt.work()
        retrieval.assert_not_called()
    request = generation.call_args.args[0]
    assert request.prepared_query["preparation_version"] == query_v16.VERSION
    assert request.prepared_query["intent"] == "reexplain"
    assert request.prepared_query["needs_clarification"] is False
    assert first_question in request.prepared_query["standalone_query"]
    assert request.prepared_query["referenced_message_ids"] == [
        snapshot["messages"][-2]["message_id"]
    ]
    assert request.evidence
    assert request.history == snapshot["messages"]
    assert request.understanding["preparation_dependency"]["frozen_preparation_version"] == (
        query_v16.VERSION
    )
    assert request.understanding["preparation_dependency"]["restatement_preparation_version"] == (
        query_v15.VERSION
    )
    with rt.db() as db:
        row = db.get(AnswerRequest, second["request_id"])
        assert row.command == frozen
        assert db.get(Snapshot, row.context_snapshot_id).payload == snapshot
        assert row.budget["consumed_calls"] == 0


@pytest.mark.parametrize("prior", [None, "Hello"])
def test_restatement_without_a_factual_answer_clarifies_at_zero_calls(runtime, prior):
    rt = runtime
    rt.settings.chat_query_preparation_policy = "anchored_reference_v16"
    conversation = session(rt)
    if prior:
        first = finish(rt, submit(rt, conversation, prior))
        assert first["response"]["response_type"] == "social"
    receipt = submit(rt, conversation, "Explain it more simply.")
    with patch.object(service, "retrieve") as retrieval:
        answer = finish(rt, receipt)
        retrieval.assert_not_called()
    assert answer["response"]["response_type"] == "clarification"
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.budget["consumed_calls"] == 0


def test_later_unanswered_turn_cannot_restate_an_older_answer(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v16"
    conversation = session(rt)
    finish(rt, submit(rt, conversation, "What is photosynthesis?"))
    with rt.db() as db:
        db.add(
            Message(
                session_id=conversation["id"],
                sequence=3,
                role="user",
                content="What is quantum entanglement?",
                state="failed",
            )
        )
        db.commit()
    receipt = submit(rt, conversation, "Explain it more simply.")
    with rt.db() as db:
        marker = db.get(AnswerRequest, receipt["request_id"]).command["restatement_context"]
        assert marker["latest_exchange_available"] is False
    answer = finish(rt, receipt)
    assert answer["response"]["response_type"] == "clarification"
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).budget["consumed_calls"] == 0
