"""Real PostgreSQL/API grading lifecycle with authored sources and a scripted adapter.

These checks establish application transactions, not model answer quality. The existing
session harness migrates and drops only a random cs30_test_* database. No real provider,
saved secret, official learner/source data, or running application service is used.
"""

from concurrent.futures import ThreadPoolExecutor
from asyncio import CancelledError
from copy import deepcopy
import json
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from app.modules.identity.models import User, Workspace
from app.modules.knowledge.models import Document
from app.modules.learning_product import practice_assessment as assessment, service
from app.modules.learning_product.models import (
    LearningRecord,
    PracticeAttempt,
    PracticeItem,
    PracticeProgress,
    ReviewEntry,
    StudyGoal,
)
from app.modules.learning_state.models import LearningTask, MemoryEntry
from generation.types import ModelConfig, ProviderResult
from .test_chat_runtime import call
from .test_learning_product import draft, published, source, student_id


def authored_item(rt, kind="short"):
    _, unit = source(rt)
    rubric = {
        "acceptable_answers": ["Light supplies energy."],
        "required_points": [{"id": "PRIVATE_KEY_POINT_CANARY", "terms": ["light energy"]}],
        "explanation": "PRIVATE_SOLUTION_CANARY: light supplies the energy.",
        "hints": ["An authored disclosed hint.", "PRIVATE_UNSHOWN_HINT_CANARY"],
    }
    if kind == "step":
        rubric = {
            "steps": [
                {
                    "id": "energy-step",
                    "prompt": "Explain the source of energy.",
                    "acceptable_answers": ["Light supplies energy."],
                    "required_points": rubric["required_points"],
                    "hints": ["An authored disclosed hint."],
                },
                {
                    "id": "product-step",
                    "prompt": "Name the product described by the source.",
                    "acceptable_answers": ["Sugars"],
                    "hints": ["Think about stored chemical energy."],
                },
            ],
            "explanation": rubric["explanation"],
        }
    elif kind == "numeric":
        rubric = {"numeric": {"value": 2, "unit": "m"}, "explanation": "PRIVATE_SOLUTION_CANARY"}
    elif kind in ("mcq", "multiselect"):
        rubric = {"correct_option_ids": ["A"], "explanation": "PRIVATE_SOLUTION_CANARY"}
    return published(
        rt,
        draft(
            rt,
            unit,
            kind,
            options=[]
            if kind in ("short", "numeric", "step")
            else [{"id": "A", "text": "Light"}, {"id": "B", "text": "Sound"}],
            rubric=rubric,
        ),
    )["item"]


def make_goal(rt, item):
    units = call(rt, "GET", f"/learning/library/{item['source']['document_id']}/units")["items"]
    unit = next(unit for unit in units if unit["id"] == item["source"]["source_unit_id"])
    return call(
        rt,
        "POST",
        "/learning/goals",
        {
            "title": "Authored assessment transaction goal",
            "document_id": item["source"]["document_id"],
            "section_ids": [unit["section_id"]],
        },
        status=201,
    )


def submission(version=0, key=None, **changes):
    result = {
        "idempotency_key": key or str(uuid4()),
        "expected_version": version,
        "response": {"text": "Plants turn incoming sunlight into stored energy."},
    }
    result.update(changes)
    return result


def post_attempt(rt, item, body, headers=None, status=200):
    return call(rt, "POST", f"/learning/practice/{item['id']}/attempts", body, headers, status)


def progress(rt, item):
    return call(rt, "GET", f"/learning/practice/{item['id']}/progress")


def enable_memory(rt):
    state = call(rt, "GET", "/me/memory/settings")
    call(rt, "PATCH", "/me/memory/settings", {"enabled": True, "version": state["version"]})


