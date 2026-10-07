"""Scripted full publication paths; these are contract probes, not quality labels."""

from copy import deepcopy
import json

import pytest

from generation import GenerationService, ModelConfig, RequestBudget
from generation.checked import generate_unchecked_research
from generation.checker_encoding import decode
from generation.local_repair import VERSION as PATCH_POLICY
from generation.reliability_v6 import VERSION
from retrieval.source_spans import text_hash
from test_answer_core_v5 import checker, req
from test_enhancement_generation import Script, TEXT, answer, request as base_request


def candidate(**overrides):
    values = {
        "joint_checker_policy": VERSION,
        "config": ModelConfig(provider="openai", model="gpt-4o-mini"),
        "repair_policy": PATCH_POLICY,
        "reliability_policy": "evidence_reliability_v5",
    }
    values.update(overrides)
    return base_request(**values)


def input_data(messages):
    data = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
    if "CHECKER_INPUT_ENCODING" in data:
        data = decode(data)
    if "SOURCE_FRAGMENT_TABLE" in data:
        table = data["SOURCE_FRAGMENT_TABLE"]
        data["SOURCE_FRAGMENTS"] = [dict(zip(table["columns"], row)) for row in table["rows"]]
    return data


def compact_checker(messages):
    data = input_data(messages)
    value = checker(messages)
    units = {row["claim_id"]: row["units"] for row in data["COMPACT_CLAIM_UNITS"]}
    for row in value["claims"]:
        if row["basis"] not in {"nonfactual", "evidence_limitation"}:
            fids = [
                fid for citation in row.get("citations", []) for fid in citation["fragment_ids"]
            ]
            row["units"] = [
                {
                    "unit_id": unit["unit_id"],
                    "status": row["status"],
                    "relation_preserved": True,
                    "conditions_preserved": True,
                    "reason": "Authored transport probe.",
                    **({"fragment_ids": fids} if row["basis"] == "textbook" else {}),
                }
                for unit in units[row["claim_id"]]
            ]
    for point in value["requirements"]:
        for evidence in point["evidence"]:
            evidence.pop("quote")
            evidence["quote_ref"] = evidence["fragment_id"] + ":Q01"
    target = data["REQUEST_TARGET"]
    value["request_target"] = {
        "target_id": target["target_id"],
        "status": target["input_status"],
        "fragment_ids": [row["fragment_id"] for row in target["proven_fragments"]],
    }
    return value


def run(script, value=None, calls=4):
    adapter = Script(script)
    outcome = GenerationService(adapter).generate(
        value or candidate(), RequestBudget(max_calls=calls)
    )
    return outcome, adapter


def test_success_retains_every_final_gate_actual_source_ids_and_raw_contract():
    out, adapter = run([answer(), compact_checker])
    assert out.succeeded, out.error
    assert adapter.calls[1][1]["response_schema_name"] == "joint_check_v6"
    assert out.budget["consumed_calls"] == 2
    check = out.checks[0]
    assert check["joint_checker_policy"] == VERSION
    assert "request_target" in check["typed_judgment_raw_aliases"]
    assert "request_target" not in check["expanded_typed_judgment_raw_aliases"]
    unit = check["compact_assessment"]["claims"][0]["units"][0]
    assert all(fid.startswith("span_") for fid in unit["fragment_ids"])
    assert all(row["fragment_id"].startswith("span_") for row in unit["source_quotes"])
    assert check["compact_assessment_raw_aliases"]["claims"][0]["units"][0]["fragment_ids"] == [
        "F001"
    ]
    assert out.token_budget["claim_support"]["accepted"] is True
    assert out.token_budget["compact_joint_support"]["human_rating"] is None
    assert out.delivered_projection["content_hash"] == check["delivered_projection_hash"]


@pytest.mark.parametrize(
    ("selected_text", "coverage"), [(TEXT.split(".")[0] + ".", "complete"), (TEXT, "partial")]
)
def test_literal_selection_presence_and_exact_source_mapping_reach_checker(selected_text, coverage):
    reading = {
        "version": "reading_scope_v1",
        "release_id": "release-fixture",
        "scope": "passage",
        "document_id": "d1",
        "processing_id": "p1",
        "source_unit_id": "u1",
        "section": "Photosynthesis",
        "scope_hash": "a" * 64,
        "selection": {
            "start": 0,
            "end": len(selected_text),
            "text": selected_text,
            "text_hash": text_hash(selected_text),
            "unit_text_hash": text_hash(TEXT),
        },
    }
    out, adapter = run([answer(), compact_checker], candidate(reading_context=reading))
    assert out.succeeded, out.error
    data = input_data(adapter.calls[1][0])
    assert data["READING_CONTEXT"]["selection"]["text"] == selected_text
    assert data["REQUEST_TARGET"]["input_status"] == "present"
    assert data["REQUEST_TARGET"]["source_coverage"] == coverage
    target = out.checks[0]["compact_assessment"]["request_target"]
    assert target["assessed_status"] == "present"
    assert target["fact_support_certified"] is False
    assert target["proven_fragment_ids"][0].startswith("span_")


