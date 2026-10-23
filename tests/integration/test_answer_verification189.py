"""Checkbox choice survives real API, durable jobs and disposable PostgreSQL.

These authored local-source cases test persistence and publication boundaries.
Mock transport is not scientific checking or live-model qualification.
"""

from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.base import utcnow
from app.modules.answering import service
from app.modules.answering.models import Answer, AnswerRequest, Job, Message
from app.modules.learning_state.models import LearningTask, PrivateAnswerDraft
from app.worker import recover_stale
from generation import GenerationService

from .test_chat_runtime import call, corpus, finish, session
from .test_pending_tutor_question import binding, pending_question
from .test_practice_goal_tutor import goal_for, open_goal
from .test_practice_tutor import fixture_item, open_tutor


QUESTION = "What is photosynthesis?"
OMITTED = object()


@pytest.fixture(autouse=True)
def close_own_unfinished_jobs(runtime):
    """The shared fixture database must not retain this file's queued work."""
    with runtime.db() as db:
        before = set(db.scalars(select(Job.id)))
    yield
    with runtime.db() as db:
        for job in db.scalars(select(Job).where(Job.state.in_(service.ACTIVE))):
            if job.id not in before:
                service.cancel_job(db, job)
        db.commit()


def send(rt, chat, check_answer=OMITTED, *, key=None, text=QUESTION, **values):
    body = {"content": text, "use_profile": False, **values}
    if check_answer is not OMITTED:
        body["check_answer"] = check_answer
    return call(
        rt,
        "POST",
        f"/sessions/{chat['id']}/messages",
        body,
        {**rt.headers(), "Idempotency-Key": key or str(uuid4())},
        202,
    )


def frozen(rt, receipt, mode, requested):
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        command = deepcopy(req.command)
        assert command["verification_mode"] == mode
        assert command["check_requested"] is (mode == "verified")
        assert command["requested_check_answer"] is requested
        assert command["teaching_context"]["verification_mode"] == mode
        assert req.trace["verification_mode"] == mode
        assert req.trace["check_requested"] is (mode == "verified")
        return command


@pytest.mark.parametrize(
    "requested,mode,status",
    [
        (OMITTED, "verified", "not_performed"),
        (True, "verified", "not_performed"),
        (False, "fast", "not_requested"),
    ],
)
def test_checkbox_freezes_through_worker_answer_and_reloaded_history(
    runtime, requested, mode, status
):
    rt = runtime
    corpus(rt)
    chat = session(rt)
    receipt = send(rt, chat, requested)
    frozen(rt, receipt, mode, None if requested is OMITTED else requested)
    assert receipt["verification_mode"] == mode
    assert receipt["check_requested"] is (mode == "verified")
    queued = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert queued["verification_mode"] == mode
    answer = finish(rt, receipt)
    assert answer["verification_mode"] == mode
    assert answer["check_requested"] is (mode == "verified")
    assert answer["check_executed"] is False
    assert answer["verification_status"] == status
    assert answer["response"]["response_type"] == "answer"
    assert answer["evidence"] and answer["response"]["citations"]
    reloaded = call(rt, "GET", f"/sessions/{chat['id']}/messages")
    assert reloaded["items"][-1]["answer"] == answer
    completed = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert completed["verification_mode"] == mode
    assert completed["check_requested"] is (mode == "verified")
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.trace["verification_mode"] == mode
        assert req.trace["check_requested"] is (mode == "verified")
        assert req.trace["check_executed"] is False
        assert req.trace["verification_status"] == status
        assert req.budget["consumed_calls"] == 1
        assert not list(
            db.scalars(
                select(PrivateAnswerDraft).where(
                    PrivateAnswerDraft.request_id == req.id,
                    PrivateAnswerDraft.phase == "online_check",
                )
            )
        )


def test_omitted_legacy_and_explicit_true_share_identity_false_conflicts(runtime):
    rt = runtime
    chat = session(rt)
    key = str(uuid4())
    receipt = send(rt, chat, key=key, text="Hello")
    assert send(rt, chat, True, key=key, text="Hello") == receipt
    call(
        rt,
        "POST",
        f"/sessions/{chat['id']}/messages",
        {"content": "Hello", "use_profile": False, "check_answer": False},
        {**rt.headers(), "Idempotency-Key": key},
        409,
    )
    frozen(rt, receipt, "verified", None)


