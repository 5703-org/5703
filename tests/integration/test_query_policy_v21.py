"""Frozen mixed-clause transport; generation stops before any model call."""

from copy import deepcopy
from unittest.mock import patch

from app.core.config import Settings
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Snapshot
from conversation import query_v20, query_v21
from .test_chat_runtime import corpus, finish, session, submit

QUESTION = (
    "Why can prairie dogs get used to harmless footsteps, while a duckling follows "
    "the first adult it sees? Compare the kind of experience and timing involved "
    "in these two learning examples. Please give me one hint for this step."
)


def test_latest_default_preserves_checker_coverage_and_full_answer_controls():
    settings = Settings(_env_file=None)
    assert settings.chat_query_preparation_policy == "anchored_reference_v22"
    assert settings.chat_joint_checker_policy == "typed_joint_v5"
    assert settings.chat_coverage_query_policy == settings.chat_source_relation_policy == "off"


def test_frozen_v21_worker_preserves_scientific_span_and_independent_presentation(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v21"
    receipt = submit(rt, session(rt), QUESTION)
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        frozen = deepcopy(row.command)
        context = deepcopy(db.get(Snapshot, row.context_snapshot_id).payload)
        assert frozen["requirements_version"] == "question_requirements_v7"
        assert frozen["preparation_version"] == query_v21.VERSION
    rt.settings.chat_query_preparation_policy = "anchored_reference_v20"
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("STOP")
    ) as generation:
        assert rt.work()
    request = generation.call_args.args[0]
    assert request.prepared_query["preparation_version"] == query_v21.VERSION
    assert request.prepared_query["standalone_query"] == QUESTION
    assert request.understanding["version"] == "question_requirements_v7"
    assert request.understanding["requirement_source_text"] == QUESTION
    assert [row["id"] for row in request.understanding["required_knowledge"]] == [
        "requirement_01",
        "requirement_02",
    ]
    point = request.understanding["required_knowledge"][1]
    assert point["request_span"]["end"] == 184
    assert point["request"] == QUESTION[103:184]
    assert request.understanding["presentation_requests"][0]["request"] == QUESTION[186:223]
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen and row.budget["consumed_calls"] == 0
        assert db.get(Snapshot, row.context_snapshot_id).payload == context


def test_historical_v20_worker_keeps_its_original_mixed_scientific_requirement(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v20"
    receipt = submit(rt, session(rt), QUESTION)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v21"
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("STOP")
    ) as generation:
        assert rt.work()
    request = generation.call_args.args[0]
    assert request.prepared_query["preparation_version"] == query_v20.VERSION
    assert request.understanding["version"] == "question_requirements_v6"
    assert request.understanding["required_knowledge"][1]["request"] == QUESTION[103:223]
    assert request.understanding["presentation_requests"] == []


def test_v21_unresolved_reference_keeps_zero_call_clarification(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v21"
    receipt = submit(rt, session(rt), "What does this illustrate about a fixed action pattern?")
    with patch.object(service, "retrieve") as retrieval:
        answer = finish(rt, receipt)
        retrieval.assert_not_called()
    assert answer["response"]["response_type"] == "clarification"
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command["preparation_version"] == query_v21.VERSION
        assert row.budget["consumed_calls"] == 0