@pytest.fixture
def script(runtime, monkeypatch):
    config = ModelConfig(
        provider="openai_compatible",
        model="scripted-db-transaction-fixture-only",
        configuration_id="model-settings:authored-db-fixture",
        tokenizer_provider="estimate",
        window_tokens=32000,
        max_tokens=4096,
        timeout_seconds=5,
    )
    state = SimpleNamespace(
        calls=[],
        mode="correct",
        hook=None,
        config=config,
        started=Event(),
        release=Event(),
        secrets=0,
    )
    monkeypatch.setattr(assessment, "resolve_active_checker_model_config", lambda *args: config)

    def no_saved_secret(*args):
        state.secrets += 1
        return None

    monkeypatch.setattr(assessment, "resolve_secret", no_saved_secret)

    def generate(adapter, messages, **kwargs):
        assert kwargs["response_schema_name"] == assessment.SCHEMA_NAME
        assert adapter.config.provider != "mock"
        data = json.loads(messages[1]["content"])
        assert not any(
            marker in json.dumps(data)
            for marker in (
                "PRIVATE_KEY_POINT_CANARY",
                "PRIVATE_SOLUTION_CANARY",
                "PRIVATE_UNSHOWN_HINT_CANARY",
            )
        )
        state.calls.append(deepcopy(data))
        if state.hook:
            state.hook(data)
        if state.mode == "interrupt":
            raise RuntimeError("PRIVATE_PROVIDER_EXCEPTION_CANARY")
        if state.mode == "cancelled":
            raise CancelledError("PRIVATE_PROVIDER_CANCELLATION_CANARY")
        points = [point["id"] for point in data["criteria"]["required_points"]]
        value = dict(
            binding_hash=data["binding_hash"],
            outcome=state.mode
            if state.mode in ("correct", "incorrect", "uncertain")
            else "correct",
            source_sufficient=True,
            rubric_supported=True,
            contradiction_present=state.mode == "incorrect",
            conditions_preserved=True,
            covered_point_ids=points if state.mode != "incorrect" else [],
            missing_point_ids=[] if state.mode != "incorrect" else points,
            source_spans=[dict(start=0, end=len(data["source_passage"]))],
            response_spans=[dict(start=0, end=len(data["learner_text"]))],
        )
        return ProviderResult(
            raw_text='{"raw":"PRIVATE_OUTPUT_CANARY"}'
            if state.mode == "schema"
            else json.dumps(value),
            provider=config.provider,
            model=config.model,
            request_submitted=True,
            finish_reason="length" if state.mode == "truncated" else "stop",
            error={"code": "PROVIDER_HTTP_ERROR", "message": "PRIVATE_PROVIDER_ERROR_CANARY"}
            if state.mode == "provider"
            else None,
        )

    monkeypatch.setattr(assessment.LLMAdapter, "generate", generate)
    return state


def assert_no_grade_side_effects(rt, item, *, version):
    with rt.db() as db:
        row = db.scalar(select(PracticeProgress).where(PracticeProgress.item_id == item["id"]))
        assert row.current_step == 1 and row.state == "awaiting_attempt" and row.version == version
        assert (
            db.scalar(
                select(func.count())
                .select_from(ReviewEntry)
                .where(ReviewEntry.item_id == item["id"])
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(MemoryEntry)
                .where(
                    MemoryEntry.owner_id == row.owner_id,
                    MemoryEntry.category == "assessment_performance",
                    MemoryEntry.source_details["practice_item_id"].as_string() == item["id"],
                )
            )
            == 0
        )


def test_reservation_visible_and_owner_progress_locks_released_before_transport(runtime, script):
    rt = runtime
    item = authored_item(rt, "step")
    owner_id = student_id(rt)
    observations = []

    def verify_committed(data):
        with rt.db() as db:
            assert db.bind.url.database.startswith("cs30_test_")
            db.execute(text("SET LOCAL lock_timeout = '500ms'"))
            attempt = db.get(PracticeAttempt, data["submission_identity"]["attempt_id"])
            assert attempt is not None and attempt.feedback["outcome"] == "pending_review"
            started = db.get(LearningRecord, assessment.operation_id(attempt.id))
            assert started is not None and started.details["reserved_calls"] == 1
            assert started.details["binding_hash"] == data["binding_hash"]
            assert db.get(LearningRecord, assessment.result_id(attempt.id)) is None
            # NOWAIT is a real second-connection lock proof, independent of source comments.
            db.scalar(select(User).where(User.id == owner_id).with_for_update(nowait=True, of=User))
            row = db.scalar(
                select(PracticeProgress)
                .where(PracticeProgress.id == attempt.progress_id)
                .with_for_update(nowait=True)
            )
            assert row.version == 1 and row.current_step == 1 and row.state == "awaiting_attempt"
            observations.append(True)

    script.hook = verify_committed
    result = post_attempt(
        rt, item, submission(response={"text": "Sunlight supplies the energy.", "step": 1})
    )
    assert observations == [True] and len(script.calls) == 1
    assert result["feedback"]["outcome"] == "pending_review"
    assert result["assessment"]["status"] == "applied"
    assert progress(rt, item)["current_step"] == 2


