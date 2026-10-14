"""Current reader-to-learning continuity on authored sources and disposable SQL."""

import json
from uuid import uuid4

import pytest

from app.modules.answering.models import AnswerRequest
from .conftest import disposable_postgres_url
from .test_chat_runtime import call, corpus, finish, session, submit
from .test_learning_product import draft, published
from .test_practice_goal_tutor import goal_for, open_goal
from .test_reading_answer_core_v5 import context_for, send


@pytest.fixture
def postgres_url():
    """Keep memory settings and deliberately queued jobs out of other tests."""
    with disposable_postgres_url() as url:
        yield url


@pytest.fixture(autouse=True)
def forbid_external_model_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("This native mock journey must never contact a model provider")

    monkeypatch.setattr("generation.adapters.open_provider", forbidden)
    monkeypatch.setattr("generation.adapters.LLMAdapter._call", forbidden)


def reader_answer(rt):
    rt.settings.chat_query_preparation_policy = "anchored_reference_v21"
    document, build = corpus(rt)
    reading = context_for(rt, document, build)
    current = session(rt)
    receipt = send(rt, current, reading, "What is photosynthesis in this selected passage?")
    answer = finish(rt, receipt)
    assert answer["response"]["response_type"] == "answer"
    assert answer["response"]["citations"] and answer["model_mode"] == "mock"
    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.command["requirements_version"] == "question_requirements_v7"
        assert request.trace["understanding"]["version"] == "question_requirements_v7"
        assert request.state == "answered"
    units = call(rt, "GET", f"/learning/library/{document['id']}/units")["items"]
    unit = next(value for value in units if value["id"] == reading["source_unit_id"])
    return document, current, unit, answer


