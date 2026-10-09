"""Practice/chat transitions with migrated PostgreSQL and authored isolated sources."""

import copy
import json
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.core.exceptions import AppError
from sqlalchemy import select
from app.modules.answering.models import Answer, AnswerRequest, Job
from app.modules.learning_product import tutoring
from app.modules.learning_state import tasks
from app.modules.learning_state.models import LearningTask
from .test_chat_runtime import call
from .test_learning_product import (
    source,
    draft,
    published,
    student_id,
    use_scripted_practice_grader,
    applied_practice_feedback,
)


def fixture_item(rt, kind="mcq"):
    _, unit = source(rt)
    value = draft(rt, unit)
    if kind == "step":
        value.update(
            kind="step",
            options=[],
            rubric={
                "steps": [
                    {
                        "id": "step1",
                        "prompt": "Name the energy input.",
                        "required_points": [{"id": "p1", "terms": ["light"]}],
                        "hints": ["Think about the energy reaching a leaf."],
                    },
                    {
                        "id": "step2",
                        "prompt": "Name the energy store.",
                        "required_points": [{"id": "p2", "terms": ["sugars"]}],
                        "hints": ["Look for the stored chemical material."],
                    },
                ],
                "explanation": "PRIVATE_ANSWER_SENTINEL Light energy is stored in sugars.",
            },
        )
    return published(rt, value)["item"]


def open_tutor(rt, item, version):
    return call(rt, "POST", f"/learning/practice/{item['id']}/tutor", {"expected_version": version})


def attempt(rt, item, version, **response):
    return call(
        rt,
        "POST",
        f"/learning/practice/{item['id']}/attempts",
        {"idempotency_key": str(uuid4()), "expected_version": version, "response": response},
    )


def test_practice_bridge_reuses_owned_task_preserves_attempts_and_disclosures(runtime):
    item = fixture_item(runtime)
    attempt(runtime, item, 0, selection=["B"])
    progress = call(
        runtime,
        "POST",
        f"/learning/practice/{item['id']}/help",
        {"action": "hint", "expected_version": 1},
    )
    opened = open_tutor(runtime, item, progress["version"])
    assert open_tutor(runtime, item, progress["version"]) == opened
    assert opened["teaching_mode"] == "hint"
    with runtime.db() as db:
        task = db.get(LearningTask, opened["task_id"])
        private_free = task.requirements["practice_context"]
        assert private_free["recent_attempts"][0]["response"]["selection"] == ["B"]
        assert private_free["shown_hints"] == progress["hints"]
        assert "PRIVATE_ANSWER_SENTINEL" not in json.dumps(private_free)
        assert "correct_option_ids" not in json.dumps(private_free) and "rubric" not in private_free
        context = {
            "task_id": task.id,
            "task_version": task.version,
            "exposure_epoch": task.exposure_epoch,
            "practice_context": copy.deepcopy(private_free),
        }
        tasks.validate_task(db, student_id(runtime), context)
        history = tasks.recent_attempt_feedback(db, student_id(runtime), task.id)
        assert (
            history[0]["status"] == "incorrect"
            and history[0]["basis"] == "deterministic_practice_rules"
        )
        assert (
            tutoring.disclosure_turns(private_free)[0]["response"]["answer_text"]
            == progress["hints"][0]
        )
    reflected = call(runtime, "GET", f"/learning/practice/{item['id']}/progress")
    assert (
        reflected["tutor_task_id"] == opened["task_id"]
        and reflected["tutor_session_id"] == opened["session_id"]
    )
    call(
        runtime,
        "GET",
        f"/sessions/{opened['session_id']}/learning-tasks",
        headers=runtime.headers("student2@example.com"),
        status=404,
    )
    call(
        runtime,
        "POST",
        f"/learning/practice/{item['id']}/tutor",
        {"expected_version": 0},
        status=409,
    )


