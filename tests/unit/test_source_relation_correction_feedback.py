"""Authored offline corrections test the contract, never live semantic accuracy."""

from copy import deepcopy

import pytest

from generation import GenerationService, ModelConfig, RequestBudget
from generation.source_relations import VERSION as V1
from generation.source_relations_v2 import VERSION as V2, assess_source_relations
from test_answer_core_v5 import req
from test_enhancement_generation import Script, answer
from test_source_relation_contract import (
    check_input,
    mismatched_quote,
    relation_checker,
)
from test_source_relation_units_v2 import local_fixture, unit_checker


def unassessed_unit(messages):
    value = unit_checker(messages)
    data = check_input(messages)
    row = value["claims"][0]
    selected = {fid for citation in row["citations"] for fid in citation["fragment_ids"]}
    row["units"][0]["fragment_ids"] = [
        next(f["fragment_id"] for f in data["SOURCE_FRAGMENTS"] if f["fragment_id"] not in selected)
    ]
    return value


@pytest.mark.parametrize(
    "policy,invalid,checker,schema",
    [
        (V1, mismatched_quote, relation_checker, "joint_check_source_relations_v1"),
        (V2, unassessed_unit, unit_checker, "joint_check_source_relations_v2"),
    ],
)
@pytest.mark.parametrize("negative", [False, True])
def test_source_contract_correction_keeps_its_actual_schema_and_honest_verdict(
    policy, invalid, checker, schema, negative
):
    def corrected(messages):
        feedback = messages[-1]["content"]
        assert "Return the complete " + schema + " schema" in feedback
        assert "Return the complete joint_check_v5 schema." not in feedback
        value = checker(messages)
        if negative:
            row = value["claims"][0]
            unit = row["units"][0] if policy == V2 else row["obligations"][0]
            unit.update(
                status="partial",
                reason="Authored honest partial; preserve this verdict.",
            )
        return value

    adapter = Script([answer(), invalid, corrected])
    request = req(
        source_relation_policy=policy,
        config=ModelConfig(window_tokens=32768, tokenizer_provider="estimate"),
    )
    out = GenerationService(adapter).generate(request, RequestBudget(max_calls=3))
    assert out.budget["consumed_calls"] == 3
    assert len(adapter.calls) == 3
    assert adapter.calls[1][1]["response_schema_name"] == schema
    assert adapter.calls[2][1]["response_schema_name"] == schema
    assert check_input(adapter.calls[1][0]) == check_input(adapter.calls[2][0])
    if negative:
        assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
        assert (
            "SOURCE_RELATION_PARTIAL"
            in out.checks[-1]["source_relation_assessment"]["semantic_defect_codes"]
        )
    else:
        assert out.succeeded, out.error
        assert out.checks[-1]["source_relation_assessment"]["accepted"]
    assert not out.checks[-1]["source_relation_assessment"]["source_entailment_locally_certified"]


def test_missing_assessment_identifies_exact_source_without_filling_or_changing_units():
    values = local_fixture()
    values[0]["claims"][0]["units"][1]["fragment_ids"] = ["F002"]
    original = deepcopy(values)
    contract, defects, assessment = assess_source_relations(*values)
    assert contract == [
        {
            "code": "RELATION_ASSESSED_FRAGMENT_MISMATCH",
            "claim_id": "c",
            "unit_id": "U02",
            "fragment_id": "F002",
            "evidence_id": "ev_001",
        }
    ]
    assert values == original
    assert not defects and not assessment["accepted"]
    assert assessment["claims"][0]["obligations"][0]["status"] == "supported"
    assert assessment["claims"][0]["obligations"][1]["fragment_ids"] == ["F002"]
    assert not assessment["source_entailment_locally_certified"]
