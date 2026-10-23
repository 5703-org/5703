"""Owned review scope and suggestions use actual SQLite query/persistence seams."""

import datetime as dt
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.db.models
from app.core.exceptions import AppError
from app.core.responses import ok
from app.db.base import utcnow
from app.modules.identity.models import Role, User, Workspace
from app.modules.knowledge.models import Document
from app.modules.learning_product import router, service
from app.modules.learning_product.models import (
    PracticeAttempt,
    PracticeItem,
    ReviewEntry,
    StudyGoal,
    StudyNote,
    StudyUnit,
)


@pytest.fixture
def scope(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    for model in (
        Workspace,
        Role,
        User,
        Document,
        PracticeItem,
        PracticeAttempt,
        StudyGoal,
        StudyUnit,
        StudyNote,
        ReviewEntry,
    ):
        model.__table__.create(engine)
    db = Session(engine)
    actor = SimpleNamespace(id="owner", workspace_id="workspace")
    db.add_all(
        [
            Workspace(id="workspace", name="Synthetic workspace", slug="synthetic"),
            Role(id=1, name="student"),
            User(
                id="owner",
                email="owner@fixture.invalid",
                hashed_password="unused",
                role_id=1,
                workspace_id="workspace",
            ),
            Document(id="book", title="Authored source", owner_id="owner"),
            Document(id="other-book", title="Other authored source", owner_id="owner"),
        ]
    )
    goal = StudyGoal(
        id="goal",
        owner_id="owner",
        title="Selected goal",
        document_id="book",
        release_id="release",
        depth="beginner",
    )
    other_goal = StudyGoal(
        id="other-goal",
        owner_id="other",
        title="Private goal",
        document_id="book",
        release_id="release",
        depth="beginner",
    )
    db.add_all(
        [
            goal,
            other_goal,
            StudyUnit(
                id="unit",
                goal_id="goal",
                section_id="section",
                title="Selected section",
                ordinal=0,
                concepts=[],
                prerequisites=[],
            ),
        ]
    )
    db.flush()

    # Only the stored locator seam is replaced here. The native browser cohort
    # separately uses real parsed/released source units and the unchanged validator.
    def validate_locator(database, learner, source):
        document = database.get(Document, source["document_id"])
        if document is None or not document.active or document.revoked:
            raise AppError("SOURCE_UNAVAILABLE")

    monkeypatch.setattr(service.library, "validate_locator", validate_locator)

    def item(
        identity,
        *,
        section="section",
        document="book",
        release="release",
        state="published",
        owner_workspace="workspace",
        reviewed=True,
    ):
        value = PracticeItem(
            id=identity,
            workspace_id=owner_workspace,
            creator_id="owner",
            group_id=identity,
            item_revision=1,
            state=state,
            public_payload={"title": identity, "kind": "numeric", "concepts": ["quantity"]},
            private_rubric={},
            source={"document_id": document, "release_id": release},
            validation={"section_id": section},
            content_hash=identity,
        )
        db.add(value)
        if reviewed:
            db.add(
                ReviewEntry(
                    id="review-" + identity,
                    owner_id=actor.id,
                    item_id=identity,
                    due_at=utcnow() + dt.timedelta(days=1),
                    error_categories=[],
                    attempt_count=0,
                    correct_count=0,
                    scheduling_reason="Authored test schedule",
                )
            )
        db.flush()
        return value

    def queue(goal_id="goal"):
        return router.reviews(due_only=False, goal_id=goal_id, db=db, actor=actor)["data"]

    yield SimpleNamespace(db=db, actor=actor, goal=goal, item=item, queue=queue)
    db.close()
    engine.dispose()


def test_scope_filters_current_item_and_same_concept_suggestions_but_global_stays_neutral(scope):
    scope.item("outside", section="other-section")
    scope.item("inside")
    global_rows = scope.queue(None)
    inside_global = next(row for row in global_rows if row["item_id"] == "inside")
    assert inside_global["suggested_item_id"] == "outside"
    scoped = scope.queue()
    assert [row["item_id"] for row in scoped] == ["inside"]
    assert scoped[0]["suggested_item_id"] is None
    assert len(scope.queue(None)) == 2


@pytest.mark.parametrize("goal_id", ["missing", "other-goal", ""])
def test_missing_or_foreign_explicit_goal_never_falls_back_to_the_global_queue(scope, goal_id):
    scope.item("inside")
    with pytest.raises(AppError) as failure:
        scope.queue(goal_id)
    assert failure.value.code == "NOT_FOUND"


@pytest.mark.parametrize(
    "changes",
    [
        {"document": "other-book"},
        {"release": "other-release"},
        {"section": "other-section"},
        {"state": "retired"},
        {"owner_workspace": "other-workspace"},
    ],
)
def test_scope_requires_published_workspace_document_release_and_selected_section(scope, changes):
    scope.item("excluded", **changes)
    scope.item("inside")
    assert [row["item_id"] for row in scope.queue()] == ["inside"]


@pytest.mark.parametrize("field", ["active", "revoked"])
def test_source_withdrawal_hides_goal_practice_without_changing_saved_review(scope, field):
    scope.item("inside")
    assert len(scope.queue()) == 1
    document = scope.db.get(Document, "book")
    setattr(document, field, field == "revoked")
    scope.db.flush()
    assert scope.queue() == []
    assert scope.db.get(ReviewEntry, "review-inside") is not None


def test_goal_membership_is_applied_before_the_200_row_queue_limit(scope):
    for index in range(201):
        scope.item(f"outside-{index:03}", section="outside-section")
    scope.item("inside-last")
    assert [row["item_id"] for row in scope.queue()] == ["inside-last"]


def test_explicit_owned_goal_card_can_have_no_textbook_source(scope):
    scope.item("inside")
    for identity, goal_id in (("selected-card", "goal"), ("global-card", None)):
        note = StudyNote(
            id=identity,
            owner_id=scope.actor.id,
            title=identity,
            content="A personal recall prompt and answer.",
            kind="review_card",
            goal_id=goal_id,
        )
        scope.db.add(note)
        scope.db.add(
            ReviewEntry(
                id="review-" + identity,
                owner_id=scope.actor.id,
                note_id=identity,
                due_at=utcnow(),
                error_categories=[],
                attempt_count=0,
                correct_count=0,
                scheduling_reason="Personal self-report, not graded mastery",
            )
        )
    scope.db.flush()
    scoped = scope.queue()
    assert {row["note_id"] for row in scoped if row["target_type"] == "personal_review_card"} == {
        "selected-card"
    }
    card = next(row for row in scoped if row["note_id"] == "selected-card")
    assert card["card_source"] is None and card["correct_count"] == 0
    assert len(scope.queue(None)) == 3


def test_review_projection_rejects_a_foreign_goal_even_when_called_directly(scope):
    scope.item("inside")
    goal = scope.db.get(StudyGoal, "other-goal")
    row = scope.db.get(ReviewEntry, "review-inside")
    with pytest.raises(AppError) as failure:
        service.review_out(scope.db, scope.actor, row, goal=goal)
    assert failure.value.code == "NOT_FOUND"


def test_loaded_modules_come_from_the_candidate_tree():
    root = Path(__file__).resolve().parents[2]
    assert Path(service.__file__).resolve().is_relative_to(root / "backend")
    assert Path(router.__file__).resolve().is_relative_to(root / "backend")
