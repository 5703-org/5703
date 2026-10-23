"""Goal availability follows native practice visibility on authored SQLite sources."""

from copy import deepcopy
import datetime as dt
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, delete, event, inspect, select
from sqlalchemy.orm import Session

import app.db.models
from app.core.exceptions import AppError
from app.db.base import utcnow
from app.modules.identity.models import Role, User, Workspace
from app.modules.knowledge.models import (
    Chunk,
    CorpusRelease,
    Document,
    DocumentVersion,
    ProcessingRun,
    ReleaseChunk,
    SourceUnit,
)
from app.modules.learning_product import library, router, service
from app.modules.learning_product.models import (
    LearningRecord,
    PracticeAttempt,
    PracticeItem,
    StudyConceptRelation,
    StudyGoal,
    StudyUnit,
)
from contracts.study import GoalOut


@pytest.fixture
def scope():
    engine = create_engine("sqlite:///:memory:")
    models = (
        Workspace,
        Role,
        User,
        Document,
        DocumentVersion,
        ProcessingRun,
        SourceUnit,
        Chunk,
        CorpusRelease,
        ReleaseChunk,
        StudyGoal,
        StudyUnit,
        PracticeItem,
        PracticeAttempt,
        LearningRecord,
        StudyConceptRelation,
    )
    for model in models:
        model.__table__.create(engine)
    db = Session(engine)
    db.add_all(
        [
            Workspace(id="workspace", name="Authored workspace", slug="fixture"),
            Workspace(id="private-workspace", name="Other workspace", slug="other"),
            Role(id=1, name="student"),
            User(
                id="learner",
                email="learner@fixture.invalid",
                hashed_password="unused",
                role_id=1,
                workspace_id="workspace",
            ),
            User(
                id="publisher",
                email="publisher@fixture.invalid",
                hashed_password="unused",
                role_id=1,
                workspace_id="workspace",
            ),
        ]
    )
    db.flush()
    actor = db.get(User, "learner")
    release = CorpusRelease(
        id="release", name="Authored release", state="active", configuration={}, manifest={}
    )
    db.add(release)
    source_rows = {}
    for book in ("book", "other-book"):
        document = Document(id=book, title="Authored " + book, owner_id="publisher")
        version = DocumentVersion(
            id=book + "-version",
            document_id=book,
            raw_hash=library.text_hash(book),
            media_type="text/plain",
            size_bytes=100,
            storage_path="unused",
            original_filename=book,
        )
        processing = ProcessingRun(
            id=book + "-processing",
            document_version_id=version.id,
            config_hash=library.text_hash(book + "-config"),
            configuration={},
            state="validated",
        )
        db.add_all([document, version, processing])
        for index, section in enumerate(("Transport", "Energy")):
            text = f"Authored {book} {section} source passage."
            unit = SourceUnit(
                id=f"{book}-{index}",
                processing_id=processing.id,
                sequence=index,
                page=index + 1,
                section=section,
                raw_text=text,
                cleaned_text=text,
                quality="ok",
                issues=[],
            )
            chunk = Chunk(
                id=f"{book}-chunk-{index}",
                processing_id=processing.id,
                document_id=book,
                text=text,
                text_hash=library.text_hash(text),
                section=section,
                pages=[index + 1],
                spans=[{"unit_id": unit.id}],
                tokens=10,
            )
            db.add_all(
                [
                    unit,
                    chunk,
                    ReleaseChunk(
                        release_id=release.id,
                        chunk_id=chunk.id,
                        embedding=[1.0, 0.0],
                        dimension=2,
                        model_revision="authored-not-a-model",
                    ),
                ]
            )
            source_rows[(book, index)] = (document, unit)
    goal = StudyGoal(
        id="goal",
        owner_id=actor.id,
        title="Authored transport goal",
        document_id="book",
        release_id=release.id,
        depth="beginner",
    )
    document, source_unit = source_rows[("book", 0)]
    study_unit = StudyUnit(
        id="goal-unit",
        goal_id=goal.id,
        section_id=library.section_id(source_unit.processing_id, source_unit.section),
        title=source_unit.section,
        ordinal=0,
        concepts=["transport"],
        prerequisites=[],
        read=True,
    )
    db.add_all([goal, study_unit])
    db.flush()

    def item(
        identity="item",
        *,
        book="book",
        index=0,
        state="published",
        item_workspace="workspace",
        source_changes=None,
        section=None,
        created_at=None,
    ):
        _, unit = source_rows[(book, index)]
        source = library.locator(release.id, book, unit)
        source.update(source_changes or {})
        value = PracticeItem(
            id=identity,
            workspace_id=item_workspace,
            creator_id="publisher",
            group_id=identity,
            item_revision=1,
            state=state,
            public_payload={
                "title": identity,
                "kind": "short",
                "prompt": "Explain this authored transport passage.",
                "options": [],
                "concepts": ["transport"],
                "conditions": [],
            },
            private_rubric={"explanation": "PRIVATE_RUBRIC_SENTINEL"},
            source=source,
            validation={
                "section_id": section or library.section_id(unit.processing_id, unit.section)
            },
            content_hash=library.text_hash(identity),
        )
        if created_at:
            value.created_at = created_at
        db.add(value)
        db.flush()
        return value

    def goal_unit():
        output = service.goal_out(db, actor, goal)
        GoalOut.model_validate(output)
        assert "PRIVATE_RUBRIC_SENTINEL" not in json.dumps(output)
        return output["units"][0]

    def practice(**changes):
        values = dict(
            goal_id=goal.id,
            unit_id=study_unit.id,
            section_id=None,
            concept=None,
            db=db,
            actor=actor,
        )
        return router.practice_list(**{**values, **changes})["data"]

    yield SimpleNamespace(
        db=db,
        actor=actor,
        goal=goal,
        unit=study_unit,
        item=item,
        goal_unit=goal_unit,
        practice=practice,
        sources=source_rows,
        release=release,
    )
    db.close()
    engine.dispose()


