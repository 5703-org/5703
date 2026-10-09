"""Authored V8 identity and publication probes, not answer-quality labels."""

from copy import deepcopy
import json

import pytest

from generation import GenerationService, RequestBudget
from generation.citation_scope_v8 import VERSION, citation_scope
from generation.checker_encoding_v6 import decode, encode
from generation.reliability_v6 import compact_check_context, expand_compact_judgment
from test_answer_core_v5 import checker as typed_checker
from test_compact_checker_pipeline import candidate
from test_compact_checker_v7_pipeline import check
from test_compact_joint_check_v6 import fixture
from test_enhancement_generation import Script, answer


def context():
    data, verdict = fixture()
    return compact_check_context(data), verdict


def run(steps, *, policy=VERSION, calls=4, **changes):
    adapter = Script(steps)
    outcome = GenerationService(adapter).generate(
        candidate(joint_checker_policy=policy, **changes), RequestBudget(max_calls=calls)
    )
    return outcome, adapter


def test_identity_scope_is_exact_inert_and_lossless_with_full_original_sources():
    data, _ = context()
    before = deepcopy(data)
    scope = citation_scope(data)
    row = scope["claims"][0]
    assert row["actual_citations"] == data["ACTUAL_CITATION_BINDINGS"][0]["citations"]
    assert row["units"] == [
        {key: unit[key] for key in ("unit_id", "start", "end")}
        for unit in data["COMPACT_CLAIM_UNITS"][0]["units"]
    ]
    assert scope["identity_only"] is True
    assert not any(key in row for key in ("status", "supported", "entailment", "text"))
    assert data == before
    row["actual_citations"][0]["allowed_fragment_ids"].append("foreign")
    assert data == before
    data["CLAIM_CITATION_SCOPE"] = citation_scope(data)
    assert decode(encode(data)) == data
    assert data["SOURCE_FRAGMENTS"] == before["SOURCE_FRAGMENTS"]


def test_both_neutral_prompt_examples_validate_the_unchanged_claim_schema():
    from generation.prompt_builder import PROMPTS
    from generation.reliability_v6 import CompactTextbookClaim

    text = (PROMPTS / "citation_scope_check_v8.txt").read_text(encoding="utf-8")
    examples = [json.loads(line) for line in text.splitlines() if line.startswith("{")]
    assert len(examples) == 2
    positive, negative = [CompactTextbookClaim.model_validate(row) for row in examples]
    assert positive.units[0].unit_id == negative.units[0].unit_id == "U01"
    assert positive.citations[0].fragment_ids == positive.units[0].fragment_ids == ["F001"]
    assert negative.status == negative.units[0].status == "unsupported"
    assert negative.citations == negative.units[0].fragment_ids == []


@pytest.mark.parametrize("fault", ["duplicate", "missing", "foreign_fragment", "markers"])
def test_inconsistent_scope_inputs_fail_instead_of_adding_local_references(fault):
    data, _ = context()
    if fault == "duplicate":
        data["ACTUAL_CITATION_BINDINGS"].append(deepcopy(data["ACTUAL_CITATION_BINDINGS"][0]))
    elif fault == "missing":
        data["ACTUAL_CITATION_BINDINGS"] = []
    elif fault == "foreign_fragment":
        data["SOURCE_FRAGMENTS"][0]["evidence_id"] = "ev_999"
    else:
        data["CLAIMS"][0]["evidence_ids"] = []
    with pytest.raises(ValueError, match="CITATION_SCOPE_"):
        citation_scope(data)


@pytest.mark.parametrize("fault", ["uncited", "other_claim", "unassessed", "negative_relation"])
def test_scope_never_turns_unbound_or_negative_sources_into_supported_units(fault):
    data, verdict = context()
    if fault == "uncited":
        data["ACTUAL_CITATION_BINDINGS"][0]["citations"] = []
        verdict["claims"][0]["citations"] = []
    elif fault == "other_claim":
        extra = {**data["SOURCE_FRAGMENTS"][1], "fragment_id": "F003", "evidence_id": "ev_002"}
        data["SOURCE_FRAGMENTS"].append(extra)
        claim = {**data["CLAIMS"][0], "claim_id": "c2"}
        data["CLAIMS"].append(claim)
        data["ACTUAL_CITATION_BINDINGS"].append(
            {
                "claim_id": "c2",
                "citations": [{"evidence_id": "ev_002", "allowed_fragment_ids": ["F003"]}],
            }
        )
        data = compact_check_context(data)
        second = deepcopy(verdict["claims"][0])
        second["claim_id"] = "c2"
        second["citations"] = [
            {"evidence_id": "ev_002", "fragment_ids": ["F003"], "relation": "supporting"}
        ]
        for unit in second["units"]:
            unit["fragment_ids"] = ["F003"]
        verdict["claims"].append(second)
        verdict["claims"][0]["units"][0]["fragment_ids"] = ["F003"]
    elif fault == "unassessed":
        verdict["claims"][0]["units"][0]["fragment_ids"] = ["F002"]
    else:
        verdict["claims"][0]["citations"][0]["relation"] = "contradictory"
    data["CLAIM_CITATION_SCOPE"] = citation_scope(data)
    before = deepcopy((data, verdict))
    _, contract, defects, _ = expand_compact_judgment(
        verdict, data, answer_mode="textbook", teaching_mode="direct"
    )
    expected = (
        "COMPACT_UNIT_CITATION_CONFLICT"
        if fault == "negative_relation"
        else "COMPACT_UNIT_ASSESSED_FRAGMENT_MISMATCH"
    )
    assert expected in {row["code"] for row in contract + defects}
    assert (data, verdict) == before


