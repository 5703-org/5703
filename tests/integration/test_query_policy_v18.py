"""Frozen explicit comparison axes cross the real API and worker boundaries."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Snapshot
from conversation import query_v17, query_v18
from conversation.query import evidence_strategy

from .test_chat_runtime import corpus, finish, session, submit

PRIOR = "Compare DNA and RNA in their sugars, nitrogenous bases and usual strand structure. Explain each difference separately."
FOLLOWUP = "Explain the sugar difference in simpler language."


def test_new_installation_defaults_to_v22_and_retains_checker_v5():
    settings = Settings(_env_file=None)
    assert settings.chat_query_preparation_policy == "anchored_reference_v22"
    assert settings.chat_joint_checker_policy == "typed_joint_v5"


@pytest.mark.parametrize("policy", ["anchored_reference_v17", "anchored_reference_v18"])
def test_recorded_dispatch_survives_a_live_policy_change(runtime, policy):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = policy
    receipt = submit(
        rt, session(rt), "Compare oxygen and carbon dioxide. Explain each difference separately."
    )
    with rt.db() as db:
        frozen = deepcopy(db.get(AnswerRequest, receipt["request_id"]).command)
    rt.settings.chat_query_preparation_policy = (
        "anchored_reference_v18" if policy.endswith("17") else "anchored_reference_v17"
    )
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("STOP")
    ) as generation:
        assert rt.work()
    request = generation.call_args.args[0]
    expected = query_v17.VERSION if policy.endswith("17") else query_v18.VERSION
    assert request.prepared_query["preparation_version"] == expected
    assert request.understanding["version"] == "question_requirements_v5"
    assert request.understanding["preparation_dependency"]["frozen_preparation_version"] == expected
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen
        assert row.budget["consumed_calls"] == 0


def test_owned_comparison_refusal_allows_new_axis_retrieval_with_frozen_spans(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v18"
    conversation = session(rt)
    first = finish(rt, submit(rt, conversation, PRIOR))
    assert first["response"]["response_type"] == "refusal"
    receipt = submit(rt, conversation, FOLLOWUP)
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        frozen = deepcopy(row.command)
        context = deepcopy(db.get(Snapshot, row.context_snapshot_id).payload)
        assert frozen["restatement_context"]["answer_id"] == first["id"]
        assert frozen["restatement_context"]["answer_response_type"] == "refusal"
    rt.settings.chat_query_preparation_policy = "anchored_reference_v17"
    with (
        patch.object(service, "retrieve", wraps=service.retrieve) as retrieval,
        patch.object(
            service.GenerationService, "generate", side_effect=RuntimeError("STOP")
        ) as generation,
    ):
        assert rt.work()
        assert retrieval.called
    request = generation.call_args.args[0]
    prepared = request.prepared_query
    assert prepared["preparation_version"] == query_v18.VERSION
    assert prepared["needs_clarification"] is False
    assert prepared["intent"] == "comparison"
    assert evidence_strategy(FOLLOWUP, prepared) == "retrieve_and_reuse"
    assert prepared["referenced_message_ids"] == [context["messages"][-2]["message_id"]]
    (point,) = request.understanding["required_knowledge"]
    assert point["objects"] == ["DNA", "RNA"]
    assert point["requested_axes"] == ["sugars"]
    assert request.understanding["requirement_source_text"] == FOLLOWUP
    span = point["request_span"]
    assert FOLLOWUP[span["start"] : span["end"]] == point["verbatim_request"]
    assert request.history == context["messages"]
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).command == frozen
        assert db.get(Snapshot, row.context_snapshot_id).payload == context


def test_unknown_axis_keeps_clarification_and_zero_calls(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v18"
    conversation = session(rt)
    finish(rt, submit(rt, conversation, PRIOR))
    receipt = submit(rt, conversation, "Explain the cost difference in simpler language.")
    with patch.object(service, "retrieve") as retrieval:
        answer = finish(rt, receipt)
        retrieval.assert_not_called()
    assert answer["response"]["response_type"] == "clarification"
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).budget["consumed_calls"] == 0