def test_false_identity_cannot_be_reused_with_checked_choice(runtime):
    rt = runtime
    chat = session(rt)
    key = str(uuid4())
    receipt = send(rt, chat, False, key=key, text="Hello")
    assert send(rt, chat, False, key=key, text="Hello") == receipt
    call(
        rt,
        "POST",
        f"/sessions/{chat['id']}/messages",
        {"content": "Hello", "use_profile": False, "check_answer": True},
        {**rt.headers(), "Idempotency-Key": key},
        409,
    )
    frozen(rt, receipt, "fast", False)


@pytest.mark.parametrize("requested", [False, True])
def test_cancel_retry_regenerate_and_later_settings_keep_frozen_choice(runtime, requested):
    rt = runtime
    corpus(rt)
    chat = session(rt)
    receipt = send(rt, chat, requested)
    mode = "verified" if requested else "fast"
    before = frozen(rt, receipt, mode, requested)
    call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
    # A later checkbox selection belongs to its own request, not the queued one.
    other = send(rt, session(rt), not requested)
    other_mode = "fast" if requested else "verified"
    frozen(rt, other, other_mode, not requested)
    call(rt, "POST", "/jobs/" + other["job_id"] + "/cancel", {})
    retried = call(
        rt,
        "POST",
        "/answer-requests/" + receipt["request_id"] + "/retry",
        {},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    assert retried["request_id"] == receipt["request_id"]
    assert retried["job_id"] != receipt["job_id"]
    assert frozen(rt, retried, mode, requested) == before
    rt.settings.llm_provider = "local"
    rt.settings.llm_model = "later-settings-must-not-rebind-frozen-request"
    answer = finish(rt, retried)
    assert answer["model_mode"] == "mock" and answer["verification_mode"] == mode
    regenerated = call(
        rt,
        "POST",
        "/answers/" + answer["id"] + "/regenerate",
        {},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    assert regenerated["request_id"] != receipt["request_id"]
    after = frozen(rt, regenerated, mode, requested)
    assert after["model_config"] == before["model_config"]
    replacement = finish(rt, regenerated)
    assert replacement["verification_mode"] == mode
    assert replacement["message_id"] == answer["message_id"]
    historical = call(rt, "GET", "/answers/" + answer["id"])
    assert historical["verification_mode"] == mode
    assert historical["verification_status"] == answer["verification_status"]


@pytest.mark.parametrize("requested", [False, True])
def test_stale_worker_recovery_preserves_frozen_request_without_automatic_replay(
    runtime, requested
):
    rt = runtime
    chat = session(rt)
    receipt = send(rt, chat, requested, text="Hello")
    mode = "verified" if requested else "fast"
    before = frozen(rt, receipt, mode, requested)
    with rt.db() as db:
        job = db.get(Job, receipt["job_id"])
        job.state = "running"
        job.execution_token = str(uuid4())
        job.updated_at = utcnow() - timedelta(minutes=5)
        db.commit()
    assert recover_stale(rt.engine, 60) == 1
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed" and job["error"]["code"] == "WORKER_INTERRUPTED"
    assert job["verification_mode"] == mode and job["answer_id"] is None
    assert frozen(rt, receipt, mode, requested) == before
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).budget["consumed_calls"] == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(Answer)
                .where(Answer.request_id == receipt["request_id"])
            )
            == 0
        )


def test_checkbox_does_not_grant_cross_owner_access(runtime):
    rt = runtime
    corpus(rt)
    chat = session(rt)
    receipt = send(rt, chat, False)
    other = rt.headers("student2@example.com")
    call(rt, "GET", "/jobs/" + receipt["job_id"], headers=other, status=404)
    call(rt, "GET", f"/sessions/{chat['id']}/messages", headers=other, status=404)
    call(
        rt,
        "POST",
        f"/sessions/{chat['id']}/messages",
        {"content": QUESTION, "check_answer": False},
        {**other, "Idempotency-Key": str(uuid4())},
        404,
    )
    answer = finish(rt, receipt)
    call(rt, "GET", "/answers/" + answer["id"], headers=other, status=404)
    call(
        rt,
        "POST",
        "/answers/" + answer["id"] + "/regenerate",
        {},
        {**other, "Idempotency-Key": str(uuid4())},
        404,
    )
    call(rt, "GET", "/documents", status=403)


