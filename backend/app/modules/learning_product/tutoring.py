"""Owned practice-to-chat continuity using already learner-visible state."""

import copy
from uuid import uuid4
from app.core.exceptions import AppError
from app.db.base import utcnow
from app.modules.answering.models import Message
from app.modules.learning.models import ChatSession
from app.modules.learning_state.models import LearningTask
from . import library
from .models import PracticeProgress

VERSION = "practice_tutor_context_v1"


def snapshot(db, actor, item, progress):
    """No correct options, private points, unshown hints or expected values."""
    from . import service

    visible = service.progress_out(db, actor, item, progress)
    value = {
        "version": VERSION,
        "item_id": item.id,
        "item_revision": item.item_revision,
        "progress_id": progress.id,
        "progress_version": progress.version,
        "source": copy.deepcopy(item.source),
        "prompt": item.public_payload["prompt"],
        "conditions": list(item.public_payload.get("conditions", [])),
        "options": copy.deepcopy(item.public_payload.get("options", [])),
        "concepts": list(item.public_payload.get("concepts", [])),
        "current_step": visible["current_step"],
        "current_step_prompt": visible["current_step_prompt"],
        "response_kind": visible["current_step_response_kind"],
        "expected_unit": visible["expected_unit"],
        "state": visible["state"],
        "help_level": visible["help_level"],
        "shown_hints": list(visible["hints"]),
        "shown_full_explanation": visible["full_explanation"],
        "recent_attempts": [
            tutor_attempt(attempt)
            for attempt in visible["attempts"]
            if item.public_payload["kind"] != "step"
            or attempt["response"].get("step") == progress.current_step
        ][-3:],
        "progress_authority": "saved_practice_attempt",
    }
    selection_task = item.public_payload.get("selection_task")
    selection_candidates = item.public_payload.get("selection_candidates")
    if selection_task is not None or selection_candidates is not None:
        if not isinstance(selection_task, dict) or not isinstance(selection_candidates, dict):
            raise ValueError("SELECTION_TASK_INVENTORY_MISSING")
        step = selection_task.get("current_step")
        if type(step) is not int or step != selection_candidates.get("current_step"):
            raise ValueError("SELECTION_TASK_INVENTORY_MISMATCH")
        if step == visible["current_step"]:
            value["selection_task"] = copy.deepcopy(selection_task)
            value["selection_candidates"] = copy.deepcopy(selection_candidates)
    return value


def tutor_attempt(attempt):
    """Tutor consumers read applied feedback while preserving the submission receipt."""
    assessment = attempt.get("assessment")
    if assessment and assessment.get("status") == "applied":
        return {
            **attempt,
            "submission_feedback": attempt["feedback"],
            "feedback": assessment["feedback"],
        }
    return attempt


def linked_task(db, actor, progress):
    task = db.get(LearningTask, progress.tutor_task_id) if progress.tutor_task_id else None
    session = db.get(ChatSession, task.session_id) if task else None
    if (
        not task
        or task.owner_id != actor.id
        or not session
        or session.user_id != actor.id
        or session.workspace_id != actor.workspace_id
        or session.deleted_at
        or session.status != "active"
        or task.state != "active"
    ):
        return None
    return task


def refresh_task(db, actor, item, progress, task):
    value = snapshot(db, actor, item, progress)
    previous = task.requirements.get("practice_context", {})
    if previous == value:
        return
    task.requirements = {**task.requirements, "practice_context": value}
    task.current_step = progress.current_step
    task.help_level = (
        progress.help_level
        if previous.get("current_step") != progress.current_step
        else max(task.help_level, progress.help_level)
    )
    task.teaching_mode = (
        "direct" if progress.full_explanation or progress.state == "completed" else "hint"
    )
    task.pending_tutor_question = (
        value["current_step_prompt"] or item.public_payload["prompt"]
        if task.teaching_mode == "hint"
        else None
    )
    task.pending_tutor_question_id = str(uuid4()) if task.pending_tutor_question else None
    task.pending_tutor_question_version += 1
    task.expected_response_kind = (
        "numeric"
        if value["response_kind"] == "numeric"
        else "choice"
        if item.public_payload["kind"] in {"mcq", "multiselect"}
        else "explanation"
    )
    if task.teaching_mode == "direct":
        task.expected_response_kind = None
    task.version += 1
    task.exposure_epoch += 1
    task.updated_at = utcnow()


