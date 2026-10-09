"""Practice checks certify bounded rules, not independent semantic correctness."""

import pytest
from pydantic import ValidationError
from contracts.study import (
    KnowledgePoint,
    NumericKey,
    PracticeFeedback,
    PracticeResponse,
    PracticeRubric,
    StepKey,
)
from app.modules.learning_product.grading import grade, validate_rubric


@pytest.mark.parametrize(
    "value,unit,outcome,error",
    [
        (200.0, "cm", "correct", None),
        (2.0, "m", "correct", None),
        (2.0, "s", "incorrect", "unit_error"),
        (3.0, "m", "incorrect", "calculation_error"),
        (2.0, '__import__("os")', "incorrect", "unit_error"),
        (None, "m", "insufficient", "missing_value"),
    ],
)
def test_numeric_dimension_conversion_and_unsafe_unit(value, unit, outcome, error):
    rubric = PracticeRubric(
        numeric=NumericKey(value=2.0, unit="m"), explanation="Private worked answer"
    )
    result = grade("numeric", PracticeResponse(value=value, unit=unit), rubric)
    assert result["outcome"] == outcome
    assert result["error_categories"] == ([error] if error else [])
    assert result["semantic_correctness_verified"] is None
    assert "Private" not in str(result)


def test_affine_temperature_and_explicit_tolerance():
    rubric = PracticeRubric(
        numeric=NumericKey(value=273.15, unit="K", absolute_tolerance=0.01),
        explanation="Freezing point",
    )
    assert grade("numeric", PracticeResponse(value=0.0, unit="°C"), rubric)["outcome"] == "correct"
    assert (
        grade("numeric", PracticeResponse(value=0.02, unit="°C"), rubric)["outcome"] == "incorrect"
    )


@pytest.mark.parametrize(
    "selection,outcome",
    [([], "insufficient"), (["A"], "partial"), (["A", "C"], "correct"), (["A", "B"], "incorrect")],
)
def test_multiselect_exact_set_without_correct_option_disclosure(selection, outcome):
    result = grade(
        "multiselect",
        PracticeResponse(selection=selection),
        PracticeRubric(correct_option_ids=["A", "C"], explanation="Private key"),
    )
    assert result["outcome"] == outcome
    assert "correct_option_ids" not in result


def test_short_required_points_and_contradictions_require_model_assessment():
    rubric = PracticeRubric(
        required_points=[
            KnowledgePoint(id="direction", terms=["higher to lower"]),
            KnowledgePoint(id="motion", terms=["net movement"]),
        ],
        forbidden_terms=["requires ATP"],
        explanation="Private key",
    )
    partial = grade("short", PracticeResponse(text="Net movement of particles"), rubric)
    assert partial["outcome"] == "pending_review" and partial["missing_point_ids"] == []
    bad = grade(
        "short", PracticeResponse(text="Net movement from higher to lower requires ATP"), rubric
    )
    assert bad["outcome"] == "pending_review"
    assert grade("short", PracticeResponse(text=""), rubric)["outcome"] == "insufficient"


def test_negated_required_expression_cannot_complete_a_practice_step():
    rubric = PracticeRubric(
        required_points=[KnowledgePoint(id="energy", terms=["light energy"])],
        explanation="Private solution",
    )
    negated = grade(
        "short", PracticeResponse(text="Photosynthesis does not use light energy."), rubric
    )
    assert negated["outcome"] == "pending_review"
    assert negated["grading_method"] == "pending_model_assessment_v1"
    assert negated["missing_point_ids"] == []
    assert negated["error_categories"] == []
    assert "light energy" not in negated["message"]
    assert (
        grade("short", PracticeResponse(text="Photosynthesis uses light energy."), rubric)[
            "outcome"
        ]
        == "pending_review"
    )
    assert (
        PracticeFeedback.model_validate(
            {
                "outcome": "correct",
                "message": "Historical result",
                "grading_method": "deterministic_rules_v1",
            }
        ).grading_method
        == "deterministic_rules_v1"
    )


def test_authored_negative_answers_are_not_awarded_a_lexical_pass():
    rubric = PracticeRubric(
        acceptable_answers=["The process does not require ATP."],
        required_points=[KnowledgePoint(id="energy", terms=["ATP"])],
        explanation="Private solution",
    )
    assert (
        grade("short", PracticeResponse(text="The process does not require ATP."), rubric)[
            "outcome"
        ]
        == "pending_review"
    )
    assert (
        grade("short", PracticeResponse(text="It uses not only ATP."), rubric)["outcome"]
        == "pending_review"
    )


def test_step_cannot_skip_to_hidden_next_step():
    rubric = PracticeRubric(
        steps=[
            StepKey(id="one", prompt="Choose a variable", acceptable_answers=["x"]),
            StepKey(id="two", prompt="Compute it", numeric=NumericKey(value=4.0, unit="m")),
        ],
        explanation="Private two-step solution",
    )
    assert (
        grade("step", PracticeResponse(step=2, value=4.0, unit="m"), rubric, 1)["outcome"]
        == "irrelevant"
    )
    assert (
        grade("step", PracticeResponse(step=1, text="x"), rubric, 1)["outcome"] == "pending_review"
    )


def test_structural_validation_rejects_unsolvable_or_duplicate_choices():
    rubric = PracticeRubric(correct_option_ids=["missing"], explanation="Private answer")
    issues = validate_rubric(
        "mcq", [{"id": "A", "text": "Same"}, {"id": "A", "text": "Same"}], rubric
    )
    assert set(issues) == {"duplicate_options", "invalid_choice_key"}
    assert validate_rubric("short", [], PracticeRubric(explanation="No rules")) == [
        "missing_text_rule"
    ]


def test_nonfinite_and_unknown_key_fields_rejected_before_grading():
    with pytest.raises(ValidationError):
        PracticeResponse(value=float("nan"))
    with pytest.raises(ValidationError):
        PracticeResponse.model_validate({"text": "answer", "correct_option_ids": ["A"]})


def test_finite_inputs_cannot_overflow_into_a_false_numeric_pass():
    rubric = PracticeRubric(numeric=NumericKey(value=1e308, unit="km"), explanation="Huge value")
    assert validate_rubric("numeric", [], rubric) == ["numeric_key_range"]
    result = grade("numeric", PracticeResponse(value=1e308, unit="km"), rubric)
    assert result["outcome"] == "insufficient" and result["error_categories"] == ["numeric_range"]


def test_blank_and_duplicate_step_rules_cannot_publish():
    rubric = PracticeRubric(
        steps=[
            StepKey(
                id="one",
                prompt="Try",
                required_points=[
                    KnowledgePoint(id="point", terms=[" "]),
                    KnowledgePoint(id="point", terms=["x"]),
                ],
                acceptable_answers=[" "],
            )
        ],
        explanation="Private",
    )
    assert set(validate_rubric("step", [], rubric)) == {
        "empty_knowledge_expression",
        "duplicate_knowledge_points",
        "empty_answer_expression",
    }


def test_publisher_objectives_require_an_exact_label_and_cleaned_source_membership():
    from app.modules.learning_product.library import published_objectives

    source = "Learning Objectives\nBy the end of this section, you will be able to:\n• Describe net movement\n• Compare active and passive transport\n\nOther prose"
    assert published_objectives(source, source) == [
        "Describe net movement",
        "Compare active and passive transport",
    ]
    assert published_objectives("• Invented goal\nNo objective heading", source) == []
    assert published_objectives(source, "unrelated replacement") == []