@pytest.mark.parametrize("position", ["opening", "closing", "short_answer"])
def test_uncited_opening_closing_and_summary_need_content_repair_and_final_recheck(position):
    cited = "Photosynthesis uses light energy. [ev_001]"
    uncited = "Carbon dioxide supplies carbon for sugar."
    draft = (
        answer(uncited + " " + cited)
        if position == "opening"
        else answer(cited + " " + uncited)
        if position == "closing"
        else answer(cited, short_answer=uncited)
    )

    def negative(messages):
        value = check(messages)
        data = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
        target = next(c for c in data["CLAIMS"] if not c["evidence_ids"])
        claim = next(c for c in value["claims"] if c["claim_id"] == target["claim_id"])
        actual = next(
            c for c in data["CLAIM_CITATION_SCOPE"]["claims"] if c["claim_id"] == target["claim_id"]
        )
        assert actual["actual_citations"] == []
        claim.update(
            basis="textbook",
            status="unsupported",
            citations=[],
            units=[
                {
                    "unit_id": unit["unit_id"],
                    "status": "unsupported",
                    "fragment_ids": [],
                    "relation_preserved": True,
                    "conditions_preserved": True,
                    "reason": "Authored uncited factual defect.",
                }
                for unit in actual["units"]
            ],
        )
        value.update(body_ok=False, complete_answer=False)
        return value

    def patch(messages):
        data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n")[-1])
        target = next(c for c in data["original_claims"] if not c["evidence_ids"])
        kept = next(c for c in data["original_claims"] if c["evidence_ids"])
        assert kept["claim_id"] in {row["claim_id"] for row in data["protected_exact_claims"]}
        return {
            "edits": [{"claim_id": target["claim_id"], "replacement_text": uncited + " [ev_001]"}],
            "append_answer_text": "",
        }

    out, adapter = run([draft, negative, patch, check])
    assert out.succeeded, out.error
    assert out.budget["consumed_calls"] == 4
    assert [row["stage"] for row in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert out.checks[0]["semantic_negative_routing"]["route"] == "semantic_repair"
    assert not out.checks[0]["accepted"] and out.checks[1]["accepted"]
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert cited in out.response["answer_text"]
    assert (
        uncited + " [ev_001]"
        in out.response["short_answer" if position == "short_answer" else "answer_text"]
    )


@pytest.mark.parametrize("field", ["body_ok", "requirements", "request_target", "cumulative_ok"])
def test_missing_independent_gate_cannot_be_inferred_from_the_identity_table(field):
    def missing(messages):
        value = check(messages)
        value.pop(field)
        return value

    out, _ = run([answer(), missing], calls=2)
    assert out.response is None and out.error["code"] == "CHECKER_INCONSISTENT"
    assert out.budget["consumed_calls"] == 2


@pytest.mark.parametrize("negative_gate", [None, "complete_answer", "limitations_explicit"])
def test_honest_partial_completeness_still_requires_actual_positive_gates(negative_gate):
    def limited(messages):
        value = check(messages)
        value.update(
            coverage="supported_partial",
            missing_facets=["requested source condition"],
            limitations_explicit=True,
        )
        value["requirements"][0].update(
            sufficiency="partial",
            response_coverage="partial",
            missing_information="The requested condition is absent from the submitted sources.",
        )
        if negative_gate:
            value[negative_gate] = False
        return value

    out, _ = run([answer(), limited], calls=2)
    if negative_gate:
        assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED"
        assert out.checks[0]["typed_judgment_raw_aliases"][negative_gate] is False
    else:
        assert out.succeeded, out.error
        assert (
            out.checks[0]["typed_judgment_raw_aliases"]["requirements"][0]["sufficiency"]
            == "partial"
        )
        assert out.token_budget["answer_completeness"]["status"] == "partial"


@pytest.mark.parametrize("policy", ["typed_joint_v5", "scoped_compact_v6", "scoped_compact_v7"])
def test_frozen_old_policies_never_receive_v8_appendices_or_scope(policy):
    out, adapter = run(
        [answer(), typed_checker if policy == "typed_joint_v5" else check], policy=policy
    )
    assert out.succeeded, out.error
    assert not any(
        "SCOPED COMPACT V8" in message["content"] or "CLAIM_CITATION_SCOPE" in message["content"]
        for messages, _ in adapter.calls
        for message in messages
    )


def test_v8_scope_and_appendices_reach_the_real_checker_without_changing_schema_or_budget():
    out, adapter = run([answer(), check], checker_payload_policy="lossless_checker_tables_v1")
    assert out.succeeded, out.error
    assert out.budget["max_calls"] == 4 and out.budget["max_active_seconds"] == 180
    assert out.checks[0]["joint_checker_policy"] == VERSION
    assert adapter.calls[1][1]["response_schema_name"] == "joint_check_v6"
    assert "SCOPED COMPACT V8" in adapter.calls[0][0][0]["content"]
    messages = adapter.calls[1][0]
    assert "SCOPED COMPACT V8" in messages[0]["content"]
    data = next(json.loads(m["content"]) for m in messages if m["content"].startswith("{"))
    if "CHECKER_INPUT_ENCODING" in data:
        data = decode(data)
    assert data["CLAIM_CITATION_SCOPE"] == citation_scope(data)
    assert data["SOURCE_FRAGMENTS"] and data["CONTEXT_COVERAGE"]
    assert out.token_budget["compact_joint_support"]["human_rating"] is None
