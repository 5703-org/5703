"""Presentation-aware requirements at the frozen API/worker boundary."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Snapshot
from conversation import query_v16, query_v17

from .test_chat_runtime import corpus, finish, session, submit


@pytest.mark.parametrize(
    "question,expected_count",
    [
        ("Compare oxygen and carbon dioxide. Explain each difference separately.", 1),
        ("Why does photosynthesis need light and which products are transported?", 2),
    ],
)
def test_v17_requirements_are_frozen_before_live_policy_changes(runtime, question, expected_count):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v17"
    assert rt.settings.chat_query_preparation_policy == "anchored_reference_v17"
    receipt = submit(rt, session(rt), question)
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        frozen = deepcopy(row.command)
        assert frozen["preparation_version"] == query_v17.VERSION
        assert frozen["requirements_version"] == "question_requirements_v5"
    rt.settings.chat_query_preparation_policy = "anchored_reference_v16"
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("STOP")
    ) as generation:
        assert rt.work()
    request = generation.call_args.args[0]
    assert request.question == question
    assert request.prepared_query["standalone_query"] == question
    assert request.prepared_query["preparation_version"] == query_v17.VERSION
    assert request.understanding["version"] == "question_requirements_v5"
    assert len(request.understanding["required_knowledge"]) == expected_count
    if "separately" in question:
        assert request.understanding["presentation_requests"]
        assert not any(
            point["request"] == "Explain each difference separately"
            for point in request.understanding["required_knowledge"]
        )
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen
        assert row.budget["consumed_calls"] == 0


def test_default_v17_retains_last_verified_answer_restatement(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v17"
    conversation = session(rt)
    first = finish(rt, submit(rt, conversation, "What is photosynthesis?"))
    second = submit(rt, conversation, "Explain it more simply.")
    with rt.db() as db:
        row = db.get(AnswerRequest, second["request_id"])
        frozen = deepcopy(row.command)
        snapshot = deepcopy(db.get(Snapshot, row.context_snapshot_id).payload)
        assert frozen["restatement_context"]["answer_id"] == first["id"]
    rt.settings.chat_query_preparation_policy = "anchored_reference_v16"
    with (
        patch.object(service, "retrieve") as retrieval,
        patch.object(
            service.GenerationService, "generate", side_effect=RuntimeError("STOP")
        ) as generation,
    ):
        assert rt.work()
        retrieval.assert_not_called()
    request = generation.call_args.args[0]
    assert request.prepared_query["preparation_version"] == query_v17.VERSION
    assert request.prepared_query["intent"] == "reexplain"
    assert request.prepared_query["referenced_message_ids"] == [
        snapshot["messages"][-2]["message_id"]
    ]
    assert request.understanding["preparation_dependency"]["frozen_preparation_version"] == (
        query_v17.VERSION
    )
    assert request.evidence
    with rt.db() as db:
        assert db.get(AnswerRequest, second["request_id"]).command == frozen


@pytest.mark.parametrize("policy", ["anchored_reference_v16", "anchored_reference_v17"])
def test_recorded_query_policy_keeps_its_requirement_version(runtime, policy):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = policy
    receipt = submit(
        rt,
        session(rt),
        "Compare oxygen and carbon dioxide. Explain each difference separately.",
    )
    rt.settings.chat_query_preparation_policy = (
        "anchored_reference_v17" if policy.endswith("16") else "anchored_reference_v16"
    )
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("STOP")
    ) as generation:
        assert rt.work()
    request = generation.call_args.args[0]
    if policy.endswith("16"):
        assert request.prepared_query["preparation_version"] == query_v16.VERSION
        assert request.understanding["version"] == "question_requirements_v4"
        assert len(request.understanding["required_knowledge"]) == 2
    else:
        assert request.prepared_query["preparation_version"] == query_v17.VERSION
        assert request.understanding["version"] == "question_requirements_v5"
        assert len(request.understanding["required_knowledge"]) == 1
