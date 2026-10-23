"""Authored policy transport and failure fixtures; zero semantic quality labels."""

from copy import deepcopy
from dataclasses import replace

import pytest

from generation import GenerationRequest, GenerationService, RequestBudget
from generation import coverage_v2, coverage_v3, coverage_v4, teaching_plan_v6
from generation.coverage_query_policy_v1 import (
    VERSION,
    CATALOG_SHA256,
    freeze_policy,
    validate_policy,
    validate_request,
    submission_fields,
    resolve_coverage,
)
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, answer
from test_unit_definition_coverage_v5 import GAS, UNIT_FACET, supplied, evidence


def context(**changes):
    return {
        "mode": "interactive_chat",
        "condition": "E1",
        "answer_mode": "textbook",
        "enhancement_version": "learning_enhancement_v1",
        "reliability_policy": "evidence_reliability_v5",
        "generation_policy": teaching_plan_v6.freeze_generation_policy(),
        **changes,
    }


@pytest.mark.parametrize("base", [coverage_v3, coverage_v4])
def test_exact_policy_is_detached_and_legacy_base_is_explicit(base):
    value = freeze_policy(base.VERSION)
    assert value == {
        "version": VERSION,
        "base_version": base.VERSION,
        "catalog_sha256": CATALOG_SHA256,
    }
    assert validate_policy(value, base_version=base.VERSION) == value
    assert validate_policy(value, base_version=base.VERSION) is not value
    copy = validate_policy(value, base_version=base.VERSION)
    copy["catalog_sha256"] = "0" * 64
    assert value == freeze_policy(base.VERSION)


@pytest.mark.parametrize(
    "mutation",
    ["extra", "missing", "version", "base_version", "catalog_sha256", "type", "list", "bool"],
)
def test_unknown_modified_or_incomplete_policy_fails_closed(mutation):
    value = freeze_policy(coverage_v3.VERSION)
    if mutation == "extra":
        value["allow_semantic_support"] = True
    elif mutation == "missing":
        value.pop("catalog_sha256")
    elif mutation == "type":
        value["base_version"] = True
    elif mutation == "list":
        value = []
    elif mutation == "bool":
        value = True
    else:
        value[mutation] = "wrong"
    with pytest.raises(ValueError, match="COVERAGE_QUERY_POLICY_MISMATCH"):
        validate_policy(value, base_version=coverage_v3.VERSION)


@pytest.mark.parametrize("base", [coverage_v2, coverage_v3, coverage_v4])
def test_absent_frozen_field_returns_exact_legacy_module_and_functions(base):
    result = resolve_coverage(None, base, **context(mode="benchmark_openqa", condition="E0"))
    assert result is base
    assert result.assess_evidence_coverage is base.assess_evidence_coverage
    assert result.supplement_once is base.supplement_once
    assert (
        GenerationRequest("r", "benchmark_openqa", "E0", "Question").coverage_query_policy is None
    )


@pytest.mark.parametrize(
    "source,expected",
    [
        ("off", coverage_v3.VERSION),
        ("source_relation_contract_v1", coverage_v4.VERSION),
        ("source_relation_contract_v2", coverage_v4.VERSION),
    ],
)
def test_submission_opt_in_freezes_selected_base_and_catalog_without_changing_default(
    source, expected
):
    assert submission_fields("off", source_relation_policy=source, answer_mode="textbook") == {}
    assert (
        submission_fields(VERSION, source_relation_policy=source, answer_mode="general_knowledge")
        == {}
    )
    assert submission_fields(VERSION, source_relation_policy=source, answer_mode="textbook") == {
        "coverage_query_policy": freeze_policy(expected)
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "benchmark_openqa"},
        {"mode": "benchmark_mcq"},
        {"condition": "E0"},
        {"answer_mode": "general_knowledge"},
        {"enhancement_version": None},
        {"reliability_policy": "evidence_reliability_v4"},
        {"generation_policy": None},
        {"generation_policy": {"version": []}},
        {"generation_policy": {"version": "generation_controls_v2"}},
    ],
)
def test_enabled_policy_rejects_incompatible_modes_before_any_callback(changes):
    with pytest.raises(ValueError, match="COVERAGE_QUERY_POLICY_INCOMPATIBLE"):
        resolve_coverage(freeze_policy(coverage_v3.VERSION), coverage_v3, **context(**changes))