def test_false_missing_selection_is_contract_failure_without_fabricated_support():
    def missing(messages):
        value = compact_checker(messages)
        value["request_target"]["status"] = "missing"
        return value

    out, _ = run([answer(), missing], calls=2)
    assert out.response is None
    assert out.error["code"] == "CHECKER_INCONSISTENT"
    assert "REQUEST_TARGET_PRESENCE_STATUS_MISMATCH" in out.error["details"]["issue_codes"]
    assert not out.checks[0]["accepted"]


def test_negative_unit_blocks_an_optimistic_compound_and_routes_local_repair():
    draft = answer(
        "Photosynthesis uses light energy. [ev_001] Plants create matter from nothing. [ev_001]"
    )

    def rejected(messages):
        value = compact_checker(messages)
        # Deliberately preserve the contradictory aggregate as raw diagnostic
        # data. The independently negative unit must prevent its publication.
        value["claims"][1]["units"][0]["status"] = "unsupported"
        return value

    def patch(messages):
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[-1])
        kept = {row["claim_id"] for row in data["protected_exact_claims"]}
        assert data["original_claims"][0]["claim_id"] in kept
        assert data["original_claims"][1]["claim_id"] not in kept
        assert all(
            action["action"] == "support_required_content_or_narrow_optional_assertion"
            for action in data["repair_plan"]["actions"]
            if action["code"].startswith("COMPACT_")
        )
        return {
            "edits": [
                {
                    "claim_id": data["original_claims"][1]["claim_id"],
                    "replacement_text": "Carbon dioxide supplies carbon for sugar. [ev_001]",
                }
            ],
            "append_answer_text": "",
        }

    out, adapter = run([draft, rejected, patch, compact_checker])
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4 and len(out.checks) == 2
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert out.checks[0]["typed_judgment_raw_aliases"]["body_ok"] is True
    assert out.checks[0]["checker_inconsistencies"] == []
    assert "COMPACT_UNIT_UNSUPPORTED" in {row["code"] for row in out.checks[0]["structural_issues"]}
    assert out.response["answer_text"].startswith("Photosynthesis uses light energy. [ev_001]")
    assert "nothing" not in out.response["answer_text"]
    assert out.checks[-1]["accepted"] is True
    assert out.checks[0]["projection_hash"] != out.checks[1]["projection_hash"]


@pytest.mark.parametrize("field", ["body_ok", "requirements", "request_target"])
def test_absent_independent_judgment_is_never_filled_or_published(field):
    def invalid(messages):
        value = compact_checker(messages)
        value.pop(field)
        return value

    out, _ = run([answer(), invalid], calls=2)
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == 2


@pytest.mark.parametrize(
    "field", ["scope_ok", "evidence_display_ok", "cumulative_ok", "attempt_evaluation_ok"]
)
def test_hint_and_feedback_gates_survive_the_compact_contract(field):
    def invalid(messages):
        value = compact_checker(messages)
        value[field] = False
        return value

    from generation.teaching_plan_v2 import freeze_generation_policy

    hint = candidate(
        teaching_context={"teaching_mode": "hint", "current_problem": "Explain photosynthesis."},
        generation_policy=freeze_generation_policy(),
    )
    out, _ = run([answer(), invalid], hint, calls=2)
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"


@pytest.mark.parametrize(
    "change",
    [
        {"joint_checker_policy": "unknown"},
        {"source_relation_policy": "source_relation_contract_v2"},
        {"reliability_policy": "evidence_reliability_v4"},
        {"config": ModelConfig()},
        {"enhancement_version": None},
    ],
)
def test_incompatible_frozen_axes_fail_before_any_transport_call(change):
    out, adapter = run([], candidate(**change))
    assert out.response is None
    assert out.error["code"] in {
        "UNKNOWN_JOINT_CHECKER_POLICY",
        "JOINT_CHECKER_POLICY_INCOMPATIBLE",
    }
    assert adapter.calls == []


def test_unchecked_research_cannot_silently_ignore_the_requested_checker():
    with pytest.raises(ValueError, match="INVALID_UNCHECKED_RESEARCH_CONTROL"):
        generate_unchecked_research(GenerationService(Script([])), candidate())


def test_legacy_default_keeps_original_schema_and_budget():
    out, adapter = run([answer(), checker], req())
    assert out.succeeded
    assert adapter.calls[1][1]["response_schema_name"] == "joint_check_v5"
    assert out.budget["consumed_calls"] == 2
    assert "compact_joint_support" not in out.token_budget


def test_expansion_cannot_publish_duplicate_conflicting_actual_citations():
    def conflicting(messages):
        value = compact_checker(messages)
        contradictory = deepcopy(value["claims"][0]["citations"][0])
        contradictory["relation"] = "contradictory"
        value["claims"][0]["citations"].append(contradictory)
        return value

    out, _ = run([answer(), conflicting], calls=2)
    assert out.response is None
    assert not out.checks[0]["accepted"]
