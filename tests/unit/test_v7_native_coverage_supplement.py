"""Actual native supplement entry points; authored fixtures are not support labels."""

from copy import deepcopy

import pytest

from generation import (
    coverage_v3,
    coverage_v4,
    coverage_v5,
    teaching_plan,
    teaching_plan_v2,
    teaching_plan_v3,
    teaching_plan_v4,
    teaching_plan_v5,
    teaching_plan_v6,
    teaching_plan_v7,
)


QUESTION = "Compare diffusion and osmosis."
ORIGINAL = [
    {"evidence_id": "ev_001", "chunk_id": "diffusion", "text": "Diffusion moves particles."}
]
SUPPLEMENT = [{"evidence_id": "ev_002", "chunk_id": "osmosis", "text": "Osmosis moves water."}]
ENGINES = [coverage_v3, coverage_v4, coverage_v5]


def run_supplement(engine, policy):
    calls = []

    def retrieve(query, limit):
        calls.append((query, limit))
        return deepcopy(SUPPLEMENT)

    result = engine.supplement_once(
        QUESTION,
        deepcopy(ORIGINAL),
        None,
        policy,
        retrieve=retrieve,
        rerank=lambda _, rows: rows,
        screen=lambda _, rows: (rows, {}),
        checkpoint=lambda *_: None,
        **({"base_version": coverage_v3.VERSION} if engine is coverage_v5 else {}),
    )
    return result, calls


@pytest.mark.parametrize("engine", ENGINES, ids=lambda value: value.VERSION)
@pytest.mark.parametrize("arm", ["A", "B", "C", "D"])
def test_explicit_v7_runs_one_native_pass_without_changing_legacy_results(engine, arm):
    policy = teaching_plan_v7.freeze_generation_policy(arm)
    before = deepcopy(policy)
    result, calls = run_supplement(engine, policy)
    legacy_result, legacy_calls = run_supplement(
        engine, teaching_plan_v6.freeze_generation_policy(arm)
    )
    final, coverage, trace = result
    assert result == legacy_result and calls == legacy_calls
    assert final == ORIGINAL + SUPPLEMENT
    assert len(calls) == trace["retrieval_passes"] == 1 and calls[0][1] == 10
    assert trace["added_chunk_ids"] == ["osmosis"]
    assert coverage["semantic_sufficiency"] is None and trace["semantic_sufficiency"] is None
    assert policy == before and policy["version"] == "generation_controls_v7"
    assert teaching_plan_v6.freeze_generation_policy()["version"] == "generation_controls_v6"


@pytest.mark.parametrize("engine", ENGINES, ids=lambda value: value.VERSION)
@pytest.mark.parametrize(
    "change",
    [
        {"version": "generation_controls_unknown"},
        {"targeted_candidate_limit": 11},
        {"provider_planning_calls": 1},
    ],
)
def test_invalid_v7_controls_fail_before_any_native_lookup(engine, change):
    calls = []
    policy = {**teaching_plan_v7.freeze_generation_policy(), **change}
    with pytest.raises(ValueError, match="UNKNOWN_GENERATION_POLICY"):
        engine.supplement_once(
            QUESTION,
            deepcopy(ORIGINAL),
            None,
            policy,
            retrieve=lambda *_: calls.append("retrieve") or [],
            rerank=lambda _, rows: rows,
            screen=lambda _, rows: (rows, {}),
            checkpoint=lambda *_: calls.append("checkpoint"),
            **({"base_version": coverage_v3.VERSION} if engine is coverage_v5 else {}),
        )
    assert calls == []


@pytest.mark.parametrize("engine", ENGINES, ids=lambda value: value.VERSION)
def test_historical_v3_through_v6_keep_exact_supplement_outputs(engine):
    expected = run_supplement(engine, teaching_plan_v3.freeze_generation_policy())
    for version in [teaching_plan_v3, teaching_plan_v4, teaching_plan_v5, teaching_plan_v6]:
        policy = version.freeze_generation_policy()
        before = deepcopy(policy)
        assert run_supplement(engine, policy) == expected
        assert policy == before


@pytest.mark.parametrize("engine", ENGINES, ids=lambda value: value.VERSION)
def test_legacy_v1_v2_are_still_rejected_by_distributed_supplement(engine):
    for version in [teaching_plan, teaching_plan_v2]:
        with pytest.raises(ValueError, match="UNKNOWN_GENERATION_POLICY"):
            run_supplement(engine, version.freeze_generation_policy())
