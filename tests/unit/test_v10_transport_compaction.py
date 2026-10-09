"""Lossless V10 transport and bounded repair flow, with scripted responses only."""

import json

import pytest

from generation import GenerationService, RequestBudget, teaching_plan_v10
from test_enhancement_generation import Script
from test_hint_task_alignment_v10 import CASES, generated_context, hint, judgment, request
from test_teaching_plan_v9 import request as previous_request


def context_wire(messages):
    return next(
        row["content"].removeprefix("CONTEXT_DATA_JSON:\n")
        for row in messages
        if row["content"].startswith("CONTEXT_DATA_JSON:\n")
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_v10_context_preserves_all_fields_strings_and_original_conditions(case):
    value = request(case)
    script = Script([hint("Use the supplied conditions.", case["useful"]), judgment(case)])
    out = GenerationService(script, checker_adapter=script).generate(
        value, RequestBudget(max_calls=2)
    )
    assert out.succeeded, out.error
    wire = context_wire(script.calls[0][0])
    data = json.loads(wire)
    assert wire == teaching_plan_v10.serialize_checker_input(data)
    assert len(wire.encode()) < len(json.dumps(data, ensure_ascii=False, sort_keys=True).encode())
    assert data["PRACTICE_CONTEXT"] == value.teaching_context["practice_context"]
    assert data["TEACHING_ACTION_PLAN"]["recorded_step_goal"]["operation"] == case["goal"]
    assert data == generated_context(script.calls[0][0])


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_v9_transport_still_uses_the_original_byte_representation(case):
    script = Script([hint("Use the supplied conditions.", case["useful"]), judgment(case)])
    out = GenerationService(script, checker_adapter=script).generate(
        previous_request(case), RequestBudget(max_calls=2)
    )
    assert out.succeeded, out.error
    wire = context_wire(script.calls[0][0])
    assert wire == json.dumps(json.loads(wire), ensure_ascii=False, sort_keys=True)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_v10_repair_and_recheck_keep_complete_feedback_and_four_call_limit(case):
    def rejected(messages):
        value = judgment(case)(messages)
        value["specific_help"] = False
        return value

    script = Script(
        [
            hint("Use the supplied conditions.", case["readback"]),
            rejected,
            hint("Use the supplied conditions.", case["useful"]),
            judgment(case),
        ]
    )
    out = GenerationService(script, checker_adapter=script).generate(
        request(case), RequestBudget(max_calls=4)
    )
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4 and len(script.calls) == 4
    message = script.calls[2][0][-1]["content"]
    wire = message.split("REPAIR_DATA_JSON:\n", 1)[1]
    data = json.loads(wire)
    assert wire == teaching_plan_v10.serialize_checker_input(data)
    assert data["judgment"]["specific_help"] is False
    assert data["draft"]["answer_text"]
    assert data["original_claims"] and data["repair_plan"]
    assert "protected_exact_claims" in data and "teaching_repair_boundary" in data
    assert data["protected_exact_claims"] == []
    assert data["teaching_repair_boundary"]["release_source_supported_claims_for_repair"] is True
    assert out.checks[0]["accepted"] is False and out.checks[-1]["accepted"] is True


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
@pytest.mark.parametrize("level", [2, 3])
def test_higher_hint_levels_keep_their_existing_approved_claim_boundary(case, level):
    def rejected(messages):
        value = judgment(case)(messages)
        value["specific_help"] = False
        return value

    script = Script(
        [
            hint("Use the supplied conditions.", case["readback"]),
            rejected,
            hint("Use the supplied conditions.", case["useful"]),
            judgment(case),
        ]
    )
    out = GenerationService(script, checker_adapter=script).generate(
        request(case, help_level=level), RequestBudget(max_calls=4)
    )
    assert not out.succeeded and out.error["code"] == "REPAIR_CHANGED_APPROVED_CONTENT"
    assert out.response is None and len(script.calls) == 3


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
@pytest.mark.parametrize("gate", ["specific_help", "scope_ok"])
def test_released_h1_claims_still_require_a_successful_final_full_check(case, gate):
    def first_rejected(messages):
        value = judgment(case)(messages)
        value["specific_help"] = False
        return value

    def final_rejected(messages):
        value = judgment(case)(messages)
        value[gate] = False
        return value

    script = Script(
        [
            hint("Use the supplied conditions.", case["readback"]),
            first_rejected,
            hint("Use the supplied conditions.", case["useful"]),
            final_rejected,
        ]
    )
    out = GenerationService(script, checker_adapter=script).generate(
        request(case), RequestBudget(max_calls=4)
    )
    assert not out.succeeded and out.response is None
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 4 and len(script.calls) == 4
    assert out.checks[-1]["accepted"] is False