def test_applied_result_is_immutable_base_feedback_and_idempotent_with_safe_history(
    runtime, script
):
    rt = runtime
    item = authored_item(rt)
    goal = make_goal(rt, item)
    enable_memory(rt)
    body = submission(goal_id=goal["id"])
    result = post_attempt(rt, item, body)
    assert result["feedback"]["outcome"] == "pending_review"
    assert result["assessment"]["feedback"]["outcome"] == "correct"
    assert result["assessment"]["applied_progress_version"] == 2
    assert post_attempt(rt, item, body) == result and len(script.calls) == 1
    post_attempt(rt, item, dict(body, response={"text": "Changed"}), status=409)
    assert len(script.calls) == 1
    assert call(rt, "GET", "/learning/practice/attempts/" + result["id"]) == result
    with rt.db() as db:
        attempt = db.get(PracticeAttempt, result["id"])
        actor = db.get(User, attempt.owner_id)
        reservation = db.get(LearningRecord, assessment.operation_id(attempt.id)).details
        assert attempt.feedback == result["feedback"] and attempt.progress_version == 1
        assert assessment.finish(db, actor, attempt.id, reservation, None, {}) == result
        assert (
            db.scalar(
                select(func.count())
                .select_from(LearningRecord)
                .where(
                    LearningRecord.object_id == attempt.id,
                    LearningRecord.kind == "practice_assessment",
                )
            )
            == 1
        )
        review = db.scalar(select(ReviewEntry).where(ReviewEntry.item_id == item["id"]))
        assert review.correct_count == review.attempt_count == 1
    review = next(
        r for r in call(rt, "GET", "/learning/review?due_only=false") if r["item_id"] == item["id"]
    )
    assert (
        review["graded_count"],
        review["pending_count"],
        review["recent_graded_count"],
        review["recent_pending_count"],
    ) == (1, 0, 1, 0)
    unit = call(rt, "GET", "/learning/goals/" + goal["id"])["units"][0]
    assert (
        unit["attempts"],
        unit["graded_attempts"],
        unit["pending_attempts"],
        unit["correct_attempts"],
    ) == (1, 1, 0, 1)
    public = json.dumps(
        [
            result,
            progress(rt, item),
            call(rt, "GET", "/learning/records"),
            call(rt, "GET", "/me/memories"),
        ]
    )
    assert "PRIVATE_" not in public
    history = call(rt, "GET", "/learning/records")
    assert all("diagnostic" not in row["details"] for row in history)
    assert all(
        "source_passage" not in row["details"] and "criteria" not in row["details"]
        for row in history
    )
    memory = next(
        m
        for m in call(rt, "GET", "/me/memories")
        if m["provenance"].get("practice_attempt_id") == result["id"]
    )
    assert memory["provenance"]["assessment_id"] == result["assessment"]["id"]
    assert memory["provenance"]["verification"] == "model_assessed_unverified"


@pytest.mark.parametrize(
    "failure",
    [
        "unconfigured",
        "mock",
        "provider",
        "schema",
        "truncated",
        "uncertain",
        "interrupt",
        "cancelled",
    ],
)
@pytest.mark.filterwarnings("error::pytest.PytestUnhandledThreadExceptionWarning")
def test_failed_check_saves_work_without_grade_progress_review_or_memory(
    runtime, script, monkeypatch, failure
):
    rt = runtime
    item = authored_item(rt, "step")
    enable_memory(rt)
    if failure in ("unconfigured", "mock"):
        monkeypatch.setattr(
            assessment,
            "resolve_active_checker_model_config",
            lambda *args: None if failure == "unconfigured" else ModelConfig(),
        )
    else:
        script.mode = failure
    body = submission(
        response={"text": "Light energy appears, but only sound drives this process.", "step": 1}
    )
    result = post_attempt(rt, item, body)
    assert result["response"]["text"] == body["response"]["text"]
    assert (
        result["feedback"]["outcome"]
        == result["assessment"]["feedback"]["outcome"]
        == "pending_review"
    )
    assert result["assessment"]["status"] == "pending_review"
    assert result["assessment"]["applied_progress_version"] is None
    assert result["assessment"]["feedback"]["error_categories"] == []
    assert_no_grade_side_effects(rt, item, version=1)
    assert len(script.calls) == (0 if failure in ("unconfigured", "mock") else 1)
    assert post_attempt(rt, item, body) == result
    assert "PRIVATE_" not in json.dumps(call(rt, "GET", "/learning/records"))


