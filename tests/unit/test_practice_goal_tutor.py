"""Owned goal fencing on explicitly synthetic, local-only software fixtures."""

from copy import deepcopy
from types import SimpleNamespace as NS
from pathlib import Path
import json

import pytest
from pydantic import ValidationError
from fastapi.encoders import jsonable_encoder
import yaml

from app.core.exceptions import AppError
from app.modules.learning_product import goal_tutoring as bridge
from contracts.study import PracticeTutorInput, PracticeTutorOut
from contracts.learning import TaskOut


@pytest.fixture
def scope(monkeypatch):
    actor = NS(id="owner")
    item = NS(
        id="practice",
        item_revision=2,
        source={
            "document_id": "book",
            "release_id": "release",
            "processing_id": "processing",
            "source_unit_id": "unit",
            "text_hash": "source-sha",
            "start": 3,
            "end": 17,
        },
        validation={"section_id": "actual-section"},
    )
    progress = NS(
        id="progress",
        owner_id=actor.id,
        item_id=item.id,
        tutor_task_id="task",
        version=4,
        updated_at=None,
    )
    goal = NS(id="goal", document_id="book", release_id="release")
    task = NS(
        id="task",
        requirements={},
        version=8,
        exposure_epoch=6,
        updated_at=None,
        owner_id=actor.id,
        question="Immutable original question",
        session_id="session",
    )
    db = NS(
        scalars=lambda _: ["actual-section"],
        flush=lambda: None,
        get=lambda model, key: {
            "owner": actor,
            "practice": item,
            "progress": progress,
            "task": task,
        }.get(key),
    )
    monkeypatch.setattr(bridge.service, "owned", lambda *args: goal)
    monkeypatch.setattr(
        bridge.library,
        "validate_locator",
        lambda *args: (None, [], NS(processing_id="processing", section="Section")),
    )
    monkeypatch.setattr(bridge.library, "section_id", lambda *args: "actual-section")
    monkeypatch.setattr(bridge.service, "practice_item", lambda *args: item)
    return NS(actor=actor, item=item, progress=progress, goal=goal, task=task, db=db)


def bound(scope):
    return bridge.goal_binding(scope.db, scope.actor, scope.item, scope.progress, scope.goal.id)


def test_binding_uses_the_validated_source_section_and_preserves_exact_locator(scope):
    value = bound(scope)
    assert value["section_id"] == "actual-section" and value["source"] == scope.item.source
    scope.item.source["start"] = 4
    assert value["source"]["start"] == 3
    assert bridge.saved_goal(value) == scope.goal.id


@pytest.mark.parametrize("change", ["document", "release", "item_section", "unselected_section"])
def test_goal_must_select_the_exact_current_document_release_and_validated_section(scope, change):
    if change == "document":
        scope.goal.document_id = "other-book"
    elif change == "release":
        scope.goal.release_id = "other-release"
    elif change == "item_section":
        scope.item.validation["section_id"] = "forged-section"
    else:
        scope.db.scalars = lambda _: ["other-section"]
    with pytest.raises(AppError) as error:
        bound(scope)
    assert error.value.code == "VALIDATION_FAILED"


def test_foreign_goal_retains_the_existing_owner_hidden_error(scope, monkeypatch):
    def foreign(*args):
        raise AppError("NOT_FOUND")

    monkeypatch.setattr(bridge.service, "owned", foreign)
    with pytest.raises(AppError) as error:
        bound(scope)
    assert error.value.code == "NOT_FOUND"


@pytest.mark.parametrize("value", [[], "goal", {}, {"version": "future"}, False])
def test_malformed_saved_binding_cannot_change_the_progress_pointer(value):
    with pytest.raises(AppError) as error:
        bridge.saved_goal(value)
    assert error.value.code == "CONFLICT"


def test_legacy_no_goal_context_keeps_the_existing_path(scope):
    bridge.validate_context(scope.db, scope.actor.id, scope.task, {})
    assert bridge.goal_binding(scope.db, scope.actor, scope.item, scope.progress, None) is None


@pytest.mark.parametrize("mutation", ["goal", "source", "revision", "progress", "pointer", "owner"])
def test_frozen_context_cannot_cross_goal_source_revision_progress_or_owner(scope, mutation):
    value = bound(scope)
    scope.task.requirements[bridge.KEY] = value
    context = {"requirements": {bridge.KEY: deepcopy(value)}}
    bridge.validate_context(scope.db, scope.actor.id, scope.task, context)
    if mutation == "goal":
        context["requirements"][bridge.KEY]["goal_id"] = "other-goal"
    elif mutation == "source":
        scope.item.source["text_hash"] = "changed-sha"
    elif mutation == "revision":
        scope.item.item_revision += 1
    elif mutation == "progress":
        context["requirements"][bridge.KEY]["progress_id"] = "other-progress"
    elif mutation == "pointer":
        scope.progress.tutor_task_id = "other-task"
    else:
        scope.progress.owner_id = "other-owner"
    with pytest.raises(AppError):
        bridge.validate_context(scope.db, scope.actor.id, scope.task, context)