def assert_unavailable(scope):
    value = scope.goal_unit()
    assert value["practice_available"] is False
    assert value["practice_availability_reason"] == "no_published_questions"
    assert value["recommended_action"] == "read"
    assert scope.practice() == []
    return value


def test_no_published_questions_preserves_reading_without_suggesting_practice(scope):
    value = assert_unavailable(scope)
    assert value["read"] is True and value["status"] == "read"
    assert value["attempts"] == value["correct_attempts"] == 0


@pytest.mark.parametrize("state", ["draft", "validated", "retired"])
def test_unpublished_item_is_not_available_or_leaked(scope, state):
    scope.item(state=state)
    assert_unavailable(scope)


@pytest.mark.parametrize(
    "changes",
    [
        {"book": "other-book"},
        {"index": 1},
        {"source_changes": {"release_id": "different-release"}},
        {"item_workspace": "private-workspace"},
        {"source_changes": {"text_hash": "f" * 64}},
        {"source_changes": {"source_unit_id": "missing-source-unit"}},
        {"source_changes": {"processing_id": "changed-processing"}},
    ],
)
def test_goal_and_practice_list_agree_on_exact_selection_and_source(scope, changes):
    scope.item(**changes)
    assert_unavailable(scope)


@pytest.mark.parametrize(
    "withdrawal", ["revoked", "inactive", "foreign_owner", "release", "membership"]
)
def test_native_source_withdrawal_hides_availability_without_changing_read_history(
    scope, withdrawal
):
    scope.item()
    assert scope.goal_unit()["practice_available"] and len(scope.practice()) == 1
    document, _ = scope.sources[("book", 0)]
    if withdrawal == "revoked":
        document.revoked = True
    elif withdrawal == "inactive":
        document.active = False
    elif withdrawal == "foreign_owner":
        scope.db.get(User, "publisher").workspace_id = "private-workspace"
    elif withdrawal == "release":
        scope.release.state = "building"
    else:
        scope.db.execute(delete(ReleaseChunk).where(ReleaseChunk.release_id == scope.release.id))
    scope.db.flush()
    value = assert_unavailable(scope)
    assert value["read"] is True and value["status"] == "read"


def test_matching_visible_publication_enables_practice_and_updates_without_cache(scope):
    item = scope.item(state="draft")
    assert_unavailable(scope)
    item.state = "published"
    scope.db.flush()
    value = scope.goal_unit()
    assert value["practice_available"] is True
    assert value["practice_availability_reason"] == "available"
    assert value["recommended_action"] == "practise"
    assert [row["id"] for row in scope.practice()] == [item.id]
    item.state = "retired"
    scope.db.flush()
    assert_unavailable(scope)


def test_matching_item_after_201_unselected_items_is_not_hidden_by_a_global_limit(scope):
    old = utcnow() - dt.timedelta(days=1)
    for index in range(201):
        scope.item(f"unselected-{index}", index=1)
    scope.item("matching-older", created_at=old)
    assert scope.goal_unit()["practice_available"] is True
    assert [row["id"] for row in scope.practice()] == ["matching-older"]


def test_invalid_newer_source_does_not_hide_an_older_visible_question(scope):
    scope.item("invalid-newer", source_changes={"text_hash": "f" * 64})
    scope.item("valid-older", created_at=utcnow() - dt.timedelta(days=1))
    assert scope.goal_unit()["practice_available"] is True
    assert [row["id"] for row in scope.practice()] == ["valid-older"]


