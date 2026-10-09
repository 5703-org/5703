"""Current complete observations retain frozen query and requirement dispatch."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Snapshot
from conversation import query_v18, query_v19
from .test_chat_runtime import corpus, finish, session, submit

QUESTION = (
    "A breeding male stickleback attacks a red-bottomed object that does "
    "not resemble a fish. What does this illustrate about a fixed action pattern, "
    "its triggering stimulus and completion after the stimulus is removed?"
)


def test_new_default_retains_full_checker_and_opt_in_controls():
    settings = Settings(_env_file=None)
    # Explicit V19 fixtures below continue to assert their frozen predecessor.
    assert settings.chat_query_preparation_policy == "anchored_reference_v22"
    assert settings.chat_joint_checker_policy == "typed_joint_v5"
    assert settings.chat_coverage_query_policy == settings.chat_source_relation_policy == "off"


@pytest.mark.parametrize("suffix", ["", " Please give me one hint for this step."])
def test_current_full_observation_survives_frozen_worker_dispatch(runtime, suffix):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v19"
    text = QUESTION + suffix
    receipt = submit(rt, session(rt), text)
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        frozen = deepcopy(row.command)
        context = deepcopy(db.get(Snapshot, row.context_snapshot_id).payload)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v18"
    with (
        patch.object(service, "retrieve", wraps=service.retrieve) as retrieval,
        patch.object(
            service.GenerationService, "generate", side_effect=RuntimeError("STOP")
        ) as generation,
    ):
        assert rt.work()
        assert retrieval.called
    request = generation.call_args.args[0]
    assert request.prepared_query["preparation_version"] == query_v19.VERSION
    assert request.prepared_query["standalone_query"] == text
    assert request.prepared_query["referenced_message_ids"] == []
    assert not request.prepared_query["needs_clarification"]
    assert request.understanding["version"] == "question_requirements_v5"
    assert request.understanding["requirement_source_text"] == text
    assert request.understanding["current_message_resolution"]["source_text"] == text
    assert (
        request.understanding["preparation_dependency"]["frozen_preparation_version"]
        == query_v19.VERSION
    )
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen and row.budget["consumed_calls"] == 0
        assert db.get(Snapshot, row.context_snapshot_id).payload == context


def test_historical_v18_command_keeps_original_clarification(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v18"
    receipt = submit(rt, session(rt), QUESTION)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v19"
    with patch.object(service, "retrieve") as retrieval:
        answer = finish(rt, receipt)
        retrieval.assert_not_called()
    assert answer["response"]["response_type"] == "clarification"
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command["preparation_version"] == query_v18.VERSION
        assert row.budget["consumed_calls"] == 0


def test_isolated_demonstrative_remains_zero_call_clarification(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v19"
    receipt = submit(rt, session(rt), "What does this illustrate about a fixed action pattern?")
    with patch.object(service, "retrieve") as retrieval:
        answer = finish(rt, receipt)
        retrieval.assert_not_called()
    assert answer["response"]["response_type"] == "clarification"
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command["preparation_version"] == query_v19.VERSION
        assert row.budget["consumed_calls"] == 0
