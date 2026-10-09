"""Opt-in checker policy snapshots against the real API, worker and PostgreSQL."""

from unittest.mock import patch

import pytest

from app.modules.answering import service
from app.modules.answering.models import AnswerRequest
from conversation import query_v14
from conversation.query import VERSION as BASE_QUERY_VERSION

from .test_chat_runtime import call, corpus, session, submit


@pytest.mark.parametrize(
    ("submitted", "later", "expected"),
    [
        ("off", "source_relation_contract_v1", None),
        ("source_relation_contract_v1", "off", "source_relation_contract_v1"),
        ("source_relation_contract_v2", "off", "source_relation_contract_v2"),
    ],
)
def test_worker_uses_the_submitted_relation_policy_after_setting_changes(
    runtime, submitted, later, expected
):
    rt = runtime
    corpus(rt)
    rt.settings.chat_source_relation_policy = submitted
    rt.settings.chat_query_preparation_policy = "anchored_reference_v14" if expected else "recorded"
    receipt = submit(rt, session(rt), "What is photosynthesis?")
    with rt.db() as db:
        frozen = dict(db.get(AnswerRequest, receipt["request_id"]).command)
        assert frozen["source_relation_policy"] == expected
        assert frozen["preparation_version"] == (
            query_v14.VERSION if expected else BASE_QUERY_VERSION
        )
    rt.settings.chat_source_relation_policy = later
    rt.settings.chat_query_preparation_policy = "recorded" if expected else "anchored_reference_v14"
    # Stop at the actual generation boundary: this test checks durable policy
    # transport, without treating authored fixture answers as semantic evidence.
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("BOUNDARY_TEST_STOP")
    ) as generate:
        assert rt.work()
    request = generate.call_args.args[0]
    assert request.source_relation_policy == expected
    assert request.prepared_query["preparation_version"] == (
        query_v14.VERSION if expected else BASE_QUERY_VERSION
    )
    assert request.evidence_coverage["version"] == (
        "context_coverage_v4" if expected else "context_coverage_v3"
    )
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen
        assert row.budget["max_calls"] == 4
        assert row.budget["max_active_seconds"] == 180
        assert row.budget["consumed_calls"] == 0
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed"
    assert job.get("answer_id") is None


def test_legacy_command_without_relation_marker_is_not_upgraded_by_live_setting(runtime):
    rt = runtime
    corpus(rt)
    receipt = submit(rt, session(rt), "What is photosynthesis?")
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        frozen = dict(row.command)
        frozen.pop("source_relation_policy")
        row.command = frozen
        db.commit()
    rt.settings.chat_source_relation_policy = "source_relation_contract_v1"
    rt.settings.chat_query_preparation_policy = "anchored_reference_v14"
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("BOUNDARY_TEST_STOP")
    ) as generate:
        assert rt.work()
    assert generate.call_args.args[0].source_relation_policy is None
    assert generate.call_args.args[0].evidence_coverage["version"] == "context_coverage_v3"
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).command == frozen


@pytest.mark.parametrize(
    "question",
    [
        "Does an enzyme alter a reaction's free-energy change, or only its activation-energy "
        "barrier? Explain the distinction without treating the two energies as equal.",
        "Follow the sequence from light absorption to sugar production, then distinguish "
        "the source and storage forms described for transport through a growing plant.",
    ],
)
def test_default_query_policy_reaches_generation_without_relation_candidate_or_history(
    runtime, question
):
    rt = runtime
    corpus(rt)
    rt.settings.chat_source_relation_policy = "off"
    rt.settings.chat_query_preparation_policy = "anchored_reference_v14"
    receipt = submit(rt, session(rt), question)
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("BOUNDARY_TEST_STOP")
    ) as generate:
        assert rt.work()
    request = generate.call_args.args[0]
    assert request.prepared_query["needs_clarification"] is False
    assert request.prepared_query["standalone_query"] == question
    assert request.prepared_query["referenced_message_ids"] == []
    assert request.question == question
    assert request.understanding["preparation_dependency"]["frozen_preparation_version"] == (
        query_v14.VERSION
    )
    assert request.source_relation_policy is None
    assert request.evidence_coverage["version"] == "context_coverage_v3"