def test_current_reader_answer_continues_through_owned_learning_and_revocation(runtime):
    rt = runtime
    document, current, unit, answer = reader_answer(rt)
    owner = rt.headers()
    other = rt.headers("student2@example.com")
    admin = rt.headers("admin@example.com")
    state = call(rt, "GET", "/me/memory/settings")
    call(
        rt,
        "PATCH",
        "/me/memory/settings",
        {"enabled": True, "version": state["version"]},
    )
    call(
        rt,
        "PUT",
        "/learning/reading-position",
        {"source": unit["locator"], "char_offset": 5, "expected_version": 0},
    )
    assert any(
        position["char_offset"] == 5 for position in call(rt, "GET", "/learning/reading-position")
    )
    item = published(rt, draft(rt, unit))["item"]
    goal = goal_for(rt, item, title="Current reader continuity")
    note = call(
        rt,
        "POST",
        "/learning/notes",
        {
            "title": "Current reader explanation",
            "content": "Review the energy input in this saved explanation.",
            "source": unit["locator"],
            "answer_id": answer["id"],
            "goal_id": goal["id"],
            "concepts": ["photosynthesis"],
        },
        status=201,
    )
    call(rt, "GET", f"/learning/goals/{goal['id']}", headers=other, status=404)
    call(
        rt,
        "PATCH",
        f"/learning/notes/{note['id']}",
        {"expected_version": note["version"], "content": "Foreign overwrite"},
        other,
        404,
    )
    assert "Foreign overwrite" not in call(rt, "GET", "/learning/notes/export")["markdown"]

    opened = open_goal(rt, item, 0, goal["id"])
    hint = call(
        rt,
        "POST",
        f"/sessions/{opened['session_id']}/messages",
        {
            "content": "Help me with the current practice step without giving the answer.",
            "teaching_mode": "hint",
            "task_action": "continue",
            "task_id": opened["task_id"],
            "task_version": opened["task_version"],
            "use_profile": False,
        },
        {**owner, "Idempotency-Key": str(uuid4())},
        202,
    )
    assert rt.work()
    failed = call(rt, "GET", "/jobs/" + hint["job_id"])
    assert failed["state"] == "failed" and failed["answer_id"] is None
    assert failed["error"]["code"] == "SEMANTIC_CHECK_UNAVAILABLE"
    assert call(rt, "GET", f"/learning/goals/{goal['id']}")["units"][0]["attempts"] == 0
    call(rt, "GET", "/admin/failures/" + hint["request_id"], headers=admin)
    call(rt, "GET", "/admin/failures/" + hint["request_id"], headers=owner, status=403)

    wrong_body = {
        "idempotency_key": str(uuid4()),
        "expected_version": 0,
        "goal_id": goal["id"],
        "response": {"selection": ["B"]},
    }
    wrong = call(rt, "POST", f"/learning/practice/{item['id']}/attempts", wrong_body)
    assert wrong["feedback"]["outcome"] == "incorrect"
    assert call(rt, "POST", f"/learning/practice/{item['id']}/attempts", wrong_body) == wrong
    memory = next(
        value
        for value in call(rt, "GET", "/me/memories")
        if value["provenance"].get("practice_attempt_id") == wrong["id"]
    )
    assert memory["category"] == "assessment_performance"
    assert "PRIVATE_ANSWER_SENTINEL" not in json.dumps(memory)
    assert all(
        value["id"] != memory["id"] for value in call(rt, "GET", "/me/memories", headers=other)
    )
    progress = call(rt, "GET", f"/learning/practice/{item['id']}/progress")
    assert progress["full_explanation"] is None
    correct = call(
        rt,
        "POST",
        f"/learning/practice/{item['id']}/attempts",
        {
            "idempotency_key": str(uuid4()),
            "expected_version": progress["version"],
            "goal_id": goal["id"],
            "response": {"selection": ["A"]},
        },
    )
    assert correct["feedback"]["outcome"] == "correct"
    unit_progress = call(rt, "GET", f"/learning/goals/{goal['id']}")["units"][0]
    assert unit_progress["attempts"] == 2 and unit_progress["correct_attempts"] == 1
    assert (
        open_goal(rt, item, correct["progress_version"], goal["id"])["task_id"] == opened["task_id"]
    )

    card = call(rt, "POST", f"/learning/notes/{note['id']}/review-card", status=201)
    review = next(
        value for value in call(rt, "GET", "/learning/review") if value["note_id"] == card["id"]
    )
    recorded = call(
        rt,
        "POST",
        f"/learning/review/{review['id']}/record",
        {"expected_version": review["version"], "outcome": "recalled"},
    )
    assert (
        recorded["correct_count"] == 1
        and "No graded mastery inferred" in recorded["scheduling_reason"]
    )
    export = call(rt, "GET", "/learning/notes/export")["markdown"]
    assert answer["id"] in export and document["title"] in export
    assert "PRIVATE_ANSWER_SENTINEL" not in export
    assert rt.client.get("/api/v1/learning/notes/export.docx", headers=owner).status_code == 200

    cancelled = submit(rt, current, "What is photosynthesis?")
    call(rt, "POST", "/jobs/" + cancelled["job_id"] + "/cancel", headers=owner)
    assert call(rt, "GET", "/jobs/" + cancelled["job_id"])["state"] == "cancelled"
    assert call(rt, "GET", "/answers/" + answer["id"])["response"] == answer["response"]
    call(rt, "POST", "/documents/" + document["id"] + "/revoke", headers=admin)
    withdrawn = call(rt, "GET", "/learning/notes/export")["markdown"]
    assert "A saved answer citation is currently unavailable." in withdrawn
    assert document["title"] not in withdrawn
    assert all(
        value["note_id"] != card["id"]
        for value in call(rt, "GET", "/learning/review?due_only=false")
    )
    call(
        rt,
        "GET",
        f"/answers/{answer['id']}/evidence/{answer['response']['citations'][0]}",
        status=410,
    )


def test_complex_selected_request_preserves_native_mock_limit_without_false_answer(
    runtime,
):
    rt = runtime
    rt.settings.chat_query_preparation_policy = "anchored_reference_v21"
    document, build = corpus(rt)
    question = (
        "I prefer examples for photosynthesis. Explain how sunlight supplies energy "
        "for photosynthesis in the selected passage."
    )
    receipt = send(rt, session(rt), context_for(rt, document, build), question)
    answer = finish(rt, receipt)
    assert answer["model_mode"] == "mock"
    assert answer["response"]["response_type"] == "refusal"
    assert answer["response"]["refusal_reason"] == "INSUFFICIENT_EVIDENCE"
    assert answer["response"]["citations"] == []
    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.state == "refused"
        assert request.command["requirements_version"] == "question_requirements_v7"
