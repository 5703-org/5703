"""Goal continuity on authored isolated sources; no live provider or official-data writes."""

from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.modules.answering.models import AnswerRequest
from app.modules.learning_product.models import (
    LearningRecord,
    PracticeAttempt,
    PracticeProgress,
    StudyGoal,
)
from app.modules.learning_state import tasks
from app.modules.learning_state.models import LearningTask
from generation import GenerationService

from .test_chat_runtime import call
from .test_learning_product import (
    student_id,
    use_scripted_practice_grader,
    applied_practice_feedback,
)
from .test_practice_tutor import attempt, fixture_item
from .test_learning_state import ScriptedCheckedTransport, checker_input


class GoalCheckedTransport(ScriptedCheckedTransport):
    """Authored wire verdicts exercise real schemas and fences; no quality labels."""

    def __init__(self, item, goal_id, during_check=None):
        self.item = item
        self.goal_id = goal_id
        self.during_check = during_check
        self.schemas = []

    def generate(self, messages, **kwargs):
        schema = kwargs["response_schema_name"]
        self.schemas.append(schema)
        teaching = kwargs["request_context"]["teaching_context"]
        binding = teaching["requirements"]["practice_goal_context"]
        assert binding["version"] == "owned_practice_goal_v1"
        assert binding["goal_id"] == self.goal_id and binding["item_id"] == self.item["id"]
        assert binding["source"] == self.item["source"]
        if schema.startswith("joint_check_"):
            data = checker_input(messages)
            assert data["ACTUAL_CITATION_BINDINGS"] and data["CLAIMS"]
            assert any(
                "Photosynthesis captures" in row["exact_text"] for row in data["SOURCE_FRAGMENTS"]
            )
            if self.during_check is not None:
                action, self.during_check = self.during_check, None
                action()
        return super().generate(messages, **kwargs)


def use_scripted_goal_transport(monkeypatch, item, goal_id, during_check=None):
    transport = GoalCheckedTransport(item, goal_id, during_check)

    def factory(**kwargs):
        # The actual generation service still parses both returned JSON schemas,
        # validates actual claim/source bindings and runs all publication checks.
        return GenerationService(transport, checker_adapter=transport, **kwargs)

    monkeypatch.setattr("app.modules.answering.service.GenerationService", factory)
    return transport


def goal_for(rt, item, **changes):
    page = call(rt, "GET", f"/learning/library/{item['source']['document_id']}/units")
    source = next(unit for unit in page["items"] if unit["id"] == item["source"]["source_unit_id"])
    body = {
        "title": "Authored goal continuity fixture",
        "document_id": item["source"]["document_id"],
        "section_ids": [source["section_id"]],
        **changes,
    }
    return call(rt, "POST", "/learning/goals", body, status=201)


def open_goal(rt, item, expected, goal_id=None, status=200):
    return call(
        rt,
        "POST",
        f"/learning/practice/{item['id']}/tutor",
        {"expected_version": expected, **({"goal_id": goal_id} if goal_id else {})},
        status=status,
    )


