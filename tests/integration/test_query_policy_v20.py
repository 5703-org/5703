"""Persisted V20/V6 and historical V19/V5 remain independent."""

from copy import deepcopy
from unittest.mock import patch

from app.core.config import Settings
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Snapshot
from conversation import query_v19, query_v20
from .test_chat_runtime import corpus, finish, session, submit

QUESTION = (
    "A breeding male stickleback attacks a red-bottomed object that does not resemble "
    "a fish. What does this illustrate about a fixed action pattern, its triggering "
    "stimulus and completion after the stimulus is removed? Please give me one hint for this step."
)


def test_latest_v21_default_preserves_all_other_opt_in_and_checker_controls():
    settings = Settings(_env_file=None)
    assert settings.chat_query_preparation_policy == "anchored_reference_v22"
    assert settings.chat_joint_checker_policy == "typed_joint_v5"
    assert settings.chat_coverage_query_policy == settings.chat_source_relation_policy == "off"


def test_frozen_v20_constructor_and_worker_keep_scientific_ids(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v20"
    receipt = submit(rt, session(rt), QUESTION)
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        frozen = deepcopy(row.command)
        context = deepcopy(db.get(Snapshot, row.context_snapshot_id).payload)
        assert frozen["requirements_version"] == "question_requirements_v6"
        assert frozen["preparation_version"] == query_v20.VERSION
    rt.settings.chat_query_preparation_policy = "anchored_reference_v19"
    with (
        patch.object(service, "retrieve", wraps=service.retrieve) as retrieval,
        patch.object(
            service.GenerationService, "generate", side_effect=RuntimeError("STOP")
        ) as generation,
    ):
        assert rt.work()
        assert retrieval.called
    request = generation.call_args.args[0]
    assert request.prepared_query["preparation_version"] == query_v20.VERSION
    assert request.prepared_query["standalone_query"] == QUESTION
    assert request.understanding["version"] == "question_requirements_v6"
    assert request.understanding["requirement_source_text"] == QUESTION
    assert [point["id"] for point in request.understanding["required_knowledge"]] == [
        "requirement_01",
        "requirement_02",
    ]
    assert (
        request.understanding["presentation_requests"][-1]["original_requirement_id"]
        == "requirement_03"
    )
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen and row.budget["consumed_calls"] == 0
        assert db.get(Snapshot, row.context_snapshot_id).payload == context


def test_historical_v19_constructor_keeps_v5_all_three_points(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v19"
    receipt = submit(rt, session(rt), QUESTION)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v20"
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("STOP")
    ) as generation:
        assert rt.work()
    request = generation.call_args.args[0]
    assert request.prepared_query["preparation_version"] == query_v19.VERSION
    assert request.understanding["version"] == "question_requirements_v5"
    assert [point["id"] for point in request.understanding["required_knowledge"]] == [
        "requirement_01",
        "requirement_02",
        "requirement_03",
    ]


def test_isolated_reference_remains_zero_call_clarification(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v20"
    receipt = submit(rt, session(rt), "What does this illustrate about a fixed action pattern?")
    with patch.object(service, "retrieve") as retrieval:
        answer = finish(rt, receipt)
        retrieval.assert_not_called()
    assert answer["response"]["response_type"] == "clarification"
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command["preparation_version"] == query_v20.VERSION
        assert row.budget["consumed_calls"] == 0
