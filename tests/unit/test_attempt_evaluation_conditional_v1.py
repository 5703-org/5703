"""Authored conditional contract regressions, not measured model quality."""

from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from generation import GenerationService, RequestBudget
from generation.attempt_evaluation_contract_v1 import (
    ATTEMPT_CONTEXT_FIELDS,
    NOT_APPLICABLE,
    assessment,
    gate_satisfied,
    normalize_attempt_verdict,
    ordinary_question_without_attempt,
)
from generation.reliability_v5 import OrdinaryQuestionCheckV5, ReliableCheckV5
from generation.reliability_v4 import compact_schema
from generation.semantic_negative_v1 import _shape_safe
from generation.types import ModelConfig
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer


def complete_record():
    return {
        "claims": [],
        "body_ok": True,
        "specific_help": True,
        "scope_ok": True,
        "suggestions_ok": True,
        "evidence_display_ok": True,
        "cumulative_ok": True,
        "complete_answer": True,
        "coverage": "full",
        "missing_facets": [],
        "limitations_explicit": True,
        "reason": "Authored contract fixture.",
        "repair_fragment_ids": [],
        "attempt_evaluation_ok": True,
        "tutor_question_ok": True,
        "requirements": [],
        "non_repetitive_next_action": True,
    }


@pytest.mark.parametrize("history", [None, []])
def test_only_explicit_clean_user_question_has_no_attempt(history):
    context = {"turn_role": "user_question", "attempt_history": history}
    assert ordinary_question_without_attempt(context)
    assert not ordinary_question_without_attempt(context, {"status": "correct"})


@pytest.mark.parametrize("field", ATTEMPT_CONTEXT_FIELDS)
@pytest.mark.parametrize("value", ["current attempt", {}, []])
def test_every_current_attempt_context_value_blocks_not_applicable(field, value):
    assert not ordinary_question_without_attempt({"turn_role": "user_question", field: value})


@pytest.mark.parametrize("context", [None, {}, {"turn_role": "auto"}, {"turn_role": "learner_attempt"}])
def test_missing_unknown_and_real_attempt_roles_keep_required_contract(context):
    assert not ordinary_question_without_attempt(context)


@pytest.mark.parametrize("history", [[{"status": "incorrect"}], "unknown", {}, False])
def test_nonempty_or_untyped_attempt_history_keeps_required_contract(history):
    assert not ordinary_question_without_attempt({"turn_role": "user_question", "attempt_history": history})


def test_missing_field_normalizes_only_to_explicit_inapplicability():
    raw = complete_record()
    raw.pop("attempt_evaluation_ok")
    original = deepcopy(raw)
    normalized = normalize_attempt_verdict(raw, not_applicable=True)
    assert raw == original
    assert set(normalized) == set(raw) | {"attempt_evaluation_ok"}
    typed = OrdinaryQuestionCheckV5.model_validate(normalized).model_dump()
    assert typed["attempt_evaluation_ok"] == NOT_APPLICABLE
    assert assessment(typed, not_applicable=True, missing=True)["learner_evaluation_passed"] is None
    assert assessment(typed, not_applicable=True, missing=True)["normalization"] == "missing_to_not_applicable"


@pytest.mark.parametrize("value", [True, False, None, "invalid"])
def test_existing_returned_verdicts_are_never_rewritten(value):
    raw = complete_record()
    raw["attempt_evaluation_ok"] = value
    assert normalize_attempt_verdict(raw, not_applicable=True) is raw
    if type(value) is bool:
        typed = OrdinaryQuestionCheckV5.model_validate(raw).model_dump()
        assert gate_satisfied(typed, "attempt_evaluation_ok", attempt_not_applicable=True) is value
    else:
        with pytest.raises(ValidationError):
            OrdinaryQuestionCheckV5.model_validate(raw)


@pytest.mark.parametrize("value", [NOT_APPLICABLE, "true", 1, None])
def test_original_real_attempt_schema_remains_strict_boolean(value):
    raw = complete_record()
    raw["attempt_evaluation_ok"] = value
    with pytest.raises(ValidationError):
        ReliableCheckV5.model_validate(raw)