def test_goal_practice_hint_return_attempt_and_next_step_keep_the_goal(runtime, monkeypatch):
    use_scripted_practice_grader(monkeypatch)
    item = fixture_item(runtime, "step")
    goal = goal_for(runtime, item)
    listed = call(
        runtime, "GET", f"/learning/practice?goal_id={goal['id']}&unit_id={goal['units'][0]['id']}"
    )
    assert item["id"] in {row["id"] for row in listed}
    opened = open_goal(runtime, item, 0, goal["id"])
    assert opened["goal_id"] == goal["id"]
    receipt = call(
        runtime,
        "POST",
        f"/sessions/{opened['session_id']}/messages",
        {
            "content": "Help me with the current practice step without giving the answer.",
            "task_action": "continue",
            "teaching_mode": "hint",
            "task_id": opened["task_id"],
            "task_version": opened["task_version"],
            "use_profile": False,
        },
        {**runtime.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    with runtime.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        frozen = deepcopy(request.command["teaching_context"])
        assert frozen["requirements"]["practice_goal_context"]["goal_id"] == goal["id"]
        assert frozen["practice_context"]["current_step"] == 1
    transport = use_scripted_goal_transport(monkeypatch, item, goal["id"])
    assert runtime.work()
    job = call(runtime, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "succeeded" and job["answer_id"], {
        "state": job["state"],
        "stage": job.get("stage"),
        "error": job.get("error"),
    }
    assert "joint_check_v5" in transport.schemas and 2 <= len(transport.schemas) <= 4
    visible_answer = call(runtime, "GET", "/answers/" + job["answer_id"])
    assert visible_answer["learning_task"]["practice_goal_id"] == goal["id"]
    assert call(runtime, "GET", "/learning/goals/" + goal["id"])["units"][0]["attempts"] == 0
    body = {
        "idempotency_key": str(uuid4()),
        "expected_version": 0,
        "goal_id": visible_answer["learning_task"]["practice_goal_id"],
        "response": {"text": "light", "step": 1},
    }
    saved = call(runtime, "POST", f"/learning/practice/{item['id']}/attempts", body)
    assert applied_practice_feedback(saved)["outcome"] == "correct"
    assert call(runtime, "POST", f"/learning/practice/{item['id']}/attempts", body) == saved
    reflected = call(runtime, "GET", "/learning/goals/" + goal["id"])
    assert reflected["units"][0]["attempts"] == 1
    assert reflected["units"][0]["correct_attempts"] == 1
    with runtime.db() as db:
        row = db.get(PracticeAttempt, saved["id"])
        assert row.goal_id == goal["id"]
        record = db.scalar(
            select(LearningRecord).where(
                LearningRecord.object_id == saved["id"], LearningRecord.kind == "practice_attempt"
            )
        )
        assert record.details["goal_id"] == goal["id"]
        task = db.get(LearningTask, opened["task_id"])
        assert task.current_step == 2
        assert task.requirements["practice_goal_context"]["goal_id"] == goal["id"]
        with pytest.raises(AppError):
            tasks.validate_task(db, student_id(runtime), frozen)
    resumed = open_goal(runtime, item, saved["assessment"]["applied_progress_version"], goal["id"])
    assert resumed["task_id"] == opened["task_id"]
    assert resumed["goal_id"] == goal["id"]


def test_same_goal_reopen_is_idempotent_and_preserves_the_legacy_practice_snapshot(runtime):
    item = fixture_item(runtime)
    goal = goal_for(runtime, item)
    first = open_goal(runtime, item, 0, goal["id"])
    assert open_goal(runtime, item, 0, goal["id"]) == first
    with runtime.db() as db:
        task = db.get(LearningTask, first["task_id"])
        assert task.requirements["practice_context"]["version"] == "practice_tutor_context_v1"
        records = list(
            db.scalars(
                select(LearningRecord).where(
                    LearningRecord.kind == "practice_tutor_goal_bound",
                    LearningRecord.object_id == item["id"],
                    LearningRecord.owner_id == student_id(runtime),
                )
            )
        )
        assert len(records) == 1


def test_changing_goal_creates_a_new_task_and_preserves_prior_task_requirements(
    runtime, monkeypatch
):
    item = fixture_item(runtime)
    first_goal = goal_for(runtime, item)
    second_goal = goal_for(runtime, item, title="Second authored goal")
    first = open_goal(runtime, item, 0, first_goal["id"])
    receipt = call(
        runtime,
        "POST",
        f"/sessions/{first['session_id']}/messages",
        {
            "content": "Help me with the current practice step without giving the answer.",
            "teaching_mode": "hint",
            "task_action": "continue",
            "use_profile": False,
            "task_id": first["task_id"],
            "task_version": first["task_version"],
        },
        {**runtime.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    transport = use_scripted_goal_transport(monkeypatch, item, first_goal["id"])
    assert runtime.work()
    published = call(runtime, "GET", "/jobs/" + receipt["job_id"])
    assert published["state"] == "succeeded" and published["answer_id"], {
        "state": published["state"],
        "stage": published.get("stage"),
        "error": published.get("error"),
    }
    assert "joint_check_v5" in transport.schemas and 2 <= len(transport.schemas) <= 4
    with runtime.db() as db:
        task = db.get(LearningTask, first["task_id"])
        prior = (
            deepcopy(task.requirements),
            task.version,
            task.question,
            task.owner_id,
            task.session_id,
        )
        frozen = {
            "task_id": task.id,
            "task_version": task.version,
            "exposure_epoch": task.exposure_epoch,
            "practice_context": deepcopy(task.requirements["practice_context"]),
            "requirements": deepcopy(task.requirements),
        }
    second = open_goal(runtime, item, 0, second_goal["id"])
    assert second["task_id"] != first["task_id"] and second["session_id"] != first["session_id"]
    assert second["practice_progress_version"] == 1
    with runtime.db() as db:
        old = db.get(LearningTask, first["task_id"])
        assert (old.requirements, old.version, old.question, old.owner_id, old.session_id) == prior
        with pytest.raises(AppError):
            tasks.validate_task(db, student_id(runtime), frozen)
        assert tasks.task_out(old)["practice_goal_id"] == first_goal["id"]
    historic_answer = call(runtime, "GET", "/answers/" + published["answer_id"])
    assert historic_answer["learning_task"]["id"] == first["task_id"]
    assert historic_answer["learning_task"]["practice_goal_id"] == first_goal["id"]
    open_goal(runtime, item, 0, first_goal["id"], status=409)


def test_goal_adoption_and_goal_removal_each_create_a_separate_task(runtime):
    item = fixture_item(runtime)
    original = open_goal(runtime, item, 0)
    with runtime.db() as db:
        prior = deepcopy(db.get(LearningTask, original["task_id"]).requirements)
    goal = goal_for(runtime, item)
    selected = open_goal(runtime, item, 0, goal["id"])
    plain = open_goal(runtime, item, 1)
    assert len({original["task_id"], selected["task_id"], plain["task_id"]}) == 3
    assert selected["goal_id"] == goal["id"] and plain["goal_id"] is None
    assert plain["practice_progress_version"] == 2
    with runtime.db() as db:
        assert db.get(LearningTask, original["task_id"]).requirements == prior
        assert "practice_goal_context" not in db.get(LearningTask, plain["task_id"]).requirements


def test_foreign_goal_is_hidden_and_cannot_create_a_tutor(runtime):
    item = fixture_item(runtime)
    goal = goal_for(runtime, item)
    call(
        runtime,
        "POST",
        f"/learning/practice/{item['id']}/tutor",
        {"expected_version": 0, "goal_id": goal["id"]},
        headers=runtime.headers("student2@example.com"),
        status=404,
    )
    with runtime.db() as db:
        assert (
            db.scalar(select(PracticeProgress).where(PracticeProgress.item_id == item["id"]))
            is None
        )


def test_unselected_section_and_different_book_are_rejected(runtime):
    item = fixture_item(runtime)
    units = call(runtime, "GET", f"/learning/library/{item['source']['document_id']}/units")[
        "items"
    ]
    actual = next(unit for unit in units if unit["id"] == item["source"]["source_unit_id"])
    other = next(unit for unit in units if unit["section_id"] != actual["section_id"])
    wrong_section = goal_for(runtime, item, section_ids=[other["section_id"]])
    open_goal(runtime, item, 0, wrong_section["id"], status=422)
    first_goal = goal_for(runtime, item)
    other_item = fixture_item(runtime)
    open_goal(runtime, other_item, 0, first_goal["id"], status=422)


def test_current_goal_binding_and_revoked_source_are_rechecked_before_publication(runtime):
    item = fixture_item(runtime)
    goal = goal_for(runtime, item)
    opened = open_goal(runtime, item, 0, goal["id"])
    with runtime.db() as db:
        task = db.get(LearningTask, opened["task_id"])
        frozen = {
            "task_id": task.id,
            "task_version": task.version,
            "exposure_epoch": task.exposure_epoch,
            "practice_context": deepcopy(task.requirements["practice_context"]),
            "requirements": deepcopy(task.requirements),
        }
        modified = deepcopy(frozen)
        modified["requirements"]["practice_goal_context"]["goal_id"] = str(uuid4())
        with pytest.raises(AppError):
            tasks.validate_task(db, student_id(runtime), modified)
        tasks.validate_task(db, student_id(runtime), frozen)
    call(
        runtime,
        "POST",
        "/documents/" + item["source"]["document_id"] + "/revoke",
        headers=runtime.headers("admin@example.com"),
    )
    open_goal(runtime, item, 0, goal["id"], status=410)
    with runtime.db() as db:
        task = db.get(LearningTask, opened["task_id"])
        with pytest.raises(AppError):
            tasks.validate_task(db, student_id(runtime), frozen)


def test_stale_practice_cas_rejects_reopening_the_goal_after_a_saved_attempt(runtime):
    item = fixture_item(runtime)
    goal = goal_for(runtime, item)
    opened = open_goal(runtime, item, 0, goal["id"])
    saved = attempt(runtime, item, 0, selection=["A"])
    open_goal(runtime, item, 0, goal["id"], status=409)
    assert (
        open_goal(runtime, item, saved["progress_version"], goal["id"])["task_id"]
        == opened["task_id"]
    )


def test_goal_with_a_different_release_cannot_reuse_or_mutate_the_published_task(runtime):
    item = fixture_item(runtime)
    goal = goal_for(runtime, item)
    opened = open_goal(runtime, item, 0, goal["id"])
    other = fixture_item(runtime)
    assert other["source"]["release_id"] != item["source"]["release_id"]
    with runtime.db() as db:
        row = db.get(StudyGoal, goal["id"])
        row.release_id = other["source"]["release_id"]
        task = db.get(LearningTask, opened["task_id"])
        original = (deepcopy(task.requirements), task.version, task.question)
        db.commit()
    open_goal(runtime, item, 0, goal["id"], status=422)
    with runtime.db() as db:
        task = db.get(LearningTask, opened["task_id"])
        assert (task.requirements, task.version, task.question) == original
        progress = db.scalar(select(PracticeProgress).where(PracticeProgress.item_id == item["id"]))
        assert progress.version == 0 and progress.tutor_task_id == opened["task_id"]


def test_native_mock_hint_keeps_its_semantic_guard_and_owned_goal_pointer(runtime):
    item = fixture_item(runtime)
    goal = goal_for(runtime, item)
    opened = open_goal(runtime, item, 0, goal["id"])
    with runtime.db() as db:
        task = db.get(LearningTask, opened["task_id"])
        original = deepcopy(task.requirements)
    receipt = call(
        runtime,
        "POST",
        f"/sessions/{opened['session_id']}/messages",
        {
            "content": "Help me with the current practice step without giving the answer.",
            "teaching_mode": "hint",
            "task_action": "continue",
            "use_profile": False,
            "task_id": opened["task_id"],
            "task_version": opened["task_version"],
        },
        {**runtime.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    assert runtime.work()
    job = call(runtime, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed" and job["answer_id"] is None, job
    assert job["error"]["code"] == "SEMANTIC_CHECK_UNAVAILABLE"
    with runtime.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.budget["consumed_calls"] == 0
        task = db.get(LearningTask, opened["task_id"])
        assert task.requirements == original
        progress = db.scalar(select(PracticeProgress).where(PracticeProgress.item_id == item["id"]))
        assert progress.version == 0 and progress.tutor_task_id == opened["task_id"]
    assert call(runtime, "GET", "/learning/goals/" + goal["id"])["units"][0]["attempts"] == 0


def test_goal_switch_during_strict_check_cannot_publish_the_old_frozen_task(runtime, monkeypatch):
    item = fixture_item(runtime)
    first_goal = goal_for(runtime, item)
    second_goal = goal_for(runtime, item, title="Late switch fixture")
    first = open_goal(runtime, item, 0, first_goal["id"])
    with runtime.db() as db:
        original = deepcopy(db.get(LearningTask, first["task_id"]).requirements)
    receipt = call(
        runtime,
        "POST",
        f"/sessions/{first['session_id']}/messages",
        {
            "content": "Help me with the current practice step without giving the answer.",
            "teaching_mode": "hint",
            "task_action": "continue",
            "use_profile": False,
            "task_id": first["task_id"],
            "task_version": first["task_version"],
        },
        {**runtime.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    switched = []
    transport = use_scripted_goal_transport(
        monkeypatch,
        item,
        first_goal["id"],
        lambda: switched.append(open_goal(runtime, item, 0, second_goal["id"])),
    )
    assert runtime.work()
    job = call(runtime, "GET", "/jobs/" + receipt["job_id"])
    assert "joint_check_v5" in transport.schemas and len(switched) == 1
    assert job["state"] == "failed" and job["answer_id"] is None, job
    assert job["error"]["code"] == "CONFLICT"
    with runtime.db() as db:
        old = db.get(LearningTask, first["task_id"])
        assert old.requirements == original
        progress = db.scalar(select(PracticeProgress).where(PracticeProgress.item_id == item["id"]))
        assert progress.version == 1 and progress.tutor_task_id == switched[0]["task_id"]
    assert (
        call(runtime, "GET", "/sessions/" + first["session_id"] + "/messages")["items"][-1][
            "answer"
        ]
        is None
    )