def test_scripted_incorrect_assessment_applies_errors_without_advancing(runtime, script):
    rt = runtime
    item = authored_item(rt, "step")
    script.mode = "incorrect"
    result = post_attempt(
        rt,
        item,
        submission(
            response={
                "text": "Light energy is present but sound alone drives the process.",
                "step": 1,
            }
        ),
    )
    assert result["feedback"]["outcome"] == "pending_review"
    assert result["assessment"]["status"] == "applied"
    assert result["assessment"]["feedback"]["outcome"] == "incorrect"
    state = progress(rt, item)
    assert (
        state["current_step"] == 1
        and state["state"] == "awaiting_attempt"
        and state["version"] == 2
    )
    row = next(
        r for r in call(rt, "GET", "/learning/review?due_only=false") if r["item_id"] == item["id"]
    )
    assert row["correct_count"] == 0 and row["graded_count"] == 1 and row["pending_count"] == 0
    assert row["recent_error_counts"] == {"source_contradiction": 1}


@pytest.mark.parametrize(
    "change",
    ["progress", "help", "source", "item", "owner", "workspace", "goal", "tutor", "linked_goal"],
)
def test_late_model_result_is_superseded_when_authority_changes(runtime, script, change):
    rt = runtime
    item = authored_item(rt, "step")
    owner_id = student_id(rt)
    with rt.db() as db:
        original_workspace = db.get(User, owner_id).workspace_id
    goal = make_goal(rt, item) if change in ("goal", "linked_goal") else None
    tutor = None
    if change in ("tutor", "linked_goal"):
        tutor = call(
            rt,
            "POST",
            f"/learning/practice/{item['id']}/tutor",
            {"expected_version": 0, **({"goal_id": goal["id"]} if goal else {})},
        )
    body = submission(
        goal_id=goal["id"] if change == "goal" else None,
        response={"text": "Sunlight supplies the energy.", "step": 1},
    )
    mutations = []

    def change_authority(data):
        with rt.db() as db:
            attempt = db.get(PracticeAttempt, data["submission_identity"]["attempt_id"])
            row = db.get(PracticeProgress, attempt.progress_id)
            if change == "progress":
                row.version += 1
            elif change == "help":
                row.help_level += 1
                row.shown_hints = ["A newly disclosed hint"]
                row.version += 1
            elif change == "source":
                db.get(Document, item["source"]["document_id"]).revoked = True
            elif change == "item":
                db.get(PracticeItem, item["id"]).item_revision += 1
            elif change == "owner":
                db.get(User, attempt.owner_id).status = "deactivated"
            elif change == "workspace":
                workspace = Workspace(name="Authored changed scope", slug="scope-" + uuid4().hex)
                db.add(workspace)
                db.flush()
                db.get(User, attempt.owner_id).workspace_id = workspace.id
            elif change in ("goal", "linked_goal"):
                saved_goal = db.get(StudyGoal, goal["id"])
                saved_goal.state = "paused"
                saved_goal.version += 1
            elif change == "tutor":
                task = db.get(LearningTask, tutor["task_id"])
                task.version += 1
                task.exposure_epoch += 1
            db.commit()
            mutations.append(True)

    script.hook = change_authority
    try:
        result = post_attempt(rt, item, body)
    finally:
        if change in ("owner", "workspace"):
            # The shared disposable seed persists between function-scoped runtimes.
            # Restore only this authored authority mutation even if an assertion fails.
            with rt.db() as db:
                actor = db.get(User, owner_id)
                actor.status = "active"
                actor.workspace_id = original_workspace
                db.commit()
    assert mutations == [True] and len(script.calls) == 1
    assert result["assessment"]["status"] == "superseded"
    assert (
        result["feedback"]["outcome"]
        == result["assessment"]["feedback"]["outcome"]
        == "pending_review"
    )
    assert_no_grade_side_effects(rt, item, version=2 if change in ("progress", "help") else 1)


def test_duplicate_pending_request_returns_receipt_without_second_transport(runtime, script):
    rt = runtime
    item = authored_item(rt)
    headers = rt.headers()
    body = submission()

    def wait_for_duplicate(data):
        script.started.set()
        assert script.release.wait(3), (
            "The duplicate route must return without waiting for provider"
        )

    script.hook = wait_for_duplicate
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(post_attempt, rt, item, body, headers)
        assert script.started.wait(3)
        try:
            duplicate = pool.submit(post_attempt, rt, item, body, headers).result(timeout=2)
            assert (
                duplicate["feedback"]["outcome"] == "pending_review"
                and duplicate["assessment"] is None
            )
        finally:
            script.release.set()
        finished = first.result(timeout=3)
    assert duplicate["id"] == finished["id"] and finished["assessment"]["status"] == "applied"
    assert len(script.calls) == 1 and progress(rt, item)["version"] == 2
    assert post_attempt(rt, item, body, headers) == finished


