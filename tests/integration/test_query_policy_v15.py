"""New and historical query identities against actual worker/API/PostgreSQL."""

from unittest.mock import patch

import pytest

from app.modules.answering import service
from app.modules.answering.models import AnswerRequest
from conversation import query_v14, query_v15

from .test_chat_runtime import corpus, finish, session, submit


@pytest.mark.parametrize(
    "question",
    [
        "Does an enzyme alter a reaction's free-energy change, or only its activation-energy "
        "barrier? Explain the distinction without treating the two energies as equal.",
        "Follow the sequence from light absorption to sugar production, then distinguish "
        "the source and storage forms described for transport through a growing plant.",
    ],
)
def test_v15_submission_preserves_question_and_identity_after_live_reversion(runtime, question):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v15"
    assert rt.settings.chat_query_preparation_policy == "anchored_reference_v15"
    rt.settings.chat_source_relation_policy = "off"
    receipt = submit(rt, session(rt), question)
    with rt.db() as db:
        frozen = dict(db.get(AnswerRequest, receipt["request_id"]).command)
        assert frozen["preparation_version"] == query_v15.VERSION
    rt.settings.chat_query_preparation_policy = "anchored_reference_v14"
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("STOP")
    ) as gen:
        assert rt.work()
    request = gen.call_args.args[0]
    assert request.question == request.prepared_query["standalone_query"] == question
    assert request.prepared_query["preparation_version"] == query_v15.VERSION
    assert request.prepared_query["needs_clarification"] is False
    assert request.prepared_query["referenced_message_ids"] == []
    dependency = request.understanding["preparation_dependency"]
    assert dependency["frozen_preparation_version"] == query_v15.VERSION
    assert dependency["anchor_preparation_version"] == query_v14.VERSION
    assert request.source_relation_policy is None
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen
        assert row.budget["consumed_calls"] == 0


@pytest.mark.parametrize(
    "question",
    [
        "Explain the previously mentioned source.",
        "Can the previous source be used?",
        "Does the original source still exist?",
        "Describe the above source.",
        "Compare the prior source with the earlier source.",
        "Explain the earlier process, then distinguish source and storage forms.",
        "Describe the previously mentioned mechanism, then identify the source.",
        "Explain the above topic, then compare source and storage forms.",
    ],
)
def test_missing_discourse_reference_clarifies_without_search_or_provider(runtime, question):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v15"
    receipt = submit(rt, session(rt), question)
    with patch.object(service, "retrieve") as retrieval:
        answer = finish(rt, receipt)
        retrieval.assert_not_called()
    assert answer["response"]["response_type"] == "clarification"
    assert answer["evidence"] == []
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command["preparation_version"] == query_v15.VERSION
        assert row.budget["consumed_calls"] == 0
