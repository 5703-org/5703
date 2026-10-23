"""Saved numeric tolerances govern grading and durable practice effects."""

import math
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.db.models  # Register referenced ORM tables without opening a database.
from app.modules.learning_product import grading, service
from app.modules.learning_product.models import (
    PracticeAttempt,
    PracticeItem,
    PracticeProgress,
    ReviewEntry,
)
from contracts.study import NumericKey, PracticeResponse, PracticeRubric, StepKey


@pytest.mark.parametrize("kind", ["numeric", "step"])
@pytest.mark.parametrize(
    "expected,answer,unit",
    [
        (1e-15, 0.0, "mol"),
        (-1e-15, 0.0, "mol"),
        (0.0, 1e-15, "mol"),
        (1e-13, 5e-13, "m"),
        (5e-324, 0.0, "mg"),
        (1e-15, 0.0, "degC"),
        (0.35, math.nextafter(0.35, math.inf), "m"),
    ],
)
def test_zero_saved_tolerances_reject_different_values_at_every_scale(kind, expected, answer, unit):
    key = NumericKey(value=expected, unit=unit)
    rubric = PracticeRubric(
        numeric=key if kind == "numeric" else None,
        steps=[StepKey(id="one", prompt="Record the quantity.", numeric=key)]
        if kind == "step"
        else [],
        explanation="Private worked solution",
    )
    result = grading.grade(kind, PracticeResponse(value=answer, unit=unit, step=1), rubric)
    assert result["outcome"] == "incorrect"
    assert result["error_categories"] == ["calculation_error"]
    assert result["semantic_correctness_verified"] is None
    assert "Private" not in str(result)


@pytest.mark.parametrize(
    "expected,expected_unit,answer,answer_unit",
    [
        (0.35, "m", 35.0, "cm"),
        (10.0, "m/s", 36.0, "km/h"),
        (14.4, "km/h", 4.0, "m/s"),
        (273.15, "K", 0.0, "degC"),
        (0.0, "degC", 273.15, "K"),
        (-40.0, "degC", 233.15, "K"),
        (5e-324, "mg", 5e-324, "mg"),
        (1e-15, "mol", 1e-15, "mol"),
    ],
)
def test_exact_decimal_unit_conversions_need_no_hidden_tolerance(
    expected, expected_unit, answer, answer_unit
):
    result = grading.grade(
        "numeric",
        PracticeResponse(value=answer, unit=answer_unit),
        PracticeRubric(
            numeric=NumericKey(value=expected, unit=expected_unit),
            explanation="Private worked solution",
        ),
    )
    assert result["outcome"] == "correct"


@pytest.mark.parametrize(
    "key,answer,answer_unit,outcome",
    [
        (NumericKey(value=1e-15, unit="mol", absolute_tolerance=1e-16), 1.1e-15, "mol", "correct"),
        (
            NumericKey(value=1e-15, unit="mol", absolute_tolerance=1e-16),
            1.2e-15,
            "mol",
            "incorrect",
        ),
        (NumericKey(value=1e-15, unit="mol", relative_tolerance=0.01), 1.01e-15, "mol", "correct"),
        (
            NumericKey(value=1e-15, unit="mol", relative_tolerance=0.01),
            1.02e-15,
            "mol",
            "incorrect",
        ),
        (NumericKey(value=1e-15, unit="mol", relative_tolerance=0.01), 0.0, "mol", "incorrect"),
        (NumericKey(value=-100.0, unit="m", relative_tolerance=0.01), -101.0, "m", "correct"),
        (NumericKey(value=100.0, unit="m", relative_tolerance=0.01), 101.01, "m", "correct"),
        (NumericKey(value=1e-10, unit="cm", absolute_tolerance=1e-12), 1.01e-12, "m", "correct"),
        (NumericKey(value=1e-10, unit="cm", absolute_tolerance=1e-12), 1.02e-12, "m", "incorrect"),
    ],
)
def test_only_saved_absolute_or_relative_tolerance_can_accept_an_inexact_value(
    key, answer, answer_unit, outcome
):
    result = grading.grade(
        "numeric",
        PracticeResponse(value=answer, unit=answer_unit),
        PracticeRubric(numeric=key, explanation="Private worked solution"),
    )
    assert result["outcome"] == outcome


def test_existing_finite_conversion_limit_remains_explicit():
    rubric = PracticeRubric(
        numeric=NumericKey(value=1e308, unit="km"), explanation="Private worked solution"
    )
    assert grading.validate_rubric("numeric", [], rubric) == ["numeric_key_range"]
    result = grading.grade("numeric", PracticeResponse(value=1e308, unit="km"), rubric)
    assert result["outcome"] == "insufficient"
    assert result["error_categories"] == ["numeric_range"]


def test_wrong_tiny_numeric_value_does_not_complete_or_increment_durable_correct_count():
    """Use actual SQLAlchemy persistence and the production grade/effects consumer."""
    engine = create_engine("sqlite:///:memory:")
    try:
        for model in (PracticeItem, PracticeProgress, PracticeAttempt, ReviewEntry):
            model.__table__.create(engine)
        actor = SimpleNamespace(id="synthetic-learner")
        rubric = PracticeRubric(
            numeric=NumericKey(value=1e-15, unit="mol"),
            explanation="Private worked solution",
        )
        response = PracticeResponse(value=0.0, unit="mol")
        result = grading.grade("numeric", response, rubric)
        with Session(engine) as db:
            item = PracticeItem(
                id="synthetic-item",
                workspace_id="synthetic-workspace",
                creator_id="synthetic-author",
                group_id="synthetic-group",
                item_revision=1,
                state="published",
                public_payload={"kind": "numeric"},
                private_rubric=rubric.model_dump(),
                source={},
                validation={},
                content_hash="synthetic-content",
            )
            progress = PracticeProgress(id="synthetic-progress", owner_id=actor.id, item_id=item.id)
            db.add_all([item, progress])
            db.flush()
            attempt = PracticeAttempt(
                id="synthetic-attempt",
                owner_id=actor.id,
                item_id=item.id,
                progress_id=progress.id,
                idempotency_key="synthetic-numeric-attempt",
                body_hash="synthetic-body",
                item_revision=1,
                response=response.model_dump(),
                feedback=result,
                progress_version=1,
            )
            db.add(attempt)
            db.flush()
            service.apply_attempt_effects(db, actor, item, attempt, progress, result)
            db.commit()
        with Session(engine) as db:
            saved_progress = db.get(PracticeProgress, "synthetic-progress")
            saved_attempt = db.get(PracticeAttempt, "synthetic-attempt")
            review = db.scalar(select(ReviewEntry))
            assert saved_attempt.feedback["outcome"] == "incorrect"
            assert saved_progress.state == "awaiting_attempt"
            assert saved_progress.current_step == 1
            assert review.attempt_count == 1
            assert review.correct_count == 0
            assert "incorrect" in review.scheduling_reason
    finally:
        engine.dispose()
