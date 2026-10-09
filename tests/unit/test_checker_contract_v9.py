"""Private development tests for bounded checker formatting; no semantic labels."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from generation import GenerationService, ModelConfig, RequestBudget
from generation.checker_contract import (
    LEGACY_POLICY,
    SCHEMA_CORRECTIONS_POLICY,
    correction_limit,
)
from generation.reliability_v4 import ClaimVariant
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer


def successor(**values):
    return req(checker_contract_policy=SCHEMA_CORRECTIONS_POLICY, **values)


def forbidden(messages):
    value = checker(messages)
    value["claims"][0]["reason_detail"] = "Semantic material cannot be silently dropped."
    return value


def duplicate(messages):
    value = checker(messages)
    value["claims"].append(deepcopy(value["claims"][0]))
    return value


def run(values, request=None, budget=None):
    adapter = Script(values)
    result = GenerationService(adapter).generate(request or successor(), budget or RequestBudget())
    return result, adapter


@pytest.mark.parametrize("defect", [forbidden, duplicate])
def test_two_structural_corrections_preserve_draft_and_require_full_final_validation(defect):
    out, adapter = run([answer(), defect, defect, checker])
    assert out.succeeded, out.error
    assert out.response == out.drafts[0]["response"]
    assert len(out.drafts) == 1
    assert out.budget["consumed_calls"] == 4
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "checker_contract_repair",
        "checker_contract_repair",
    ]
    assert [c["accepted"] for c in out.checks] == [False, False, True]
    assert len({c["projection_hash"] for c in out.checks}) == 1
    initial_messages = adapter.calls[1][0]
    assert adapter.calls[2][0][: len(initial_messages)] == initial_messages
    assert adapter.calls[3][0][: len(initial_messages)] == initial_messages
    assert "STRICT CLAIM RECORD EXAMPLES" in initial_messages[0]["content"]
    assert "Semantic material cannot be silently dropped" not in adapter.calls[2][0][-1]["content"]
    if defect is forbidden:
        assert "reason_detail" in out.checks[0]["raw_text"]
        assert "typed_judgment_raw_aliases" not in out.checks[0]


def test_legacy_default_keeps_one_correction_and_original_prompt():
    out, adapter = run([answer(), forbidden, forbidden], request=req())
    assert not out.succeeded and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == 3
    assert out.token_budget["checker_contract_policy"] == LEGACY_POLICY
    assert "STRICT CLAIM RECORD EXAMPLES" not in adapter.calls[1][0][0]["content"]


def test_valid_successor_answer_keeps_the_normal_two_call_path():
    out, adapter = run([answer(), checker])
    assert out.succeeded, out.error
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert out.response == out.drafts[0]["response"]


@pytest.mark.parametrize("valid_final", [True, False])
def test_generator_format_repair_consumes_the_same_four_call_budget(valid_final):
    malformed_draft = {**answer(), "extra": "Not allowed."}
    out, adapter = run(
        [malformed_draft, answer(), forbidden, checker if valid_final else forbidden]
    )
    assert out.succeeded is valid_final
    assert len(adapter.calls) == out.budget["consumed_calls"] == 4
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "generation_format_repair",
        "joint_check",
        "checker_contract_repair",
    ]
    if not valid_final:
        assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"


@pytest.mark.parametrize("maximum", [2, 3, 4])
def test_persistent_malformed_checks_stop_at_the_original_shared_call_limit(maximum):
    out, _ = run(
        [answer(), forbidden, forbidden, forbidden], budget=RequestBudget(max_calls=maximum)
    )
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == len(out.attempts) == maximum
    assert all(not row["accepted"] for row in out.checks)


@pytest.mark.parametrize("gate", ["scope_ok", "evidence_display_ok", "cumulative_ok"])
def test_repaired_json_cannot_bypass_any_teaching_or_source_disclosure_gate(gate):
    def rejected(messages):
        return checker(messages, **{gate: False})

    out, _ = run(
        [answer(), forbidden, duplicate, rejected],
        request=successor(teaching_context={"teaching_mode": "hint", "help_level": 1}),
    )
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 4
    assert out.delivered_projection == {}


def test_final_schema_valid_partial_claim_remains_semantically_rejected():
    def partial(messages):
        value = checker(messages, body_ok=False)
        value["claims"][0]["status"] = "partial"
        return value

    out, _ = run([answer(), forbidden, duplicate, partial])
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.checks[-1]["judgment"]["claims"][0]["status"] == "partial"
    assert out.budget["consumed_calls"] == 4


def test_checker_correction_then_semantic_rejection_explains_unavailable_recheck():
    def partial(messages):
        value = checker(messages, body_ok=False)
        value["claims"][0]["status"] = "partial"
        return value

    out, adapter = run([answer(), forbidden, partial])
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(adapter.calls) == out.budget["consumed_calls"] == 3
    diagnostic = out.error["details"]["publication_block"]
    assert diagnostic == out.checks[-1]["publication_block"]
    assert diagnostic["stop_reason"] == "insufficient_calls_for_repair_and_recheck"
    assert diagnostic["remaining_provider_calls"] == 1
    assert diagnostic["required_calls_for_repair_and_recheck"] == 2
    assert diagnostic["checker_contract_repair_calls"] == 1
    assert diagnostic["checker_reported_non_supported_factual_claims"] == 1
    assert not diagnostic["checker_reported_body_ok"]
    assert "body_ok" in diagnostic["failed_checker_gate_names"]
    assert diagnostic["checker_reported_coverage"] == "full"
    assert out.delivered_projection == {}


def test_final_semantic_recheck_rejection_has_distinct_stop_reason():
    def partial(messages):
        value = checker(messages, body_ok=False)
        value["claims"][0]["status"] = "partial"
        return value

    out, adapter = run([answer(), partial, answer(), partial])
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(adapter.calls) == out.budget["consumed_calls"] == 4
    diagnostic = out.error["details"]["publication_block"]
    assert diagnostic["stop_reason"] == "final_recheck_rejected"
    assert diagnostic["remaining_provider_calls"] == 0
    assert diagnostic["required_calls_for_repair_and_recheck"] == 0
    assert diagnostic["checker_contract_repair_calls"] == 0
    assert "body_ok" in diagnostic["failed_checker_gate_names"]
    assert out.delivered_projection == {}


def test_final_schema_valid_forged_source_is_rejected():
    def forged(messages):
        value = checker(messages)
        value["requirements"][0]["evidence"][0]["quote"] = "Unseen invented source words."
        return value

    out, _ = run([answer(), forbidden, duplicate, forged])
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert not out.checks[-1]["accepted"]
    assert out.budget["consumed_calls"] == 4


def test_semantic_repair_sequence_keeps_its_two_passes_and_no_extra_checker_call():
    def partial(messages):
        value = checker(messages, body_ok=False)
        value["claims"][0]["status"] = "partial"
        return value

    out, _ = run([answer(), partial, answer(), checker])
    assert out.succeeded, out.error
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.budget["consumed_calls"] == 4


def test_schema_error_on_fourth_call_still_fails_without_fifth_call():
    def partial(messages):
        value = checker(messages, body_ok=False)
        value["claims"][0]["status"] = "partial"
        return value

    out, _ = run([answer(), partial, answer(), forbidden])
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == 4


def test_non_schema_contract_contradictions_keep_one_correction():
    def pessimistic(messages):
        return checker(messages, body_ok=False)

    out, _ = run([answer(), pessimistic, pessimistic])
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == 3


def test_mixed_history_does_not_turn_semantic_contract_rechecks_into_extra_schema_calls():
    out, _ = run([answer(), lambda m: checker(m, body_ok=False), forbidden])
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == 3


def test_active_timeout_prevents_an_extra_correction():
    budget = RequestBudget()

    def timed_out(messages):
        value = forbidden(messages)
        budget.active_seconds = 180
        return value

    out, _ = run([answer(), timed_out], budget=budget)
    assert out.response is None
    assert out.error["code"] == "BUDGET_EXHAUSTED"
    assert out.budget["consumed_calls"] == 2
    assert out.budget["max_active_seconds"] == 180


def test_examples_do_not_bypass_complete_prompt_window_accounting():
    out, _ = run([answer(), checker])
    check_budget = next(
        row for row in out.token_budget["stage_token_budgets"] if row["stage"] == "joint_check"
    )
    cap = check_budget["input_reserved_tokens"] + check_budget["output_reserved_tokens"] - 1
    model = replace(ModelConfig(), window_tokens=cap)
    limited, adapter = run([answer()], request=successor(checker_config=model))
    assert limited.response is None and limited.error["code"] == "CONTEXT_LIMIT"
    assert len(adapter.calls) == 1


def test_every_variant_example_is_strictly_valid_and_forbids_unknown_fields():
    path = Path(__file__).resolve().parents[2] / "generation/prompts/checker_contract_v3.txt"
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("{")
    ]
    assert {row["basis"] for row in rows} == {
        "textbook",
        "problem_input",
        "derived_calculation",
        "nonfactual",
        "evidence_limitation",
        "general_knowledge",
    }
    assert len({row["claim_id"] for row in rows}) == len(rows) == 6
    adapter: TypeAdapter[Any] = TypeAdapter(ClaimVariant)
    for row in rows:
        assert adapter.validate_python(row).model_dump() == row
        with pytest.raises(ValidationError, match="extra_forbidden"):
            adapter.validate_python({**row, "reason_detail": "Forbidden."})


@pytest.mark.parametrize(
    "issue",
    [
        {"code": "FRAGMENT_IDENTITY_MISMATCH"},
        {"code": "CHECKER_SCHEMA_INVALID"},
        {"code": "CHECKER_SCHEMA_INVALID", "parse_code": "UNKNOWN_INTERNAL_VALUE"},
        {"code": "BODY_REJECTED_WITH_ALL_FACTS_SUPPORTED"},
    ],
)
def test_unknown_source_and_semantic_failures_never_receive_second_contract_correction(issue):
    assert correction_limit(SCHEMA_CORRECTIONS_POLICY, [[issue]]) == 1


def test_unknown_policy_fails_before_any_provider_submission():
    out, adapter = run([], request=req(checker_contract_policy="unregistered"))
    assert out.response is None
    assert out.error["details"]["validation_code"] == "UNKNOWN_CHECKER_CONTRACT_POLICY"
    assert not adapter.calls