def test_actual_practice_step_refreshes_task_and_fences_stale_chat(runtime, monkeypatch):
    use_scripted_practice_grader(monkeypatch)
    item = fixture_item(runtime, "step")
    opened = open_tutor(runtime, item, 0)
    receipt = call(
        runtime,
        "POST",
        f"/sessions/{opened['session_id']}/messages",
        {
            "content": "Help me with this step.",
            "teaching_mode": "hint",
            "task_action": "continue",
            "task_id": opened["task_id"],
            "task_version": opened["task_version"],
            "use_profile": False,
        },
        {**runtime.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    with runtime.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        frozen = copy.deepcopy(request.command["teaching_context"])
        assert frozen["current_step"] == 1 and frozen["practice_context"]["progress_version"] == 0
    recorded = attempt(runtime, item, 0, text="light", step=1)
    assert applied_practice_feedback(recorded)["outcome"] == "correct"
    with runtime.db() as db:
        task = db.get(LearningTask, opened["task_id"])
        assert task.current_step == 2 and task.pending_tutor_question == "Name the energy store."
        assert task.requirements["practice_context"]["recent_attempts"] == []
        with pytest.raises(AppError, match="learning task changed"):
            tasks.validate_task(db, student_id(runtime), frozen)
    assert runtime.work()
    job = call(runtime, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed" and job["answer_id"] is None
    assert (
        open_tutor(runtime, item, recorded["assessment"]["applied_progress_version"])["task_id"]
        == opened["task_id"]
    )


def test_chat_feedback_never_advances_recorded_practice_step(runtime):
    item = fixture_item(runtime, "step")
    opened = open_tutor(runtime, item, 0)
    with runtime.db() as db:
        task = db.get(LearningTask, opened["task_id"])
        context = {
            "task_id": task.id,
            "help_level": 1,
            "teaching_mode": "hint",
            "turn_role": "learner_attempt",
            "current_step": 1,
            "pending_tutor_question_id": task.pending_tutor_question_id,
            "pending_tutor_question_version": task.pending_tutor_question_version,
        }
        response = SimpleNamespace(
            teaching_context={
                "learner_attempt_evaluation": {
                    "status": "correct",
                    "feedback": "That is consistent with the source.",
                },
                "tutor_question": {
                    "question": "Can you explain your reasoning?",
                    "expected_response_kind": "explanation",
                },
            },
            response={
                "response_type": "answer",
                "answer_text": "That is consistent with the source. Can you explain your reasoning?",
            },
            model_mode="live",
            token_budget={"reliability_policy": "evidence_reliability_v5"},
        )
        tasks.publish_task(db, context, response)
        assert task.current_step == 1 and task.last_attempt_evaluation["basis"] == "model_feedback"
        db.commit()
    progress = call(runtime, "GET", f"/learning/practice/{item['id']}/progress")
    assert progress["current_step"] == 1 and progress["version"] == 0 and progress["attempts"] == []


def test_generic_practice_hint_uses_public_problem_for_actual_retrieval(runtime):
    item = fixture_item(runtime)
    opened = open_tutor(runtime, item, 0)
    question = "Help me with the current practice step without giving the answer."
    receipt = call(
        runtime,
        "POST",
        f"/sessions/{opened['session_id']}/messages",
        {
            "content": question,
            "teaching_mode": "hint",
            "task_action": "continue",
            "task_id": opened["task_id"],
            "task_version": opened["task_version"],
            "use_profile": False,
        },
        {**runtime.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    with runtime.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.command["question"] == question
        assert request.command["practice_query_policy"] == "owned_public_practice_query_v1"
        assert request.command["repair_policy"] == "practice_hint_repair_v5"
    assert runtime.work()
    with runtime.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.trace["prepared_query"]["original_message"] == question
        assert "energy input" in request.trace["prepared_query"]["standalone_query"]
        assert request.trace["retrieval_candidates"]
        resolution = request.trace["understanding"]["practice_reference_resolution"]
        assert resolution["learner_request"] == question
        assert resolution["source_unit_id"] == item["source"]["source_unit_id"]
        assert "PRIVATE_ANSWER_SENTINEL" not in json.dumps(request.trace["understanding"])


def test_current_v10_owned_practice_goal_reaches_worker_without_advancing_practice(runtime):
    item = fixture_item(runtime, "step")
    opened = open_tutor(runtime, item, 0)
    receipt = call(
        runtime,
        "POST",
        f"/sessions/{opened['session_id']}/messages",
        {
            "content": "Help me with the current step without giving the answer.",
            "teaching_mode": "hint",
            "task_action": "continue",
            "task_id": opened["task_id"],
            "task_version": opened["task_version"],
            "use_profile": False,
        },
        {**runtime.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    try:
        with runtime.db() as db:
            request = db.get(AnswerRequest, receipt["request_id"])
            frozen = copy.deepcopy(request.command["teaching_context"])
            assert request.command["generation_policy"]["version"] == "generation_controls_v10"
            assert frozen["practice_context"]["current_step_prompt"] == "Name the energy input."
            assert frozen["pending_tutor_question"] == "Name the energy input."
        assert runtime.work()
        job = call(runtime, "GET", "/jobs/" + receipt["job_id"])
        assert job["state"] == "failed", job
        assert job["error"]["code"] == "SEMANTIC_CHECK_UNAVAILABLE"
        assert job["answer_id"] is None
        with runtime.db() as db:
            request = db.get(AnswerRequest, receipt["request_id"])
            stored_job = db.get(Job, receipt["job_id"])
            assert stored_job.error["code"] == "SEMANTIC_CHECK_UNAVAILABLE"
            assert request.state == "error"
            assert request.budget["consumed_calls"] == 0
            assert request.assistant_message_id is None
            assert (
                db.scalar(select(Answer.id).where(Answer.request_id == receipt["request_id"]))
                is None
            )
            plan = request.trace["progress_plan"]
            assert plan["version"] == "progress_action_plan_v10"
            assert plan["current_step"] == frozen["practice_context"]["current_step"] == 1
            assert plan["current_question"] == frozen["pending_tutor_question"]
            assert plan["recorded_step_goal"]["operation"] == "Name the energy input."
            assert plan["recorded_step_goal"]["answer_key_used"] is False
            assert plan["action"] == "support_pending_question"
            assert plan["allowed_disclosure"]["help_level"] == 1
            assert plan["allowed_disclosure"]["complete_answer_allowed"] is False
            assert "PRIVATE_ANSWER_SENTINEL" not in json.dumps(plan)
        progress = call(runtime, "GET", f"/learning/practice/{item['id']}/progress")
        assert progress["current_step"] == 1 and progress["version"] == 0
    finally:
        job = call(runtime, "GET", "/jobs/" + receipt["job_id"])
        if job["state"] in {"queued", "running", "retry_wait"}:
            cancelled = call(runtime, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
            assert cancelled["state"] == "cancelled"


@pytest.mark.parametrize("saved_policy", ["claim_patch_repair_v3", "practice_hint_repair_v4"])
def test_existing_practice_request_retains_its_saved_repair_policy(runtime, saved_policy):
    item = fixture_item(runtime)
    opened = open_tutor(runtime, item, 0)
    receipt = call(
        runtime,
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
        {**runtime.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    with runtime.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        historical = copy.deepcopy(request.command)
        historical["repair_policy"] = saved_policy
        request.command = historical
        db.commit()
    assert runtime.work()
    with runtime.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.command["repair_policy"] == saved_policy
        assert request.command["question"] == historical["question"]


def test_practice_hint_successor_does_not_change_ordinary_or_direct_frozen_policy(runtime):
    ordinary = call(runtime, "POST", "/sessions", {"title": "Ordinary complete answer"})
    ordinary_receipt = call(
        runtime,
        "POST",
        f"/sessions/{ordinary['id']}/messages",
        {"content": "Explain photosynthesis.", "use_profile": False},
        {**runtime.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    call(runtime, "POST", "/jobs/" + ordinary_receipt["job_id"] + "/cancel", {})
    with runtime.db() as db:
        frozen = db.get(AnswerRequest, ordinary_receipt["request_id"]).command
        assert frozen["repair_policy"] == "claim_patch_repair_v3"
        assert "practice_query_policy" not in frozen
        assert "practice_context" not in (frozen["teaching_context"] or {})
    item = fixture_item(runtime)
    disclosed = call(
        runtime,
        "POST",
        f"/learning/practice/{item['id']}/help",
        {"action": "full_explanation", "expected_version": 0},
    )
    opened = open_tutor(runtime, item, disclosed["version"])
    direct_receipt = call(
        runtime,
        "POST",
        f"/sessions/{opened['session_id']}/messages",
        {
            "content": "Explain the practice in full.",
            "use_profile": False,
            "teaching_mode": "direct",
            "task_action": "continue",
            "task_id": opened["task_id"],
            "task_version": opened["task_version"],
        },
        {**runtime.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    call(runtime, "POST", "/jobs/" + direct_receipt["job_id"] + "/cancel", {})
    with runtime.db() as db:
        frozen = db.get(AnswerRequest, direct_receipt["request_id"]).command
        assert frozen["repair_policy"] == "claim_patch_repair_v3"
        assert frozen["practice_query_policy"] == "owned_public_practice_query_v1"
        assert frozen["teaching_context"]["teaching_mode"] == "direct"


def test_explicit_solution_is_carried_only_after_disclosure_and_source_revocation_blocks(runtime):
    item = fixture_item(runtime)
    opened = open_tutor(runtime, item, 0)
    shown = call(
        runtime,
        "POST",
        f"/learning/practice/{item['id']}/help",
        {"action": "full_explanation", "expected_version": 0},
    )
    assert "PRIVATE_ANSWER_SENTINEL" in shown["full_explanation"]
    again = open_tutor(runtime, item, shown["version"])
    assert again["task_id"] == opened["task_id"] and again["teaching_mode"] == "direct"
    with runtime.db() as db:
        task = db.get(LearningTask, opened["task_id"])
        value = task.requirements["practice_context"]
        assert (
            tutoring.disclosure_turns(value)[0]["response"]["answer_text"]
            == shown["full_explanation"]
        )
    call(
        runtime,
        "POST",
        "/documents/" + item["source"]["document_id"] + "/revoke",
        headers=runtime.headers("admin@example.com"),
    )
    call(
        runtime,
        "POST",
        f"/learning/practice/{item['id']}/tutor",
        {"expected_version": shown["version"]},
        status=410,
    )