def synchronize(db, actor, item, progress):
    task = linked_task(db, actor, progress)
    if task:
        refresh_task(db, actor, item, progress, task)


def open_tutor(db, actor, item_id, body):
    from . import service

    service.lock_owner(db, actor)
    item = service.practice_item(db, actor, item_id)
    progress = service.get_progress(db, actor, item, True)
    service.cas(progress, body.expected_version)
    task = linked_task(db, actor, progress)
    if task is None:
        session = ChatSession(
            user_id=actor.id,
            workspace_id=actor.workspace_id,
            title=("Practice: " + item.public_payload["title"])[:200],
        )
        db.add(session)
        db.flush()
        problem = item.public_payload["prompt"]
        conditions = item.public_payload.get("conditions", [])
        options = item.public_payload.get("options", [])
        if conditions:
            problem += "\nGiven conditions:\n" + "\n".join(conditions)
        if options:
            problem += "\nOptions:\n" + "\n".join(
                option["id"] + ": " + option["text"] for option in options
            )
        initial = Message(
            session_id=session.id, sequence=1, role="user", content=problem, state="succeeded"
        )
        db.add(initial)
        db.flush()
        task = LearningTask(
            owner_id=actor.id,
            session_id=session.id,
            initial_message_id=initial.id,
            question=problem,
            task_type="simple_calculation"
            if item.public_payload["kind"] == "numeric"
            else "process_reasoning",
            requirements={"original_question": problem},
            teaching_mode="hint",
            help_level=0,
        )
        db.add(task)
        db.flush()
        progress.tutor_task_id = task.id
        service.event(
            db,
            actor,
            "practice_tutor_opened",
            item.id,
            task_id=task.id,
            session_id=session.id,
            progress_version=progress.version,
        )
    refresh_task(db, actor, item, progress, task)
    db.flush()
    return {
        "session_id": task.session_id,
        "task_id": task.id,
        "task_version": task.version,
        "practice_progress_version": progress.version,
        "teaching_mode": task.teaching_mode,
        "source": item.source,
    }


def validate_context(db, owner_id, task, context):
    """Recheck source visibility and live practice identity before publication."""
    from app.modules.identity.models import User
    from . import service

    value = task.requirements.get("practice_context")
    if not value:
        return
    if value.get("version") != VERSION:
        raise AppError("CONFLICT", "Practice context changed. Reopen the practice tutor.")
    actor = db.get(User, owner_id)
    item = service.practice_item(db, actor, value["item_id"])
    progress = db.get(PracticeProgress, value["progress_id"])
    if progress:
        db.refresh(progress)
    if (
        not progress
        or progress.owner_id != owner_id
        or progress.item_id != item.id
        or progress.tutor_task_id != task.id
        or progress.version != value["progress_version"]
        or item.item_revision != value["item_revision"]
        or context.get("practice_context") != value
    ):
        raise AppError("CONFLICT", "Saved practice progress changed. Reopen the practice tutor.")
    library.validate_locator(db, actor, value["source"])


def disclosure_turns(value):
    """Cumulative checker receives complete text already shown on the practice page."""
    if not value:
        return []
    surfaces = list(value.get("shown_hints", []))
    if value.get("shown_full_explanation"):
        surfaces.append(value["shown_full_explanation"])
    return [
        {
            "answer_id": None,
            "response": {"answer_text": text},
            "citation_views": [],
            "help_level": value.get("help_level", 0),
            "origin": VERSION,
        }
        for text in surfaces
    ]