def test_base_mismatch_never_silently_changes_source_relation_or_coverage():
    with pytest.raises(ValueError, match="COVERAGE_QUERY_POLICY_MISMATCH"):
        resolve_coverage(freeze_policy(coverage_v4.VERSION), coverage_v3, **context())
    with pytest.raises(ValueError, match="COVERAGE_QUERY_BASE_UNKNOWN"):
        resolve_coverage(freeze_policy(coverage_v3.VERSION), coverage_v2, **context())


@pytest.mark.parametrize("base", [coverage_v3, coverage_v4])
def test_consumer_supplement_and_post_packing_assessor_share_frozen_policy_and_original_requirements(
    base,
):
    value = freeze_policy(base.VERSION)
    dispatcher = resolve_coverage(value, base, **context())
    understanding = supplied(GAS, UNIT_FACET)
    prior = deepcopy(understanding)
    calls, phases = [], []
    returned = evidence("new", "Joule, mole, kelvin, pressure and volume are authored search cues.")
    final, after, trace = dispatcher.supplement_once(
        GAS,
        [],
        understanding,
        teaching_plan_v6.freeze_generation_policy(),
        retrieve=lambda query, limit: calls.append((query, limit)) or [returned],
        rerank=lambda query, rows: rows,
        screen=lambda query, rows: (rows, {"reason": "authored fixture"}),
        checkpoint=lambda phase, current: phases.append(phase),
    )
    assert len(calls) == trace["retrieval_passes"] == 1
    assert calls == [
        ("SI unit definitions for joule, mole, kelvin. Units of pressure, volume.", 10)
    ]
    assert final == [returned]
    assert phases == ["retrieving", "reranking", "completed"]
    packed = dispatcher.assess_evidence_coverage(
        GAS,
        final,
        understanding,
        selected_evidence=[],
        excluded_evidence=[{"chunk_id": "new", "reason": "evidence_ceiling"}],
    )
    assert after["base_coverage_version"] == packed["base_coverage_version"] == base.VERSION
    assert trace["before"]["coverage_query_plan"]["catalog_sha256"] == value["catalog_sha256"]
    assert packed["semantic_sufficiency"] is None
    assert understanding == prior
    assert (
        packed["candidate_coverage"]
        == base.assess_evidence_coverage(
            GAS,
            final,
            understanding,
            selected_evidence=[],
            excluded_evidence=[{"chunk_id": "new", "reason": "evidence_ceiling"}],
        )["candidate_coverage"]
    )


def test_unknown_unit_retains_original_targeted_query_and_one_pass():
    question = "Which pressure units are compatible with 2 unknownunit without heating?"
    understanding = supplied(question)
    dispatcher = resolve_coverage(freeze_policy(coverage_v3.VERSION), coverage_v3, **context())
    expected = coverage_v3.assess_evidence_coverage(question, [], understanding)
    calls = []
    _, report, trace = dispatcher.supplement_once(
        question,
        [],
        understanding,
        teaching_plan_v6.freeze_generation_policy(),
        retrieve=lambda query, limit: calls.append((query, limit)) or [],
        rerank=lambda query, rows: rows,
        screen=lambda query, rows: (rows, {}),
        checkpoint=lambda *_: None,
    )
    assert calls == [(expected["targeted_query"], 10)]
    assert trace["reason"] == "completed" and trace["retrieval_passes"] == 1
    assert report["coverage_query_plan"]["status"] == "unknown_unit_token"
    assert report["semantic_sufficiency"] is None