def test_fast_retains_current_source_fence_before_publication(runtime, monkeypatch):
    rt = runtime
    document, _ = corpus(rt)
    receipt = send(rt, session(rt), False)
    generate = GenerationService.generate
    generated = []

    def revoke_after_generation(self, request, *args, **kwargs):
        result = generate(self, request, *args, **kwargs)
        assert result.response and not result.error
        generated.append(request.request_id)
        call(
            rt,
            "POST",
            "/documents/" + document["id"] + "/revoke",
            {},
            rt.headers("admin@example.com"),
        )
        return result

    monkeypatch.setattr(GenerationService, "generate", revoke_after_generation)
    assert rt.work()
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert generated == [receipt["request_id"]]
    assert job["state"] == "failed" and job["error"]["code"] == "SOURCE_UNAVAILABLE"
    assert job["answer_id"] is None
    with rt.db() as db:
        assert (
            db.scalar(select(Answer.id).where(Answer.request_id == receipt["request_id"])) is None
        )


def test_fast_history_and_evidence_keep_revocation_semantics(runtime):
    rt = runtime
    document, _ = corpus(rt)
    answer = finish(rt, send(rt, session(rt), False))
    cid = answer["response"]["citations"][0]
    call(
        rt, "POST", "/documents/" + document["id"] + "/revoke", {}, rt.headers("admin@example.com")
    )
    call(rt, "GET", f"/answers/{answer['id']}/evidence/{cid}", status=410)
    saved = call(rt, "GET", "/answers/" + answer["id"])
    assert saved["response"] == answer["response"]
    assert saved["verification_mode"] == "fast"
    assert saved["verification_status"] == "not_requested"


@pytest.mark.usefixtures("scripted_semantic_checker")
def test_unchecked_checkbox_cannot_disable_an_explicit_hint_check(runtime):
    rt = runtime
    receipt = send(rt, session(rt), False, teaching_mode="hint")
    frozen(rt, receipt, "verified", False)
    call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})


@pytest.mark.usefixtures("scripted_semantic_checker")
def test_unchecked_checkbox_cannot_disable_effective_pending_attempt_check(runtime):
    rt = runtime
    chat, task, _ = pending_question(rt)
    receipt = send(rt, chat, False, text="Osmosis.", **binding(task))
    command = frozen(rt, receipt, "verified", False)
    assert command["teaching_context"]["turn_role"] == "learner_attempt"
    assert (
        command["teaching_context"]["pending_tutor_question_id"]
        == task["pending_tutor_question_id"]
    )
    with rt.db() as db:
        unchanged = db.get(LearningTask, task["id"])
        assert unchanged.current_step == task["current_step"]
        assert unchanged.last_attempt_evaluation is None
    call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})


@pytest.mark.parametrize("with_goal", [False, True])
@pytest.mark.usefixtures("scripted_semantic_checker")
def test_unchecked_checkbox_cannot_disable_practice_or_goal_checks(runtime, with_goal):
    rt = runtime
    item = fixture_item(rt, "step")
    if with_goal:
        goal = goal_for(rt, item)
        opened = open_goal(rt, item, 0, goal["id"])
    else:
        opened = open_tutor(rt, item, 0)
    before = call(rt, "GET", f"/learning/practice/{item['id']}/progress")
    receipt = send(
        rt,
        {"id": opened["session_id"]},
        False,
        text="Help me with the current step without giving the answer.",
        task_action="continue",
        task_id=opened["task_id"],
        task_version=opened["task_version"],
    )
    command = frozen(rt, receipt, "verified", False)
    assert command["teaching_context"]["practice_context"]
    if with_goal:
        assert (
            command["teaching_context"]["requirements"]["practice_goal_context"]["goal_id"]
            == goal["id"]
        )
    after = call(rt, "GET", f"/learning/practice/{item['id']}/progress")
    assert after == before
    call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})


def test_nonboolean_or_alternative_selector_cannot_create_work(runtime):
    rt = runtime
    chat = session(rt)
    for extra in ({"check_answer": "false"}, {"check_answer": 0}, {"verification_mode": "fast"}):
        call(
            rt,
            "POST",
            f"/sessions/{chat['id']}/messages",
            {"content": QUESTION, **extra},
            {**rt.headers(), "Idempotency-Key": str(uuid4())},
            422,
        )
    with rt.db() as db:
        assert not list(db.scalars(select(Message).where(Message.session_id == chat["id"])))
        assert not list(
            db.scalars(select(AnswerRequest).where(AnswerRequest.session_id == chat["id"]))
        )