def test_revoked_source_stops_a_frozen_goal_before_publication(scope, monkeypatch):
    value = bound(scope)
    scope.task.requirements[bridge.KEY] = value

    def revoked(*args):
        raise AppError("SOURCE_REVOKED")

    monkeypatch.setattr(bridge.service, "practice_item", revoked)
    with pytest.raises(AppError) as error:
        bridge.validate_context(
            scope.db, scope.actor.id, scope.task, {"requirements": {bridge.KEY: deepcopy(value)}}
        )
    assert error.value.code == "SOURCE_REVOKED"


def test_goal_switch_creates_a_new_task_without_mutating_the_previous_task(scope, monkeypatch):
    old = scope.task
    old.requirements[bridge.KEY] = bound(scope)
    original = deepcopy(vars(old))
    scope.goal.id = "second-goal"
    new = NS(
        id="new-task",
        requirements={"practice_context": {"version": "practice_tutor_context_v1"}},
        version=2,
        exposure_epoch=1,
        updated_at=None,
    )
    events = []
    monkeypatch.setattr(bridge.service, "lock_owner", lambda *args: None)
    monkeypatch.setattr(bridge.service, "get_progress", lambda *args: scope.progress)

    def cas(row, version):
        if row.version != version:
            raise AppError("VERSION_CONFLICT")

    monkeypatch.setattr(bridge.service, "cas", cas)
    monkeypatch.setattr(bridge.tutoring, "linked_task", lambda *args: old)

    def original_tutor(db, actor, item_id, body):
        assert scope.progress.tutor_task_id is None
        assert body.expected_version == 5
        scope.progress.tutor_task_id = new.id
        return {
            "task_id": new.id,
            "task_version": new.version,
            "session_id": "new-session",
            "practice_progress_version": 5,
            "teaching_mode": "hint",
            "source": scope.item.source,
        }

    monkeypatch.setattr(bridge.tutoring, "open_tutor", original_tutor)
    monkeypatch.setattr(bridge.service, "event", lambda *args, **kwargs: events.append(kwargs))
    get = scope.db.get
    scope.db.get = lambda model, key: new if key == new.id else get(model, key)
    opened = bridge.open_tutor(
        scope.db, scope.actor, scope.item.id, NS(expected_version=4, goal_id=scope.goal.id)
    )
    assert vars(old) == original and opened["task_id"] == new.id
    assert opened["goal_id"] == scope.goal.id and opened["practice_progress_version"] == 5
    assert new.requirements["practice_context"]["version"] == "practice_tutor_context_v1"
    assert events[0]["goal_id"] == scope.goal.id


def test_stale_cas_fails_before_goal_or_pointer_changes(scope, monkeypatch):
    original = deepcopy(vars(scope.progress))
    monkeypatch.setattr(bridge.service, "lock_owner", lambda *args: None)
    monkeypatch.setattr(bridge.service, "get_progress", lambda *args: scope.progress)

    def stale(*args):
        raise AppError("VERSION_CONFLICT")

    monkeypatch.setattr(bridge.service, "cas", stale)
    with pytest.raises(AppError) as error:
        bridge.open_tutor(
            scope.db, scope.actor, scope.item.id, NS(expected_version=3, goal_id="goal")
        )
    assert error.value.code == "VERSION_CONFLICT" and vars(scope.progress) == original


def test_optional_goal_dto_keeps_old_requests_and_saved_task_projections_compatible():
    assert PracticeTutorInput(expected_version=0).goal_id is None
    assert PracticeTutorInput(expected_version=0, goal_id="owned-goal").goal_id == "owned-goal"
    schema = TaskOut.model_json_schema()
    assert "practice_goal_id" not in schema["required"]
    assert schema["properties"]["practice_goal_id"]["default"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"expected_version": 0, "goal_id": ""},
        {"expected_version": 0, "goal_id": "x" * 37},
        {"expected_version": 0, "goal_owner": "other-owner"},
    ],
)
def test_goal_input_cannot_create_an_unbounded_or_client_supplied_owner_authority(body):
    with pytest.raises(ValidationError):
        PracticeTutorInput.model_validate(body)


@pytest.mark.parametrize("filename", ["openapi.json", "openapi.yaml"])
def test_canonical_optional_goal_fields_match_the_existing_null_excluding_export(filename):
    path = Path(__file__).resolve().parents[2] / "contracts" / filename
    raw = path.read_text(encoding="utf-8")
    schema = json.loads(raw) if filename.endswith("json") else yaml.safe_load(raw)
    for model, field in (
        (PracticeTutorInput, "goal_id"),
        (PracticeTutorOut, "goal_id"),
        (TaskOut, "practice_goal_id"),
    ):
        exported = schema["components"]["schemas"][model.__name__]
        expected = jsonable_encoder(model.model_json_schema(), exclude_none=True)
        assert exported["properties"][field] == expected["properties"][field]
        assert field not in exported["required"]
