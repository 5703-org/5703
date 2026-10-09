"""Bounded deterministic practice checks; no expression eval or semantic truth claim."""

import math
import re
import unicodedata
from contracts.study import PracticeFeedback, PracticeRubric, PracticeResponse


# dimension, scale to base, affine offset. All supported units are explicit.
UNITS = {
    "": ("dimensionless", 1.0, 0.0),
    "1": ("dimensionless", 1.0, 0.0),
    "m": ("length", 1.0, 0.0),
    "cm": ("length", 0.01, 0.0),
    "mm": ("length", 0.001, 0.0),
    "km": ("length", 1000.0, 0.0),
    "s": ("time", 1.0, 0.0),
    "min": ("time", 60.0, 0.0),
    "h": ("time", 3600.0, 0.0),
    "kg": ("mass", 1.0, 0.0),
    "g": ("mass", 0.001, 0.0),
    "mg": ("mass", 0.000001, 0.0),
    "K": ("temperature", 1.0, 0.0),
    "°C": ("temperature", 1.0, 273.15),
    "degC": ("temperature", 1.0, 273.15),
    "Pa": ("pressure", 1.0, 0.0),
    "kPa": ("pressure", 1000.0, 0.0),
    "atm": ("pressure", 101325.0, 0.0),
    "L": ("volume", 0.001, 0.0),
    "mL": ("volume", 0.000001, 0.0),
    "m^3": ("volume", 1.0, 0.0),
    "m/s": ("speed", 1.0, 0.0),
    "km/h": ("speed", 1 / 3.6, 0.0),
    "m/s^2": ("acceleration", 1.0, 0.0),
    "N": ("force", 1.0, 0.0),
    "J": ("energy", 1.0, 0.0),
    "mol": ("amount", 1.0, 0.0),
    "mol/L": ("concentration", 1.0, 0.0),
    "M": ("concentration", 1.0, 0.0),
}


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def contains(text, phrase):
    return bool(re.search(r"(?<!\w)" + re.escape(normalized(phrase)) + r"(?!\w)", normalized(text)))


def negates_required_expression(text, phrase):
    """Catch a narrow explicit negation before a lexically matched rubric phrase."""
    expression = re.escape(normalized(phrase))
    negation = (
        r"(?:\bnot\b(?!\s+only\b)|\bnever\b|\bno\b|\bwithout\b|"
        r"\bcannot\b|\b(?:can't|doesn't|don't|isn't|aren't)\b)"
    )
    return bool(
        re.search(
            negation + r"(?:\s+[a-z0-9'-]+){0,3}\s+" + expression + r"(?!\w)",
            normalized(text),
        )
    )


def feedback(outcome, message, covered=(), missing=(), errors=()):
    return PracticeFeedback(
        outcome=outcome,
        message=message,
        covered_point_ids=list(covered),
        missing_point_ids=list(missing),
        error_categories=list(errors),
    ).model_dump()


def numeric_grade(response, key):
    if response.value is None:
        return feedback(
            "insufficient", "Enter a numeric value and its unit.", errors=["missing_value"]
        )
    if key.unit not in UNITS or response.unit not in UNITS:
        return feedback(
            "incorrect", "Use a supported unit for this quantity.", errors=["unit_error"]
        )
    target, actual = UNITS[key.unit], UNITS[response.unit]
    if target[0] != actual[0]:
        return feedback(
            "incorrect", "The unit has a different physical dimension.", errors=["unit_error"]
        )
    expected = key.value * target[1] + target[2]
    value = response.value * actual[1] + actual[2]
    absolute = key.absolute_tolerance * abs(target[1])
    if not all(math.isfinite(v) for v in (expected, value, absolute)):
        return feedback(
            "insufficient",
            "The numeric conversion exceeds the supported finite range.",
            errors=["numeric_range"],
        )
    if math.isclose(value, expected, abs_tol=max(absolute, 1e-12), rel_tol=key.relative_tolerance):
        return feedback("correct", "The value and unit satisfy the saved numeric rule.")
    return feedback(
        "incorrect",
        "Check your calculation after converting to consistent units.",
        errors=["calculation_error"],
    )


def legacy_text_grade(response, acceptable, points, forbidden):
    """Retained historical diagnostic; never authority for a new submission."""
    text = response.text.strip()
    if not text:
        return feedback(
            "insufficient", "Write an explanation before submitting.", errors=["missing_response"]
        )
    if any(contains(text, value) for value in forbidden):
        return feedback(
            "incorrect",
            "The response includes a saved contradictory statement.",
            errors=["concept_misconception"],
        )
    if normalized(text) in {normalized(v) for v in acceptable}:
        return feedback("correct", "The response matches a saved acceptable expression.")
    covered: list[str] = []
    missing: list[str] = []
    negated: list[str] = []
    for point in points:
        matched = any(contains(text, term) for term in point.terms)
        if any(
            contains(text, term) and negates_required_expression(text, term) for term in point.terms
        ):
            negated.append(point.id)
            matched = False
        (covered if matched else missing).append(point.id)
    if negated:
        return feedback(
            "insufficient",
            "A key idea in your explanation is negated. Clarify whether it applies before trying again.",
            covered,
            missing,
            ["ambiguous_negation"],
        )
    if points and not missing:
        return feedback(
            "correct",
            "All saved knowledge-point expressions were found. This is a rule-based check, not a semantic review.",
            covered,
        )
    if covered:
        return feedback(
            "partial",
            "Some required points are present; revise the missing points.",
            covered,
            missing,
            ["incomplete_expression"],
        )
    return feedback(
        "incorrect",
        "The response did not match the saved acceptable expressions.",
        covered,
        missing,
        ["concept_misconception"],
    )