def test_each_goal_section_uses_its_own_availability(scope):
    _, source_unit = scope.sources[("book", 1)]
    second = StudyUnit(
        id="second-goal-unit",
        goal_id=scope.goal.id,
        section_id=library.section_id(source_unit.processing_id, source_unit.section),
        title=source_unit.section,
        ordinal=1,
        concepts=[],
        prerequisites=[],
        read=True,
    )
    scope.db.add(second)
    scope.item(index=1)
    output = service.goal_out(scope.db, scope.actor, scope.goal)
    GoalOut.model_validate(output)
    assert [unit["practice_available"] for unit in output["units"]] == [False, True]
    assert [unit["recommended_action"] for unit in output["units"]] == ["read", "practise"]


def test_practice_endpoint_retains_concept_filter_unit_guard_and_visible_200_limit(scope):
    for index in range(201):
        scope.item(f"published-{index}")
    assert len(scope.practice()) == 200
    assert scope.practice(concept="missing-concept") == []
    assert len(scope.practice(concept="TRANSPORT")) == 200
    with pytest.raises(AppError) as mismatch:
        scope.practice(section_id="different-section")
    assert mismatch.value.code == "VALIDATION_FAILED"
    with pytest.raises(AppError) as missing:
        scope.practice(unit_id="missing-unit")
    assert missing.value.code == "NOT_FOUND"
    assert scope.goal_unit()["practice_available"] is True


def test_goal_availability_after_200_visible_rows_validates_each_available_section_once(
    scope, monkeypatch
):
    _, source_unit = scope.sources[("book", 1)]
    scope.db.add(
        StudyUnit(
            id="second-goal-unit",
            goal_id=scope.goal.id,
            section_id=library.section_id(source_unit.processing_id, source_unit.section),
            title=source_unit.section,
            ordinal=1,
            concepts=[],
            prerequisites=[],
            read=True,
        )
    )
    for index in range(201):
        scope.item(f"first-section-{index}")
    scope.item("second-section-older", index=1, created_at=utcnow() - dt.timedelta(days=1))
    original = library.validate_locator
    validated = []

    def observe_native(database, actor, source):
        validated.append(source["source_unit_id"])
        return original(database, actor, source)

    monkeypatch.setattr(library, "validate_locator", observe_native)
    output = service.goal_out(scope.db, scope.actor, scope.goal)
    assert all(unit["practice_available"] for unit in output["units"])
    assert len(validated) == 2 and len(set(validated)) == 2


def test_eligibility_read_does_not_publish_or_mutate_question_keys(scope):
    item = scope.item(state="draft")
    before = deepcopy(
        (
            item.state,
            item.public_payload,
            item.private_rubric,
            item.validation,
            item.source,
            item.version,
            scope.goal.version,
            scope.unit.read,
        )
    )
    assert_unavailable(scope)
    after = (
        item.state,
        item.public_payload,
        item.private_rubric,
        item.validation,
        item.source,
        item.version,
        scope.goal.version,
        scope.unit.read,
    )
    assert after == before
    assert list(scope.db.scalars(select(LearningRecord))) == []


def test_first_yield_loads_a_bounded_public_projection_instead_of_all_questions(scope):
    for index in range(201):
        scope.item(f"published-{index:03}")
    scope.db.expunge_all()
    loaded = []

    @event.listens_for(scope.db, "loaded_as_persistent")
    def record_load(database, row):
        if isinstance(row, PracticeItem):
            loaded.append(row.id)

    items = service.published_visible_practice_items(
        scope.db,
        scope.actor,
        goal=scope.goal,
        sections={scope.unit.section_id},
        first_per_section=True,
    )
    try:
        item = next(items)
        assert 1 <= len(loaded) <= 64
        assert "private_rubric" in inspect(item).unloaded
        service.item_out(item)
        assert "private_rubric" in inspect(item).unloaded
    finally:
        items.close()


def test_later_batch_visible_item_survives_an_entire_invalid_source_batch(scope):
    for index in range(70):
        scope.item(f"unavailable-{index:03}", source_changes={"text_hash": "f" * 64})
    scope.item("visible-older", created_at=utcnow() - dt.timedelta(days=1))
    assert scope.goal_unit()["practice_available"] is True
    assert [row["id"] for row in scope.practice()] == ["visible-older"]


def test_keyset_ties_have_no_skips_or_duplicates_across_batches(scope):
    timestamp = utcnow().replace(microsecond=0)
    expected = []
    for index in range(130):
        identity = f"published-{index:03}"
        scope.item(identity, created_at=timestamp)
        expected.append(identity)
    result = scope.practice()
    assert [row["id"] for row in result] == sorted(expected, reverse=True)
    assert len({row["id"] for row in result}) == 130
