"""Keep an explicitly selected owned goal through a practice tutor round trip."""

from copy import deepcopy
from types import SimpleNamespace

from sqlalchemy import select

from app.core.exceptions import AppError
from app.db.base import utcnow
from app.modules.identity.models import User
from app.modules.learning_state.models import LearningTask

from . import library, service, tutoring
from .models import PracticeProgress, StudyGoal, StudyUnit

VERSION = "owned_practice_goal_v1"
KEY = "practice_goal_context"
FIELDS = frozenset(
    {"version", "goal_id", "item_id", "item_revision", "progress_id", "section_id", "source"}
)


def saved_goal(value):
    """Malformed persisted bindings fail before a task or progress pointer changes."""
    if value is None:
        return None
    if (
        not isinstance(value, dict)
        or set(value) != FIELDS
        or value.get("version") != VERSION
        or any(
            not isinstance(value.get(name), str) or not value[name]
            for name in ("goal_id", "item_id", "progress_id", "section_id")
        )
        or type(value.get("item_revision")) is not int
        or value["item_revision"] < 1
        or not isinstance(value.get("source"), dict)
    ):
        raise AppError("CONFLICT", "The saved practice goal changed. Reopen its learning goal.")
    return value["goal_id"]


def goal_binding(db, actor, item, progress, goal_id):
    """Bind the exact published source and selected section to its owned goal."""
    if goal_id is None:
        return None
    goal = service.owned(db, StudyGoal, goal_id, actor)
    _, _, source_unit = library.validate_locator(db, actor, item.source)
    section_id = library.section_id(source_unit.processing_id, source_unit.section)
    selected = set(db.scalars(select(StudyUnit.section_id).where(StudyUnit.goal_id == goal.id)))
    if (
        goal.document_id != item.source["document_id"]
        or goal.release_id != item.source["release_id"]
        or section_id != item.validation.get("section_id")
        or section_id not in selected
    ):
        raise AppError(
            "VALIDATION_FAILED", detail="The practice source is outside the selected goal."
        )
    return {
        "version": VERSION,
        "goal_id": goal.id,
        "item_id": item.id,
        "item_revision": item.item_revision,
        "progress_id": progress.id,
        "section_id": section_id,
        "source": deepcopy(item.source),
    }


def open_tutor(db, actor, item_id, body):
    """A different goal receives a new task; prior task requirements stay intact."""
    service.lock_owner(db, actor)
    item = service.practice_item(db, actor, item_id)
    progress = service.get_progress(db, actor, item, True)
    service.cas(progress, body.expected_version)
    selected = goal_binding(db, actor, item, progress, body.goal_id)
    previous = tutoring.linked_task(db, actor, progress)
    previous_binding = previous.requirements.get(KEY) if previous else None
    previous_goal = saved_goal(previous_binding)
    if previous and previous_goal == body.goal_id and previous_binding != selected:
        raise AppError("CONFLICT", "The saved practice goal changed. Reopen its learning goal.")
    if previous and previous_goal != body.goal_id:
        progress.tutor_task_id = None
        progress.version += 1
        progress.updated_at = utcnow()
        db.flush()
    opened = tutoring.open_tutor(
        db, actor, item_id, SimpleNamespace(expected_version=progress.version)
    )
    task = db.get(LearningTask, opened["task_id"])
    if task is None:
        raise AppError("CONFLICT", "Reopen saved practice before continuing with its tutor.")
    if selected and task.requirements.get(KEY) is None:
        task.requirements = {**task.requirements, KEY: selected}
        task.version += 1
        task.exposure_epoch += 1
        task.updated_at = utcnow()
        service.event(
            db,
            actor,
            "practice_tutor_goal_bound",
            item.id,
            goal_id=body.goal_id,
            task_id=task.id,
            progress_version=progress.version,
        )
        db.flush()
    return {
        **opened,
        "task_version": task.version,
        "practice_progress_version": progress.version,
        "goal_id": body.goal_id,
    }


def validate_context(db, owner_id, task, context):
    """Check the frozen goal identity after the existing practice progress fence."""
    current = task.requirements.get(KEY)
    requirements = context.get("requirements", {})
    if not isinstance(requirements, dict):
        raise AppError("CONFLICT", "The saved practice goal changed. Reopen its learning goal.")
    captured = requirements.get(KEY)
    if current is None and captured is None:
        return
    saved_goal(current)
    if current is None or current != captured:
        raise AppError("CONFLICT", "The saved practice goal changed. Reopen its learning goal.")
    actor = db.get(User, owner_id)
    item = service.practice_item(db, actor, current["item_id"])
    progress = db.get(PracticeProgress, current["progress_id"])
    if (
        not progress
        or progress.owner_id != owner_id
        or progress.item_id != item.id
        or progress.tutor_task_id != task.id
        or current != goal_binding(db, actor, item, progress, current["goal_id"])
    ):
        raise AppError("CONFLICT", "The saved practice goal changed. Reopen its learning goal.")