def test_newer_concurrent_submission_can_apply_and_supersedes_older_result(runtime, script):
    rt = runtime
    item = authored_item(rt)
    headers = rt.headers()
    first_body = submission()
    second_body = submission(1, response={"text": "Sunlight supplies the incoming energy."})

    def hold_first(data):
        if data["learner_text"] == first_body["response"]["text"]:
            script.started.set()
            assert script.release.wait(4)

    script.hook = hold_first
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(post_attempt, rt, item, first_body, headers)
        assert script.started.wait(3)
        try:
            second = pool.submit(post_attempt, rt, item, second_body, headers).result(timeout=3)
            assert second["assessment"]["status"] == "applied"
        finally:
            script.release.set()
        older = first.result(timeout=3)
    assert older["assessment"]["status"] == "superseded" and len(script.calls) == 2
    state = progress(rt, item)
    assert state["version"] == 3 and state["state"] == "completed"
    review = next(
        r for r in call(rt, "GET", "/learning/review?due_only=false") if r["item_id"] == item["id"]
    )
    assert (
        review["attempt_count"],
        review["correct_count"],
        review["graded_count"],
        review["pending_count"],
    ) == (2, 1, 1, 1)


@pytest.mark.parametrize("failure", ["exception", "cancelled"])
def test_application_failure_rolls_back_all_grade_writes_before_pending_receipt(
    runtime, script, monkeypatch, failure
):
    rt = runtime
    item = authored_item(rt)
    original = service.record_practice_memory

    def fail_after_grade(*args, **kwargs):
        original(*args, **kwargs)
        if failure == "cancelled":
            raise CancelledError("PRIVATE_FAILED_APPLICATION_CANCELLATION_CANARY")
        raise RuntimeError("PRIVATE_FAILED_APPLICATION_CANARY")

    monkeypatch.setattr(service, "record_practice_memory", fail_after_grade)
    result = post_attempt(rt, item, submission())
    assert result["assessment"]["status"] == "pending_review"
    assert_no_grade_side_effects(rt, item, version=1)
    with rt.db() as db:
        terminal = db.get(LearningRecord, result["assessment"]["id"])
        assert terminal.details["diagnostic"]["reason"] == "application_failed"
    assert len(script.calls) == 1


@pytest.mark.parametrize(
    "kind,response",
    [
        ("mcq", {"selection": ["A"]}),
        ("multiselect", {"selection": ["A"]}),
        ("numeric", {"value": 200, "unit": "cm"}),
    ],
)
def test_choice_and_numeric_rules_have_no_assessment_or_secret_lane(
    runtime, script, kind, response
):
    rt = runtime
    item = authored_item(rt, kind)
    result = post_attempt(rt, item, submission(response=response))
    assert result["feedback"]["outcome"] == "correct" and result["assessment"] is None
    assert script.calls == [] and script.secrets == 0
    with rt.db() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(LearningRecord)
                .where(
                    LearningRecord.object_id == result["id"],
                    LearningRecord.kind.in_(["practice_assessment_started", "practice_assessment"]),
                )
            )
            == 0
        )


def test_applied_feedback_reaches_linked_tutor_without_mutating_submission(runtime, script):
    rt = runtime
    item = authored_item(rt)
    tutor = call(rt, "POST", f"/learning/practice/{item['id']}/tutor", {"expected_version": 0})
    result = post_attempt(rt, item, submission())
    assert result["assessment"]["status"] == "applied"
    with rt.db() as db:
        task = db.get(LearningTask, tutor["task_id"])
        visible = task.requirements["practice_context"]["recent_attempts"][-1]
        assert visible["feedback"]["outcome"] == "correct"
        assert visible["submission_feedback"] == result["feedback"]
        assert "PRIVATE_" not in json.dumps(task.requirements)


def test_wrong_owner_cannot_retrieve_or_regrade_saved_attempt(runtime, script):
    rt = runtime
    item = authored_item(rt)
    result = post_attempt(rt, item, submission())
    call(
        rt,
        "GET",
        "/learning/practice/attempts/" + result["id"],
        headers=rt.headers("student2@example.com"),
        status=404,
    )
    assert len(script.calls) == 1