@pytest.mark.parametrize(
    "mutation", ["hash", "base", "legacy", "E0", "benchmark", "general", "source_unknown"]
)
def test_actual_generation_service_rejects_policy_mismatch_or_incompatibility_with_zero_calls(
    mutation,
):
    value = req(
        generation_policy=teaching_plan_v6.freeze_generation_policy(),
        coverage_query_policy=freeze_policy(coverage_v3.VERSION),
    )
    if mutation == "hash":
        value.coverage_query_policy["catalog_sha256"] = "0" * 64
    elif mutation == "base":
        value.source_relation_policy = "source_relation_contract_v1"
    elif mutation == "legacy":
        value.reliability_policy = "evidence_reliability_v4"
    elif mutation == "E0":
        value.condition = "E0"
    elif mutation == "benchmark":
        value.mode = "benchmark_openqa"
    elif mutation == "general":
        value.answer_mode = "general_knowledge"
    else:
        value.source_relation_policy = []
    script = Script([])
    out = GenerationService(script).generate(value, RequestBudget())
    assert out.error["code"] == "COVERAGE_QUERY_CONFIGURATION_ERROR"
    assert out.response is None and out.budget["consumed_calls"] == 0 and script.calls == []


def test_actual_checked_generation_reports_same_frozen_query_policy_without_semantic_waiver():
    value = req(
        generation_policy=teaching_plan_v6.freeze_generation_policy(),
        coverage_query_policy=freeze_policy(coverage_v3.VERSION),
    )
    frozen = deepcopy(value.coverage_query_policy)
    transport = Script([answer(), checker])
    out = GenerationService(transport).generate(value, RequestBudget())
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == len(transport.calls) == 2
    assert out.token_budget["coverage_query_policy"] == frozen
    assert out.token_budget["context_coverage"]["version"] == "context_coverage_v5"
    assert out.token_budget["context_coverage"]["base_coverage_version"] == coverage_v3.VERSION
    assert (
        out.token_budget["context_coverage"]["semantic_sufficiency"]["independent_evaluation"]
        is False
    )
    assert out.checks[0]["accepted"] is True
    assert value.coverage_query_policy == frozen


def test_missing_field_still_runs_exact_old_checked_assessment_and_report_shape():
    value = req(generation_policy=teaching_plan_v6.freeze_generation_policy())
    out = GenerationService(Script([answer(), checker])).generate(value, RequestBudget())
    assert out.succeeded, out.error
    assert out.token_budget["context_coverage"]["version"] == coverage_v3.VERSION
    assert "coverage_query_policy" not in out.token_budget


def test_query_planner_cannot_waive_actual_final_semantic_rejection():
    def negative(messages):
        value = checker(messages, body_ok=False)
        value["claims"][0]["status"] = "unsupported"
        return value

    value = req(
        generation_policy=teaching_plan_v6.freeze_generation_policy(),
        coverage_query_policy=freeze_policy(coverage_v3.VERSION),
    )
    transport = Script([answer(), negative, answer(), negative])
    out = GenerationService(transport).generate(value, RequestBudget())
    assert out.response is None and out.delivered_projection == {}
    assert out.budget["consumed_calls"] == len(transport.calls) == 4
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.checks[-1]["accepted"] is False


def test_source_bound_requirements_keep_their_existing_nonlocatable_status():
    question = "Explain the selected passage."
    understanding = supplied(question)
    understanding["required_knowledge"][0]["origin"] = "verified_selected_source_referent_v1"
    understanding["required_knowledge"][0].pop("request_span")
    before = deepcopy(understanding)
    dispatcher = resolve_coverage(freeze_policy(coverage_v3.VERSION), coverage_v3, **context())
    report = dispatcher.assess_evidence_coverage(question, [], understanding)
    assert report["targeted_query"] is None
    assert report["coverage_query_plan"]["query"] is None
    assert understanding == before