def grade(kind, response, rubric, current_step=1):
    response = PracticeResponse.model_validate(response) if isinstance(response, dict) else response
    rubric = PracticeRubric.model_validate(rubric) if isinstance(rubric, dict) else rubric
    if kind in ("mcq", "multiselect"):
        selected, correct = set(response.selection), set(rubric.correct_option_ids)
        if not selected:
            return feedback(
                "insufficient", "Select an option before submitting.", errors=["missing_response"]
            )
        if selected == correct:
            return feedback("correct", "The selected options match the saved answer rule.")
        if kind == "multiselect" and selected < correct:
            return feedback(
                "partial", "Your selection is incomplete.", errors=["condition_omission"]
            )
        return feedback(
            "incorrect",
            "Revisit the tested concept and try another selection.",
            errors=["concept_misconception"],
        )
    if kind == "numeric":
        return numeric_grade(response, rubric.numeric)
    if kind == "short":
        return text_submission_feedback(response)
    if response.step != current_step:
        return feedback(
            "irrelevant", "Submit an attempt for the current step.", errors=["wrong_step"]
        )
    step = rubric.steps[current_step - 1]
    if step.numeric:
        return numeric_grade(response, step.numeric)
    return text_submission_feedback(response)


def pending_feedback(message="Your work is saved and awaiting a model assessment."):
    return PracticeFeedback(
        outcome="pending_review",
        message=message,
        grading_method="pending_model_assessment_v1",
        semantic_correctness_verified=None,
    ).model_dump()


def text_submission_feedback(response):
    if not response.text.strip():
        return feedback(
            "insufficient", "Write an explanation before submitting.", errors=["missing_response"]
        )
    return pending_feedback()


def validate_rubric(kind, options, rubric):
    """Return stable structural reasons without echoing any private key content."""
    rubric = PracticeRubric.model_validate(rubric) if isinstance(rubric, dict) else rubric
    issues = []
    option_ids = [o["id"] if isinstance(o, dict) else o.id for o in options]
    texts = [normalized(o["text"] if isinstance(o, dict) else o.text) for o in options]
    if len(set(option_ids)) != len(option_ids) or len(set(texts)) != len(texts):
        issues.append("duplicate_options")
    if kind in ("mcq", "multiselect"):
        keys = rubric.correct_option_ids
        if (
            len(option_ids) < 2
            or not keys
            or not set(keys) <= set(option_ids)
            or len(set(keys)) != len(keys)
        ):
            issues.append("invalid_choice_key")
        if kind == "mcq" and len(keys) != 1:
            issues.append("single_choice_requires_one_key")
    elif options:
        issues.append("unexpected_options")
    if kind == "numeric" and (rubric.numeric is None or rubric.numeric.unit not in UNITS):
        issues.append("missing_or_unsupported_numeric_key")
    if kind == "short" and not (rubric.acceptable_answers or rubric.required_points):
        issues.append("missing_text_rule")
    if kind == "step":
        if not rubric.steps or len({s.id for s in rubric.steps}) != len(rubric.steps):
            issues.append("missing_or_duplicate_steps")
        for step in rubric.steps:
            if not (step.acceptable_answers or step.required_points or step.numeric):
                issues.append("missing_step_rule")
            if step.numeric and step.numeric.unit not in UNITS:
                issues.append("unsupported_step_unit")
    point_groups = [rubric.required_points, *(s.required_points for s in rubric.steps)]
    if any(not term.strip() for group in point_groups for p in group for term in p.terms):
        issues.append("empty_knowledge_expression")
    if any(len({p.id for p in group}) != len(group) for group in point_groups):
        issues.append("duplicate_knowledge_points")
    expressions = [
        *rubric.acceptable_answers,
        *rubric.forbidden_terms,
        *(a for s in rubric.steps for a in s.acceptable_answers),
    ]
    if any(not v.strip() for v in expressions):
        issues.append("empty_answer_expression")
    for key in [rubric.numeric, *(s.numeric for s in rubric.steps)]:
        if (
            key
            and key.unit in UNITS
            and not all(
                math.isfinite(v)
                for v in (
                    key.value * UNITS[key.unit][1] + UNITS[key.unit][2],
                    key.absolute_tolerance * abs(UNITS[key.unit][1]),
                )
            )
        ):
            issues.append("numeric_key_range")
    return sorted(set(issues))
