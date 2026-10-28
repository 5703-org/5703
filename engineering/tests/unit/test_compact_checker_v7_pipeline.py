"""Authored V7 contract/repair paths; independent science scores remain separate."""

import json

import pytest

from generation.checker_encoding_v6 import VERSION as ENCODING, decode
from generation import GenerationService, RequestBudget
from test_compact_checker_pipeline import candidate, compact_checker
from test_enhancement_generation import Script, answer


POLICY = "scoped_compact_v7"


def check(messages):
    value = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
    if value.get("CHECKER_INPUT_ENCODING", {}).get("version") == ENCODING:
        value = decode(value)
    return compact_checker([{"role": "user", "content": json.dumps(value)}])


def partial(messages):
    value = check(messages)
    value["claims"][1]["status"] = "partial"
    value["claims"][1]["units"][0]["status"] = "partial"
    value.update(
        body_ok=False,
        coverage="supported_partial",
        missing_facets=["carbon source"],
        limitations_explicit=False,
    )
    value["requirements"][0].update(
        sufficiency="partial",
        response_coverage="partial",
        missing_information="The answer omits the source's carbon condition.",
    )
    return value


def patch(messages):
    data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[-1])
    assert any(
        row["claim_id"] == data["original_claims"][0]["claim_id"]
        for row in data["protected_exact_claims"]
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


def draft():
    return answer(
        "Photosynthesis uses light energy. [ev_001] The source of carbon is unrestricted. [ev_001]"
    )


def run(steps, *, policy=POLICY, calls=4, **changes):
    adapter = Script(steps)
    out = GenerationService(adapter).generate(
        candidate(joint_checker_policy=policy, **changes), RequestBudget(max_calls=calls)
    )
    return out, adapter


def test_valid_negatives_with_aggregate_contradiction_repair_content_and_finally_recheck():
    out, adapter = run([draft(), partial, patch, check])
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4
    assert len(out.checks) == 2
    first = out.checks[0]
    route = first["semantic_negative_routing"]
    assert route["route"] == "semantic_repair"
    assert "COMPLETE_PARTIAL_WITHOUT_LIMITS" in {
        row["code"] for row in first["original_checker_inconsistencies"]
    }
    assert first["typed_judgment_raw_aliases"]["claims"][1]["status"] == "partial"
    assert not first["accepted"]
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert first["projection_hash"] != out.checks[1]["projection_hash"]
    assert out.checks[1]["accepted"]
    assert "unrestricted" not in out.response["answer_text"]
    assert out.response["answer_text"].startswith("Photosynthesis uses light energy. [ev_001]")


def test_historical_v6_keeps_original_same_draft_correction_path():
    out, adapter = run([draft(), partial, check], policy="scoped_compact_v6")
    assert out.succeeded, out.error
    assert len(out.checks) == 2
    assert out.checks[0]["projection_hash"] == out.checks[1]["projection_hash"]
    assert "semantic_negative_routing" not in out.checks[0]
    assert adapter.calls[2][1]["response_schema_name"] == "joint_check_v6"


@pytest.mark.parametrize("relation", ["irrelevant", "contradictory"])
def test_valid_negative_citation_is_repaired_before_a_fresh_publication_check(relation):
    def negative(messages):
        value = partial(messages)
        for citation in value["claims"][1]["citations"]:
            citation["relation"] = relation
        return value

    out, adapter = run([draft(), negative, patch, check])
    assert out.succeeded, out.error
    first, final = out.checks
    route = first["semantic_negative_routing"]
    assert route["route"] == "semantic_repair"
    assert "ACTUAL_CITATION_" + relation.upper() in {
        issue["code"] for issue in route["semantic_issues"]
    }
    assert first["typed_judgment_raw_aliases"]["claims"][1]["citations"][0]["relation"] == relation
    assert not first["accepted"] and final["accepted"]
    assert first["projection_hash"] != final["projection_hash"]
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert out.budget["consumed_calls"] == 4
    assert not any(attempt["stage"] == "checker_contract_repair" for attempt in out.attempts)
    assert out.response["answer_text"].startswith("Photosynthesis uses light energy. [ev_001]")
    assert "unrestricted" not in out.response["answer_text"]


def test_v7_negative_cannot_publish_without_a_budget_for_final_repair_check():
    out, _ = run([draft(), partial], calls=2)
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.checks[0]["semantic_negative_routing"]["route"] == "semantic_repair"


def test_named_requirement_gap_remains_blocking_after_aggregate_deferral():
    def gap(messages):
        value = check(messages)
        value["limitations_explicit"] = True
        value["requirements"][0].update(
            sufficiency="partial",
            response_coverage="limitation",
            missing_information="A necessary source condition is absent.",
        )
        return value

    out, _ = run([answer(), gap], calls=2)
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    route = out.checks[0]["semantic_negative_routing"]
    assert route["route"] == "semantic_repair"
    assert "REQUIREMENT_GAP" in {row["code"] for row in route["semantic_issues"]}
    assert "FULL_COVERAGE_WITH_REQUIREMENT_GAP" in {
        row["code"] for row in route["deferred_aggregate_issues"]
    }


def test_honest_limited_partial_context_does_not_create_a_new_negative():
    def limited(messages):
        value = check(messages)
        value.update(
            coverage="supported_partial",
            missing_facets=["source condition"],
            limitations_explicit=True,
        )
        value["requirements"][0].update(
            sufficiency="partial",
            response_coverage="partial",
            missing_information="A requested condition is absent from current sources.",
        )
        return value

    out, _ = run([answer(), limited])
    assert out.succeeded, out.error
    assert out.token_budget["answer_completeness"]["status"] == "partial"
    assert out.checks[0]["semantic_negative_routing"]["route"] == "ordinary_validation"


def test_final_changed_draft_still_requires_its_own_positive_assessment():
    out, _ = run([draft(), partial, patch, partial])
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert out.budget["consumed_calls"] == 4 and len(out.checks) == 2
    assert out.checks[0]["projection_hash"] != out.checks[1]["projection_hash"]
    assert not out.checks[0]["accepted"] and not out.checks[1]["accepted"]


def test_true_identity_fault_keeps_contract_failure_even_with_a_valid_negative():
    def bad(messages):
        value = partial(messages)
        value["claims"][1]["units"][0]["fragment_ids"] = ["F999"]
        return value

    out, _ = run([draft(), bad], calls=2)
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.checks[0]["semantic_negative_routing"]["route"] == "contract_correction"
    assert out.checks[0]["checker_inconsistencies"]


@pytest.mark.parametrize("policy", ["typed_joint_v5", "scoped_compact_v6"])
def test_historical_policies_never_select_new_encoding(policy):
    from test_answer_core_v5 import checker

    out, _ = run(
        [answer(), check if policy == "scoped_compact_v6" else checker],
        policy=policy,
        checker_payload_policy="lossless_checker_tables_v1",
    )
    assert out.succeeded, out.error
    assert all(row["encoding"] != ENCODING for row in out.token_budget["checker_payload_encodings"])


def test_new_payload_policy_round_trips_exact_checked_input_without_replacing_verdicts():
    out, adapter = run([answer(), check], checker_payload_policy="lossless_checker_tables_v1")
    assert out.succeeded, out.error
    report = out.token_budget["checker_payload_encodings"][0]
    assert report["saved_encoding_policy"] == ENCODING
    assert report["original_data_sha256"] == report["decoded_data_sha256"]
    assert report["all_claim_text_preserved"] and report["all_fragment_text_preserved"]
    assert not report["local_semantic_support_certified"]
    assert adapter.calls[1][1]["response_schema_name"] == "joint_check_v6"
