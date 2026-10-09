"""HTTP task ownership/revision fences and durable attempt snapshots in PostgreSQL."""

from uuid import uuid4
from unittest.mock import patch

import pytest

from app.modules.answering.models import AnswerRequest
from app.modules.learning_state.models import LearningTask
from .test_chat_runtime import call, corpus, session
from .test_learning_state import execute, send


def pending_question(rt, expected_kind="concept"):
    """An explicit persisted tutor-question fixture isolates task routing from provider quality."""
    corpus(rt)
    owned_session = session(rt)
    first = send(rt, owned_session, "Compare diffusion and osmosis.")
    answer = execute(rt, first)
    with rt.db() as db:
        task = db.get(LearningTask, answer["task_id"])
        task.pending_tutor_question_id = str(uuid4())
        task.pending_tutor_question = "Which process specifically involves water?"
        task.pending_tutor_question_version = 1
        task.expected_response_kind = expected_kind
        task.teaching_mode = "hint"
        task.help_level = 1
        db.commit()
    public = call(rt, "GET", f"/sessions/{owned_session['id']}/learning-tasks")
    return owned_session, next(item for item in public if item["id"] == answer["task_id"]), answer


def binding(task):
    return {
        "task_id": task["id"],
        "task_version": task["version"],
        "pending_tutor_question_id": task["pending_tutor_question_id"],
        "pending_tutor_question_version": task["pending_tutor_question_version"],
    }


@pytest.mark.parametrize(
    "text,kind",
    [
        ("Osmosis.", "concept"),
        ("Diffusion.", "concept"),
        ("Not osmosis.", "concept"),
        ("I think it is osmosis. Water crosses a membrane.", "explanation"),
        ("-2.5 mol", "numeric"),
    ],
)
def test_http_attempt_freezes_original_problem_pending_question_and_depth(runtime, text, kind):
    rt = runtime
    owned_session, task, answer = pending_question(rt, kind)
    saved_answer = call(rt, "GET", f"/answers/{answer['id']}")
    assert (
        saved_answer["learning_task"]["pending_tutor_question_id"]
        == task["pending_tutor_question_id"]
    )
    receipt = send(rt, owned_session, text, **binding(task))
    with rt.db() as db:
        frozen = db.get(AnswerRequest, receipt["request_id"]).command["teaching_context"]
        assert frozen["task_id"] == task["id"]
        assert frozen["question"] == "Compare diffusion and osmosis."
        assert frozen["turn_role"] == "learner_attempt" and frozen["learner_attempt"] == text
        assert frozen["help_level"] == 1 and frozen["current_step"] == 1
        assert frozen["pending_tutor_question"] == task["pending_tutor_question"]
    call(rt, "POST", f"/jobs/{receipt['job_id']}/cancel", {})


def test_repeated_attempt_is_frozen_and_worker_selects_feedback_then_smaller_step(runtime):
    rt = runtime
    owned_session, task, _ = pending_question(rt)
    prior = [
        {"status": "incorrect", "feedback": "Review the requested process."},
        {"status": "partial", "feedback": "Add the direction of movement."},
    ]
    with patch("app.modules.learning_state.tasks.recent_attempt_feedback", return_value=prior):
        receipt = send(rt, owned_session, "The membrane itself moves.", **binding(task))
    try:
        with rt.db() as db:
            frozen = db.get(AnswerRequest, receipt["request_id"]).command
            assert frozen["generation_policy"]["version"] == "generation_controls_v10"
            assert frozen["teaching_context"]["attempt_history"] == prior
            assert frozen["teaching_context"]["turn_role"] == "learner_attempt"
        assert rt.work()
        with rt.db() as db:
            request = db.get(AnswerRequest, receipt["request_id"])
            plan = request.trace["progress_plan"]
            assert plan["version"] == "progress_action_plan_v10"
            assert plan["action"] == "assess_then_guarded_small_step"
            assert plan["exact_given_guard"] is True
            assert plan["repeated_difficulty"] is True
            assert plan["allowed_disclosure"]["help_level"] == 1
        detail = call(
            rt,
            "GET",
            "/admin/failures/" + receipt["request_id"],
            headers=rt.headers("admin@example.com"),
        )
        assert detail["processing"]["progress_plan"]["action"] == "assess_then_guarded_small_step"
    finally:
        # Preserve queue isolation if an assertion fails before this test's worker turn.
        job = call(rt, "GET", "/jobs/" + receipt["job_id"])
        if job["state"] in {"queued", "running", "retry_wait"}:
            cancelled = call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
            assert cancelled["state"] == "cancelled"


def test_http_rejects_stale_question_and_foreign_task_without_creating_message(runtime):
    rt = runtime
    owned_session, task, _ = pending_question(rt)
    before = call(rt, "GET", f"/sessions/{owned_session['id']}/messages")["items"]
    for changed in (
        {"task_version": task["version"] + 1},
        {"pending_tutor_question_id": str(uuid4())},
        {"pending_tutor_question_version": task["pending_tutor_question_version"] + 1},
    ):
        call(
            rt,
            "POST",
            f"/sessions/{owned_session['id']}/messages",
            {"content": "Osmosis.", **binding(task), **changed},
            {**rt.headers(), "Idempotency-Key": str(uuid4())},
            409,
        )
    other = session(rt)
    call(
        rt,
        "POST",
        f"/sessions/{other['id']}/messages",
        {"content": "Osmosis.", **binding(task)},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        404,
    )
    after = call(rt, "GET", f"/sessions/{owned_session['id']}/messages")["items"]
    assert [item["id"] for item in before] == [item["id"] for item in after]


@pytest.mark.parametrize(
    "text,action,expected_mode,same_task",
    [
        ("Please give the full explanation.", "full_explanation", "direct", True),
        ("What is photosynthesis?", "auto", "direct", False),
        ("A new problem: calculate 3 plus 2.", "new", "direct", False),
    ],
)
def test_http_explicit_full_and_new_problem_take_priority(
    runtime, text, action, expected_mode, same_task
):
    rt = runtime
    owned_session, task, _ = pending_question(rt)
    receipt = send(rt, owned_session, text, task_action=action, **binding(task))
    with rt.db() as db:
        frozen = db.get(AnswerRequest, receipt["request_id"]).command["teaching_context"]
        assert (frozen["task_id"] == task["id"]) is same_task
        assert frozen["teaching_mode"] == expected_mode
        assert frozen["turn_role"] == "user_question"
    call(rt, "POST", f"/jobs/{receipt['job_id']}/cancel", {})
