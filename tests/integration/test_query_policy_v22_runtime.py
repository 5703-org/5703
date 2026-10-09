"""Native frozen V21/V22 execution on authored source and disposable SQL."""

from copy import deepcopy
from uuid import uuid4

import pytest

from app.modules.answering.models import AnswerRequest
from .conftest import disposable_postgres_url
from .test_chat_runtime import call, corpus, finish, session, submit
from .test_reading_answer_core_v5 import context_for, send


@pytest.fixture
def postgres_url():
    with disposable_postgres_url() as url:
        yield url


@pytest.fixture(autouse=True)
def forbid_external_model_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Version replay controls must never contact a model provider")

    monkeypatch.setattr("generation.adapters.open_provider", forbidden)
    monkeypatch.setattr("generation.adapters.LLMAdapter._call", forbidden)


@pytest.mark.parametrize("number,requirements", [(21, 7), (22, 8)])
def test_reader_cancel_retry_worker_and_regeneration_keep_frozen_versions(
    runtime, number, requirements
):
    rt = runtime
    document, build = corpus(rt)
    reading = context_for(rt, document, build)
    rt.settings.chat_query_preparation_policy = f"anchored_reference_v{number}"
    receipt = send(rt, session(rt), reading, "What is photosynthesis in this selected passage?")
    with rt.db() as db:
        original = db.get(AnswerRequest, receipt["request_id"])
        frozen = deepcopy(original.command)
        assert frozen["preparation_version"] == f"conversation_preparer_v{number}"
        assert frozen["requirements_version"] == f"question_requirements_v{requirements}"
    call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
    rt.settings.chat_query_preparation_policy = f"anchored_reference_v{43 - number}"
    headers = {**rt.headers(), "Idempotency-Key": str(uuid4())}
    retried = call(
        rt, "POST", "/answer-requests/" + receipt["request_id"] + "/retry", {}, headers, 202
    )
    assert retried["request_id"] == receipt["request_id"]
    assert retried["job_id"] != receipt["job_id"]
    assert (
        call(rt, "POST", "/answer-requests/" + receipt["request_id"] + "/retry", {}, headers, 202)
        == retried
    )
    answer = finish(rt, retried)
    assert answer["response"]["response_type"] == "answer"
    assert answer["response"]["citations"]
    with rt.db() as db:
        original = db.get(AnswerRequest, receipt["request_id"])
        assert original.command == frozen
        assert (
            original.trace["prepared_query"]["preparation_version"] == frozen["preparation_version"]
        )
        assert original.trace["understanding"]["version"] == frozen["requirements_version"]
        assert original.budget["consumed_calls"] == 1
    headers["Idempotency-Key"] = str(uuid4())
    replacement = call(rt, "POST", "/answers/" + answer["id"] + "/regenerate", {}, headers, 202)
    with rt.db() as db:
        replay = db.get(AnswerRequest, replacement["request_id"])
        assert replay.command["preparation_version"] == frozen["preparation_version"]
        assert replay.command["requirements_version"] == frozen["requirements_version"]
        assert replay.context_snapshot_id == original.context_snapshot_id
    regenerated = finish(rt, replacement)
    assert regenerated["id"] != answer["id"]
    assert regenerated["response"]["response_type"] == "answer"
    with rt.db() as db:
        replay = db.get(AnswerRequest, replacement["request_id"])
        assert replay.trace["understanding"]["version"] == frozen["requirements_version"]
        assert (
            replay.trace["prepared_query"]["preparation_version"] == frozen["preparation_version"]
        )
        assert replay.budget["consumed_calls"] == 1


@pytest.mark.parametrize("number,count", [(21, 2), (22, 1)])
@pytest.mark.parametrize("energy", ["sunlight", "light"])
def test_current_reader_preference_classification_keeps_native_mock_refusal(
    runtime, number, count, energy
):
    rt = runtime
    document, build = corpus(rt)
    reading = context_for(rt, document, build)
    rt.settings.chat_query_preparation_policy = f"anchored_reference_v{number}"
    question = (
        "I prefer examples for photosynthesis. Explain how "
        + energy
        + " supplies energy for photosynthesis in the selected passage."
    )
    receipt = send(rt, session(rt), reading, question)
    answer = finish(rt, receipt)
    assert answer["response"]["response_type"] == "refusal"
    assert answer["response"]["citations"] == []
    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        understanding = request.trace["understanding"]
        assert len(understanding["required_knowledge"]) == count
        assert understanding["original_message"] == question
        assert understanding["required_knowledge"][-1]["id"] == "requirement_02"
        assert energy in understanding["required_knowledge"][-1]["request"]
        assert request.budget["consumed_calls"] == 1
        if number == 22:
            preference = understanding["presentation_requests"][-1]
            assert preference["kind"] == "response_style"
            assert preference["request"] == "I prefer examples for photosynthesis"
            assert preference["applies_to_requirement_ids"] == ["requirement_02"]
            assert understanding["required_knowledge"][0]["presentation_request_ids"] == [
                preference["id"]
            ]
        else:
            assert understanding["presentation_requests"] == []


def test_v22_unresolved_reference_remains_zero_call_clarification(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v22"
    receipt = submit(rt, session(rt), "What does this illustrate about a fixed action pattern?")
    answer = finish(rt, receipt)
    assert answer["response"]["response_type"] == "clarification"
    assert answer["response"]["citations"] == []
    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.command["preparation_version"] == "conversation_preparer_v22"
        assert request.budget["consumed_calls"] == 0


def test_v22_preserves_two_genuine_scientific_obligations(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v22"
    question = "Explain photosynthesis. Describe diffusion."
    receipt = submit(rt, session(rt), question)
    finish(rt, receipt)
    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        understanding = request.trace["understanding"]
        assert understanding["version"] == "question_requirements_v8"
        assert len(understanding["required_knowledge"]) == 2
        assert [point["id"] for point in understanding["required_knowledge"]] == [
            "requirement_01",
            "requirement_02",
        ]
        assert understanding["presentation_requests"] == []
        assert "preference_separation" not in understanding


@pytest.mark.parametrize("number,requirements", [(21, 7), (22, 8)])
def test_versioned_practice_goal_tutor_continues_through_native_publication(
    runtime, monkeypatch, number, requirements
):
    from sqlalchemy import select
    from .test_practice_goal_tutor import (
        test_goal_practice_hint_return_attempt_and_next_step_keep_the_goal as goal_journey,
    )

    runtime.settings.chat_query_preparation_policy = f"anchored_reference_v{number}"
    # This existing journey runs the actual API, jobs, SQL and publication guards
    # with explicitly authored checker wire responses. It is no model-quality label.
    goal_journey(runtime, monkeypatch)
    with runtime.db() as db:
        requests = list(db.scalars(select(AnswerRequest)))
        assert requests
        for request in requests:
            assert request.command["preparation_version"] == f"conversation_preparer_v{number}"
            assert (
                request.command["requirements_version"] == f"question_requirements_v{requirements}"
            )
            assert (
                request.trace["prepared_query"]["preparation_version"]
                == f"conversation_preparer_v{number}"
            )
            assert (
                request.trace["understanding"]["version"]
                == f"question_requirements_v{requirements}"
            )
