"""Persisted question boundaries, revisions and checked learner progress."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppError
from app.modules.learning_state import tasks
from app.modules.learning_state.models import LearningTask
from contracts.models import ChatMessageCreate


def pending(**changes):
    values = dict(
        id="task",
        owner_id="owner",
        session_id="session",
        initial_message_id="initial",
        question="Compare diffusion and osmosis.",
        task_type="concept_comparison",
        teaching_mode="hint",
        help_level=1,
        state="active",
        version=3,
        requirements={},
        exposure_epoch=0,
        pending_tutor_question_id="question",
        pending_tutor_question="Which process specifically involves water?",
        pending_tutor_question_version=2,
        expected_response_kind="concept",
        current_step=1,
        turn_role="user_question",
        last_attempt_evaluation=None,
    )
    values.update(changes)
    return LearningTask(**values)


def body(text, **changes):
    values = dict(
        content=text,
        task_id="task",
        task_version=3,
        pending_tutor_question_id="question",
        pending_tutor_question_version=2,
    )
    values.update(changes)
    return ChatMessageCreate(**values)


class TaskDB:
    def __init__(self, task):
        self.task = task

    def get(self, _model, identity):
        return self.task if identity == self.task.id else None

    def scalar(self, _query):
        return self.task

    def scalars(self, _query):
        return []

    def add(self, task):
        self.task = task

    def flush(self):
        self.task.id = str(uuid4())
        self.task.version = 1
        self.task.exposure_epoch = 0
        self.task.pending_tutor_question_version = 0
        self.task.current_step = 1

    def refresh(self, _task):
        pass


def resolve(task, request):
    return tasks.resolve_task(
        TaskDB(task),
        SimpleNamespace(id="owner"),
        SimpleNamespace(id="session"),
        SimpleNamespace(id="message"),
        request,
        {"messages": []},
    )


@pytest.mark.parametrize(
    "text",
    [
        "Osmosis.",
        "Water.",
        "Diffusion.",
        "Not diffusion.",
        "I think it is osmosis.",
        "Osmosis. Water crosses the membrane.",
    ],
)
def test_bound_attempt_preserves_problem_and_help_depth(text):
    row = pending()
    context = resolve(row, body(text))
    assert context["turn_role"] == "learner_attempt"
    assert context["current_problem"] == "Compare diffusion and osmosis."
    assert context["learner_attempt"] == text
    assert context["help_level"] == 1 and context["task_id"] == "task"
    assert context["pending_tutor_question_version"] == 2
    assert row.version == 4


@pytest.mark.parametrize(
    "text", ["-2.5 mol", "0", "No, 3 kPa.", "I got 8 Pa. I divided force by area."]
)
def test_numeric_and_units_remain_attempts(text):
    row = pending(expected_response_kind="numeric", question="Calculate pressure.")
    assert resolve(row, body(text))["turn_role"] == "learner_attempt"


@pytest.mark.parametrize(
    "text",
    [
        "What is ATP?",
        "Explain photosynthesis.",
        "Another question: what is ATP?",
        "New problem: compare acids and bases.",
    ],
)
def test_explicit_question_or_new_problem_leaves_old_pending_task(text):
    row = pending()
    context = resolve(row, body(text))
    assert context["task_id"] != "task" and context["turn_role"] == "user_question"
    assert row.state == "completed"
    assert context["teaching_mode"] == "direct"


def test_full_explanation_takes_priority_over_attempt_marker():
    context = resolve(
        pending(), body("Please show the full explanation.", turn_role="learner_attempt")
    )
    assert context["task_id"] == "task"
    assert context["teaching_mode"] == "direct" and context["turn_role"] == "user_question"


def test_pending_question_is_required_and_unrelated_short_text_is_not_assumed():
    assert not tasks.is_learner_attempt(
        pending(pending_tutor_question_id=None), ChatMessageCreate(content="Osmosis.")
    )
    assert not tasks.is_learner_attempt(pending(), ChatMessageCreate(content="Paris."))
    assert tasks.is_learner_attempt(pending(), ChatMessageCreate(content="Osmosis."))


@pytest.mark.parametrize(
    "changes",
    [
        {"task_version": 2},
        {"pending_tutor_question_id": "old"},
        {"pending_tutor_question_version": 1},
    ],
)
def test_stale_identity_is_rejected_before_mutating(changes):
    row = pending()
    with pytest.raises(AppError) as caught:
        resolve(row, body("Osmosis.", **changes))
    assert caught.value.code == "CONFLICT" and row.version == 3


def test_foreign_owner_is_hidden():
    with pytest.raises(AppError) as caught:
        resolve(pending(owner_id="another"), body("Osmosis."))
    assert caught.value.code == "NOT_FOUND"


def test_partial_question_binding_is_invalid():
    with pytest.raises(ValidationError):
        ChatMessageCreate(content="Osmosis.", pending_tutor_question_id="question")


@pytest.mark.parametrize(
    "status,step", [("correct", 2), ("incorrect", 1), ("partial", 1), ("unclear", 1)]
)
def test_only_checked_correct_attempt_advances_step(status, step):
    row = pending()
    context = resolve(row, body("Osmosis."))
    result = SimpleNamespace(
        response={"answer_text": "Review that answer. What moves down the gradient?"},
        teaching_context={
            "learner_attempt_evaluation": {"status": status, "feedback": "Review that answer."},
            "tutor_question": {
                "question": "What moves down the gradient?",
                "expected_response_kind": "concept",
            },
        },
    )
    tasks.publish_task(TaskDB(row), context, result)
    assert row.current_step == step and row.help_level == 1
    assert row.pending_tutor_question_id != "question" and row.pending_tutor_question_version == 3
    assert row.last_attempt_evaluation["basis"] == "model_feedback"


def test_hidden_unchecked_question_cannot_be_persisted():
    row = pending()
    with pytest.raises(AppError):
        tasks.publish_task(
            TaskDB(row),
            {"task_id": "task", "teaching_mode": "hint", "help_level": 1},
            SimpleNamespace(
                response={"answer_text": "A safe hint."},
                teaching_context={
                    "tutor_question": {
                        "question": "Hidden answer?",
                        "expected_response_kind": "concept",
                    }
                },
            ),
        )


def test_publication_fence_checks_pending_revision_and_regeneration_refreshes_it():
    row = pending()
    context = resolve(row, body("Osmosis."))
    db = TaskDB(row)
    tasks.validate_task(db, "owner", context)
    row.pending_tutor_question_version += 1
    with pytest.raises(AppError):
        tasks.validate_task(db, "owner", context)
    refreshed = tasks.refresh_disclosures(db, "owner", context)
    tasks.validate_task(db, "owner", refreshed)
    assert refreshed["pending_tutor_question_version"] == 2


def test_regeneration_replaces_the_step_result_without_counting_the_attempt_twice():
    row = pending()
    context = resolve(row, body("Osmosis."))
    db = TaskDB(row)
    checked = SimpleNamespace(
        response={"answer_text": "Your response identifies the requested process."},
        teaching_context={
            "learner_attempt_evaluation": {
                "status": "correct",
                "feedback": "Your response identifies the requested process.",
            }
        },
    )
    tasks.publish_task(db, context, checked)
    assert row.current_step == 2
    refreshed = tasks.refresh_disclosures(db, "owner", context)
    tasks.publish_task(db, refreshed, checked)
    assert row.current_step == 2


def test_live_answer_cannot_publish_without_checked_attempt_feedback():
    row = pending()
    context = resolve(row, body("Osmosis."))
    with pytest.raises(AppError):
        tasks.publish_task(
            TaskDB(row),
            context,
            SimpleNamespace(
                model_mode="live",
                response={"response_type": "answer", "answer_text": "A new hint."},
                teaching_context={},
            ),
        )