def test_real_attempt_missing_field_is_never_filled():
    raw = complete_record()
    raw.pop("attempt_evaluation_ok")
    assert normalize_attempt_verdict(raw, not_applicable=False) is raw
    with pytest.raises(ValidationError):
        ReliableCheckV5.model_validate(raw)


@pytest.mark.parametrize("field", ["body_ok", "tutor_question_ok", "requirements", "claims"])
def test_other_missing_required_fields_still_fail(field):
    raw = complete_record()
    raw.pop(field)
    with pytest.raises(ValidationError):
        OrdinaryQuestionCheckV5.model_validate(normalize_attempt_verdict(raw, not_applicable=True))


@pytest.mark.parametrize("field", ["body_ok", "tutor_question_ok", "complete_answer", "scope_ok"])
def test_not_applicable_never_discharges_other_gates(field):
    raw = complete_record()
    raw[field] = NOT_APPLICABLE
    assert not gate_satisfied(raw, field, attempt_not_applicable=True)
    with pytest.raises(ValidationError):
        OrdinaryQuestionCheckV5.model_validate(raw)


def test_not_applicable_requires_explicit_context_at_consumer():
    raw = complete_record()
    raw["attempt_evaluation_ok"] = NOT_APPLICABLE
    assert not gate_satisfied(raw, "attempt_evaluation_ok")
    assert gate_satisfied(raw, "attempt_evaluation_ok", attempt_not_applicable=True)
    assert not _shape_safe(raw, {"teaching_mode": "direct"})
    assert _shape_safe(raw, {"teaching_mode": "direct"}, attempt_not_applicable=True)


def test_wire_contract_keeps_every_old_required_field_and_other_definition():
    old = compact_schema(ReliableCheckV5)
    new = compact_schema(OrdinaryQuestionCheckV5)
    assert old["required"] == new["required"]
    assert new["$defs"] == old["$defs"]
    assert {k: v for k, v in new["properties"].items() if k != "attempt_evaluation_ok"} == {
        k: v for k, v in old["properties"].items() if k != "attempt_evaluation_ok"
    }
    assert "not_applicable" in json.dumps(new["properties"]["attempt_evaluation_ok"])


def run_ordinary(checker_result, **context):
    script = Script([answer(), checker_result])
    request = req(teaching_context={"turn_role": "user_question", **context})
    out = GenerationService(script).generate(request, RequestBudget(max_calls=2))
    assert len(script.calls) == 2
    return out, script


def without_attempt(messages):
    value = checker(messages)
    value.pop("attempt_evaluation_ok")
    return value


def test_native_ordinary_missing_attempt_field_preserves_full_publication_checks():
    out, script = run_ordinary(without_attempt)
    assert out.succeeded, out.error
    assert out.response["citations"] == ["ev_001"]
    assert out.checks[0]["accepted"] is True
    assert out.checks[0]["typed_judgment_raw_aliases"]["attempt_evaluation_ok"] == NOT_APPLICABLE
    assert "attempt_evaluation_ok" not in json.loads(out.checks[0]["raw_text"])
    audit = out.token_budget["attempt_evaluation_applicability"]
    assert audit["applicability"] == NOT_APPLICABLE
    assert audit["learner_evaluation_passed"] is None
    assert audit["normalization"] == "missing_to_not_applicable"
    data = json.loads(script.calls[1][0][-1]["content"])
    assert data["ATTEMPT_EVALUATION_APPLICABILITY"]["status"] == NOT_APPLICABLE


def test_explicit_false_ordinary_verdict_still_blocks_publication():
    out, _ = run_ordinary(lambda messages: checker(messages, attempt_evaluation_ok=False))
    assert not out.succeeded and out.response is None
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"


@pytest.mark.parametrize("defect", ["partial", "unsupported", "citation", "requirement_quote", "other_missing"])
def test_scientific_and_citation_defects_survive_attempt_inapplicability(defect):
    def invalid(messages):
        value = without_attempt(messages)
        if defect in {"partial", "unsupported"}:
            value["claims"][0]["status"] = defect
            value["body_ok"] = False
        elif defect == "citation":
            value["claims"][0]["citations"] = []
        elif defect == "requirement_quote":
            value["requirements"][0]["evidence"][0]["quote"] = "Invented quotation."
        else:
            value.pop("body_ok")
        return value

    out, _ = run_ordinary(invalid)
    assert not out.succeeded and out.response is None
    assert out.error["code"] in {"SEMANTIC_CHECK_FAILED", "CHECKER_INCONSISTENT"}


@pytest.mark.parametrize("context", [
    {"learner_attempt": "actual reply"},
    {"last_attempt_evaluation": {"status": "incorrect"}},
    {"attempt_history": [{"status": "incorrect"}]},
])
def test_native_conflicting_user_question_context_keeps_missing_field_failure(context):
    out, _ = run_ordinary(without_attempt, **context)
    assert not out.succeeded and out.response is None
    assert out.error["code"] == "CHECKER_INCONSISTENT"
    assert "attempt_evaluation_applicability" not in out.token_budget


@pytest.mark.parametrize("verdict", ["missing", False, NOT_APPLICABLE])
def test_actual_learner_attempt_still_requires_checked_boolean(verdict):
    def attempt_checker(messages):
        value = checker(messages)
        if verdict == "missing":
            value.pop("attempt_evaluation_ok")
        else:
            value["attempt_evaluation_ok"] = verdict
        return value

    request = req(
        question="Light energy.",
        teaching_context={
            "turn_role": "learner_attempt",
            "learner_attempt": "Light energy.",
            "pending_tutor_question": "What does photosynthesis use?",
            "current_problem": "What does photosynthesis use?",
        },
    )
    draft = answer()
    draft["learner_attempt_evaluation"] = {
        "status": "correct",
        "feedback": "Photosynthesis uses light energy. [ev_001]",
    }
    script = Script([draft, attempt_checker])
    out = GenerationService(script).generate(request, RequestBudget(max_calls=2))
    assert len(script.calls) == 2
    assert not out.succeeded and out.response is None
    assert out.error["code"] == ("SEMANTIC_CHECK_FAILED" if verdict is False else "CHECKER_INCONSISTENT")
    assert "attempt_evaluation_applicability" not in out.token_budget


def compact_config(model="google/gemini-3.5-flash-lite"):
    return ModelConfig(
        provider="openai_compatible",
        model=model,
        base_url="https://openrouter.ai/api/v1",
        temperature=None,
        max_tokens=4096,
        window_tokens=131072,
        structured_output_mode="json_object",
        configuration_id="authored-offline-conditional-compact-v1",
        openrouter_route_profile="gemini35_google_vertex_compact_checker_v3",
    )


def test_independent_compact_wire_keeps_original_full_v5_boolean_schema():
    request = req(
        teaching_context={"turn_role": "user_question"},
        checker_config=compact_config(),
    )
    script = Script([answer(), checker])
    out = GenerationService(adapter=script, checker_adapter=script).generate(
        request, RequestBudget(max_calls=2)
    )
    assert out.succeeded, out.error
    assert script.calls[1][1]["response_schema_name"] == "joint_check_v5"
    assert script.calls[1][1]["response_schema"] == compact_schema(ReliableCheckV5)
    assert "attempt_evaluation_applicability" not in out.token_budget


def test_invalid_compact_wire_config_retains_structured_failure():
    request = req(
        teaching_context={"turn_role": "user_question"},
        checker_config=compact_config(model="wrong-model"),
    )
    script = Script([])
    out = GenerationService(adapter=script, checker_adapter=script).generate(
        request, RequestBudget(max_calls=2)
    )
    assert not out.succeeded and out.response is None
    assert out.error["code"] == "ENHANCEMENT_VALIDATION_ERROR"
    assert script.calls == []
