"""Authored development regressions for candidate navigation, not semantic Gold.

The source and checker judgments below deliberately exercise local contracts.
They do not measure a model, independent source entailment, or unseen quality.
"""

from copy import deepcopy
import json

import pytest

from generation import GenerationService, ModelConfig, RequestBudget
from generation import checked
from generation import source_evidence_combinations_v1 as combination_module
from generation.claim_feedback_transport_v1 import HEADER, decode_claim_feedback
from generation.local_repair import VERSION as REPAIR
from generation.repair_context import CONTEXT_PREFIX, restore_source_text
from generation.source_evidence_combinations_v1 import (
    MAX_NEW_FRAGMENTS,
    MAX_NEW_PER_UNIT,
    MAX_NEW_SOURCE_CHARS,
    MAX_OUTPUT_BYTES,
    MAX_PROPOSALS,
    VERSION,
    plan_source_combinations,
)
from generation.source_relations_v2 import (
    VERSION as RELATIONS,
    assess_source_relations,
    syntactic_units,
)
from retrieval.source_spans import map_fragments, text_hash
from test_answer_core_v5 import req
from test_enhancement_generation import Script, answer
from test_source_relation_contract import check_input
from test_source_relation_units_v2 import (
    assert_assessed_sources_are_canonical,
    unit_checker,
)


CASES = [
    pytest.param(
        {
            "name": "neutralisation-products",
            "question": "Which products form when hydrochloric acid reacts with sodium hydroxide?",
            "baseline": "Sodium chloride is a salt.",
            "claim": "Neutralisation of hydrochloric acid by sodium hydroxide forms sodium chloride and water. [ev_001]",
            "repair": "Hydrochloric acid reacts with sodium hydroxide to form sodium chloride and water. [ev_001]",
            "sources": [
                "Hydrochloric acid reacts with sodium hydroxide to form sodium chloride and water.",
                "A neutralisation reaction produces a salt and water from an acid and a base.",
            ],
        },
        id="neutralisation-products",
    ),
    pytest.param(
        {
            "name": "dns-purpose",
            "question": "What does DNS resolve and does it encrypt traffic?",
            "baseline": "DNS is a name service.",
            "claim": "DNS resolves a host name to an IP address and does not encrypt web traffic. [ev_001]",
            "repair": "DNS resolves a host name to an IP address. [ev_001] DNS does not encrypt web traffic. [ev_001]",
            "sources": [
                "DNS resolves a host name to an IP address.",
                "DNS does not encrypt web traffic.",
            ],
        },
        id="dns-purpose",
    ),
    pytest.param(
        {
            "name": "mechanics-condition",
            "question": "For constant mass, what happens to velocity and acceleration when net force is zero?",
            "baseline": "Net force is the vector sum of forces.",
            "claim": "With constant mass, zero net force means constant velocity and zero acceleration. [ev_001]",
            "repair": "For constant mass, zero net force gives zero acceleration. [ev_001] Velocity remains constant when acceleration is zero. [ev_001]",
            "sources": [
                "For constant mass, zero net force gives zero acceleration.",
                "Velocity remains constant when acceleration is zero.",
            ],
        },
        id="mechanics-condition",
    ),
    pytest.param(
        {
            "name": "shared-predicate-metals",
            "question": "Do copper and aluminium conduct electric current?",
            "baseline": "Copper is a metal.",
            "claim": "Copper and aluminium conduct electric current. [ev_001]",
            "repair": "Copper conducts electric current. [ev_001] Aluminium conducts electric current. [ev_001]",
            "sources": [
                "Copper conducts electric current.",
                "Aluminium conducts electric current.",
            ],
        },
        id="shared-predicate-metals",
    ),
]


def source_fixture(text, number=1, *, complete=True, evidence_id="ev_001", **updates):
    """Stable exact-text identities for direct planner fixtures, without IO."""
    source = {
        "fragment_id": "span_" + text_hash(f"proof60:{number}:{text}")[:32],
        "evidence_id": evidence_id,
        "document_version_id": "authored-proof60-v1",
        "processing_id": "authored-proof60-processing",
        "chunk_id": "authored-proof60-chunk",
        "source_unit_id": "authored-proof60-unit",
        "start": number * 10000,
        "end": number * 10000 + len(text),
        "chunk_start": number * 10000,
        "chunk_end": number * 10000 + len(text),
        "page": 1,
        "exact_text": text,
        "text_hash": text_hash(text),
        "complete_block": complete,
        "block_kind": "prose",
        "mapping_quality": "sentence",
        "offset_basis": "cleaned_source_unit_unicode",
    }
    source.update(updates)
    return source


def planner_fixture(case, *, status="partial"):
    fragments = [
        source_fixture(text, number)
        for number, text in enumerate([case["baseline"], *case["sources"]], 1)
    ]
    claims = [{"claim_id": "c1", "text": case["claim"], "evidence_ids": ["ev_001"]}]
    selected = [fragments[0]["fragment_id"]]
    bindings = [
        {
            "claim_id": "c1",
            "citations": [
                {
                    "evidence_id": "ev_001",
                    "allowed_fragment_ids": [row["fragment_id"] for row in fragments],
                }
            ],
        }
    ]
    typed = {
        "claims": [
            {
                "claim_id": "c1",
                "basis": "textbook",
                "status": "supported",
                "citations": [
                    {
                        "evidence_id": "ev_001",
                        "fragment_ids": selected,
                        "relation": "supporting",
                    }
                ],
                "units": [
                    {
                        "unit_id": unit["unit_id"],
                        "status": status,
                        "fragment_ids": selected,
                        "relation_preserved": True,
                        "conditions_preserved": True,
                        "reason": "Authored unresolved source selection; preserve this judgment exactly.",
                    }
                    for unit in syntactic_units(claims)[0]["units"]
                ],
            }
        ]
    }
    contract, _, assessment = assess_source_relations(typed, claims, bindings, fragments)
    assert contract == []
    return claims, bindings, fragments, assessment


def assert_navigation_only(plan):
    assert plan["version"] == VERSION
    assert plan["candidate_only"]
    assert not plan["source_entailment_certified"]
    assert not plan["publication_override"]
    for proposal in plan["proposals"]:
        assert proposal["candidate_only"]
        assert not proposal["source_entailment_certified"]
        assert not proposal["publication_override"]
        assert not proposal["diagnostic"]["semantic_absence_certified"]
        assert not proposal["diagnostic"]["predicate_ownership_certified"]
        assert proposal["diagnostic"]["syntactic_partition_only"]
        assert not proposal["diagnostic"]["same_source_order_is_semantic_continuation"]


@pytest.mark.parametrize("case", CASES)
def test_different_concepts_surface_only_complete_allowed_candidates_and_leave_negative_units(case):
    values = planner_fixture(case)
    original = deepcopy(values)
    plan = plan_source_combinations(*values)
    assert_navigation_only(plan)
    assert values == original
    assert plan["candidate_fragment_ids"]
    sources = {row["fragment_id"]: row for row in values[2]}
    allowed = set(values[1][0]["citations"][0]["allowed_fragment_ids"])
    assert set(plan["candidate_fragment_ids"]) <= allowed
    for proposal in plan["proposals"]:
        assert proposal["checker_status"] == "partial"
        assert proposal["claim_context_ref"] == "original_claims:c1"
        assert proposal["full_claim_hash"] == text_hash(case["claim"])
        assert proposal["full_claim_chars"] == len(case["claim"])
        assert "full_claim" not in proposal
        unit = proposal["unit_context"]
        assert "text" not in unit
        assert text_hash(case["claim"][unit["start"] : unit["end"]]) == unit["text_hash"]
        assert proposal["diagnostic"]["scoped_candidate_state"] == "allowed_unselected_candidates"
        for reference in proposal["source_refs"]:
            source = sources[reference["fragment_id"]]
            assert source["complete_block"]
            assert reference["text_hash"] == text_hash(source["exact_text"])
            assert reference["evidence_id"] == source["evidence_id"]
    assert not values[3]["accepted"]


@pytest.mark.parametrize("case", CASES)
def test_supported_control_has_no_candidate_patch_and_no_new_sources(case, monkeypatch):
    values = planner_fixture(case, status="supported")

    def forbidden_lookup(*args, **kwargs):
        raise AssertionError("Supported controls must not build the scoped source lookup.")

    monkeypatch.setattr(combination_module, "scoped_syntactic_units", forbidden_lookup)
    plan = plan_source_combinations(*values)
    assert_navigation_only(plan)
    assert plan["proposals"] == []
    assert plan["candidate_fragment_ids"] == []
    assert values[3]["accepted"]


def test_sources_outside_same_claim_scope_do_not_become_repair_candidates():
    case = CASES[1].values[0]
    values = planner_fixture(case)
    selected = values[2][0]["fragment_id"]
    values[1][0]["citations"][0]["allowed_fragment_ids"] = [selected]
    foreign = source_fixture(case["claim"], 90, evidence_id="ev_999")
    values[2].append(foreign)
    plan = plan_source_combinations(*values)
    assert_navigation_only(plan)
    assert plan["candidate_fragment_ids"] == []
    assert {row["diagnostic"]["scoped_candidate_state"] for row in plan["proposals"]} == {
        "selection_still_insufficient"
    }
    assert all(
        row["fragment_id"] == selected
        for proposal in plan["proposals"]
        for row in proposal["source_refs"]
    )


def test_empty_precise_source_bank_does_not_certify_that_knowledge_is_absent():
    values = planner_fixture(CASES[2].values[0])
    for source in values[2]:
        source["complete_block"] = False
    for obligation in values[3]["claims"][0]["obligations"]:
        obligation.update(status="unsupported", fragment_ids=[], source_quotes=[])
    plan = plan_source_combinations(*values)
    assert_navigation_only(plan)
    assert plan["candidate_fragment_ids"] == []
    assert plan["proposals"]
    assert {row["diagnostic"]["scoped_candidate_state"] for row in plan["proposals"]} == {
        "empty_scoped_candidate_bank"
    }


@pytest.mark.parametrize(
    "quality", ["coarse_partial_block", "conservative_whole_block", "conservative_sentence_block"]
)
def test_coarse_or_incomplete_unselected_blocks_are_excluded_without_truncation(quality):
    values = planner_fixture(CASES[0].values[0])
    for source in values[2][1:]:
        source["mapping_quality"] = quality
    before = deepcopy(values)
    plan = plan_source_combinations(*values)
    assert plan["candidate_fragment_ids"] == []
    assert values == before
    assert_navigation_only(plan)


def test_shared_subject_partition_carries_the_full_predicate_without_certifying_ownership():
    values = planner_fixture(CASES[3].values[0])
    plan = plan_source_combinations(*values)
    first = next(row for row in plan["proposals"] if row["unit_id"] == "U01")
    start, end = first["unit_context"]["start"], first["unit_context"]["end"]
    assert values[0][0]["text"][start:end] == "Copper"
    assert first["claim_context_ref"] == "original_claims:c1"
    assert first["full_claim_hash"] == text_hash(values[0][0]["text"])
    assert not first["diagnostic"]["predicate_ownership_certified"]
    assert not values[3]["accepted"]


def test_keyword_matching_worksheet_question_stays_candidate_only_and_never_changes_partial():
    case = {
        "baseline": "Copper is a metal.",
        "claim": "Copper conducts electric current. [ev_001]",
        "sources": ["The worksheet asks whether copper conducts electric current."],
    }
    values = planner_fixture(case)
    before = deepcopy(values)
    plan = plan_source_combinations(*values)
    # This is intentionally an insufficient semantic witness despite term overlap.
    assert plan["candidate_fragment_ids"] == [values[2][1]["fragment_id"]]
    assert_navigation_only(plan)
    assert values == before and not values[3]["accepted"]
    assert all(row["checker_status"] == "partial" for row in plan["proposals"])


def test_combination_limits_are_finite_and_never_clip_a_whole_source_block():
    values = planner_fixture(CASES[1].values[0])
    large = source_fixture("DNS resolves a host name to an IP address. " + "authored " * 900, 91)
    values[2].append(large)
    values[1][0]["citations"][0]["allowed_fragment_ids"].append(large["fragment_id"])
    plan = plan_source_combinations(*values)
    assert_navigation_only(plan)
    selected = {row["fragment_id"]: row for row in values[2]}
    assert len(set(plan["candidate_fragment_ids"])) == len(plan["candidate_fragment_ids"])
    assert len(plan["candidate_fragment_ids"]) <= MAX_NEW_FRAGMENTS
    assert len(plan["proposals"]) <= MAX_PROPOSALS
    assert_plan_fits_both_serializers(plan)
    assert all(len(row["supplement_fragment_ids"]) <= MAX_NEW_PER_UNIT for row in plan["proposals"])
    assert (
        sum(len(selected[fid]["exact_text"]) for fid in plan["candidate_fragment_ids"])
        <= MAX_NEW_SOURCE_CHARS
    )
    assert large["fragment_id"] not in plan["candidate_fragment_ids"]
    assert len(large["exact_text"]) > MAX_NEW_SOURCE_CHARS


def assert_plan_fits_both_serializers(plan):
    """Ordinary repair uses spaced JSON; the V10 serializer can use compact JSON."""
    spaced = json.dumps(plan, ensure_ascii=False, sort_keys=True).encode("utf-8")
    compact = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    assert len(compact) <= len(spaced) <= MAX_OUTPUT_BYTES


def test_metadata_limit_removes_whole_trailing_proposals_and_recounts_sources(monkeypatch):
    case = {
        "baseline": "Copper is a metal.",
        "claim": (
            "Copper conducts electric current; aluminium conducts electric current; "
            "silver conducts electric current; gold conducts electric current; "
            "iron conducts electric current; zinc conducts electric current. [ev_001]"
        ),
        "sources": ["Copper, aluminium, silver, gold, iron and zinc conduct electric current."],
    }
    values = planner_fixture(case)
    # Long legal source-location metadata stresses wire bytes, not source content.
    for source in values[2]:
        for key in ("document_version_id", "processing_id", "chunk_id", "source_unit_id"):
            source[key] = key + ":" + "x" * 800
    before = deepcopy(values)
    bounded = plan_source_combinations(*values)
    assert_navigation_only(bounded)
    assert_plan_fits_both_serializers(bounded)
    total_units = len(values[3]["claims"][0]["obligations"])
    assert total_units == 6
    assert 0 < len(bounded["proposals"]) < total_units
    assert bounded["limits"]["metadata_capacity_blocked"]
    assert bounded["limits"]["omitted_proposal_count"] == total_units - len(bounded["proposals"])
    assert not bounded["limits"].get("proposal_count_blocked", False)

    with monkeypatch.context() as context:
        context.setattr(combination_module, "MAX_OUTPUT_BYTES", 256 * 1024)
        unbounded = plan_source_combinations(*values)
    assert len(unbounded["proposals"]) == total_units
    assert (
        len(json.dumps(unbounded, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        > MAX_OUTPUT_BYTES
    )
    assert bounded["proposals"] == unbounded["proposals"][: len(bounded["proposals"])]
    assert values == before

    retained = list(
        dict.fromkeys(
            fid for proposal in bounded["proposals"] for fid in proposal["supplement_fragment_ids"]
        )
    )
    sources = {row["fragment_id"]: row for row in values[2]}
    assert retained == bounded["candidate_fragment_ids"]
    assert bounded["limits"]["new_fragment_count"] == len(retained)
    assert bounded["limits"]["new_source_chars"] == sum(
        len(sources[fid]["exact_text"]) for fid in retained
    )
    for proposal in bounded["proposals"]:
        for reference in proposal["source_refs"]:
            source = sources[reference["fragment_id"]]
            assert reference["text_hash"] == text_hash(source["exact_text"])
            for key in ("document_version_id", "processing_id", "chunk_id", "source_unit_id"):
                assert reference[key] == source[key]
    assert values[2][1]["exact_text"] == case["sources"][0]


@pytest.mark.parametrize("defect", ["missing", "duplicate", "foreign"])
def test_supported_verdict_cannot_skip_validation_of_malformed_unit_identity(defect, monkeypatch):
    values = planner_fixture(CASES[1].values[0], status="supported")
    units = values[3]["claims"][0]["obligations"]
    if defect == "missing":
        units.pop()
    elif defect == "duplicate":
        units.append(deepcopy(units[0]))
    else:
        units[0]["unit_id"] = "U999"

    def forbidden_lookup(*args, **kwargs):
        raise AssertionError("Malformed supported identities must fail before scoped lookup.")

    monkeypatch.setattr(combination_module, "scoped_syntactic_units", forbidden_lookup)
    plan = plan_source_combinations(*values)
    assert plan["blocked_reason"] == "invalid_source_composition_input"
    assert plan["proposals"] == plan["candidate_fragment_ids"] == []
    assert_navigation_only(plan)


@pytest.mark.parametrize(
    "invalid", ["contract", "duplicate_source", "duplicate_unit", "foreign_selected", "source_hash"]
)
def test_invalid_relation_or_identity_input_is_blocked_before_planning(invalid):
    values = planner_fixture(CASES[1].values[0])
    if invalid == "contract":
        values[3]["contract_issue_codes"] = ["RELATION_ASSESSED_FRAGMENT_MISMATCH"]
    elif invalid == "duplicate_source":
        values[2].append(deepcopy(values[2][0]))
    elif invalid == "duplicate_unit":
        values[3]["claims"][0]["obligations"].append(
            deepcopy(values[3]["claims"][0]["obligations"][0])
        )
    elif invalid == "source_hash":
        values[2][0]["text_hash"] = "0" * 64
    else:
        values[3]["claims"][0]["obligations"][0]["fragment_ids"] = ["span_foreign"]
    plan = plan_source_combinations(*values)
    assert plan["blocked_reason"]
    assert plan["proposals"] == plan["candidate_fragment_ids"] == []
    assert_navigation_only(plan)


def request_for(case):
    text = "\n\n".join([case["baseline"], *case["sources"]])
    evidence = {
        "evidence_id": "ev_001",
        "chunk_id": "c1",
        "asset_id": "d1",
        "processing_id": "p1",
        "source_title": "Authored cross-concept development fixture",
        "section": case["name"],
        "pages": [1],
        "locator": "Authored fixture page 1",
        "text": text,
        "text_hash": text_hash(text),
        "context_order": 1,
    }
    mapping = {
        "document_version_id": "v1",
        "processing_id": "p1",
        "asset_id": "d1",
        "chunk_text": text,
        "chunk_hash": text_hash(text),
        "units": [{"id": "u1", "page": 1, "cleaned_text": text, "text_hash": text_hash(text)}],
        "spans": [
            {
                "unit_id": "u1",
                "page": 1,
                "start": 0,
                "end": len(text),
                "chunk_start": 0,
                "chunk_end": len(text),
            }
        ],
    }
    return req(
        config=ModelConfig(window_tokens=32768, tokenizer_provider="estimate"),
        question=case["question"],
        evidence=[evidence],
        source_map={"c1": mapping},
        source_relation_policy=RELATIONS,
        repair_policy=REPAIR,
    )


def capture_codec(monkeypatch):
    """Observe the existing encoder's exact inputs without changing its result."""
    inputs = {}
    original = checked.encode_claim_feedback

    def observe(feedback, **kwargs):
        inputs.clear()
        inputs.update(deepcopy(kwargs))
        return original(feedback, **kwargs)

    monkeypatch.setattr(checked, "encode_claim_feedback", observe)
    return inputs


def repair_data(messages, codec_inputs):
    payload = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    context = next(
        json.loads(row["content"][len(CONTEXT_PREFIX) :])
        for row in messages
        if row["content"].startswith(CONTEXT_PREFIX)
    )
    # The trusted scripted producer creates this wrapper; this is not application marker detection.
    if HEADER in payload:
        payload = decode_claim_feedback(
            payload,
            encoded=True,
            **codec_inputs,
        )
    if "source_ref_version" in payload:
        payload = restore_source_text(payload, messages, context["CURRENT_EVIDENCE"])
    return payload


def negative_check(messages):
    value = unit_checker(messages)
    for row in value["claims"][1:]:
        for unit in row["units"]:
            unit.update(
                status="partial", reason="Authored selection gap, not an online quality label."
            )
    return value


def final_combined_check(messages, *, negative=False):
    data = check_input(messages)
    value = unit_checker(messages)
    fragments = data["SOURCE_FRAGMENTS"]
    complete_ids = [row["fragment_id"] for row in fragments[1:] if row["complete_block"]]
    assert complete_ids
    for row in value["claims"][1:]:
        row["citations"][0]["fragment_ids"] = complete_ids
        for unit in row["units"]:
            unit["fragment_ids"] = complete_ids
    if negative:
        value["claims"][-1]["units"][-1].update(
            status="partial", reason="Authored final partial remains a publication blocker."
        )
    return value


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize(
    "negative", [False, True], ids=["complete-final-check", "final-partial-blocked"]
)
def test_real_generation_service_uses_one_local_patch_and_one_complete_final_check(
    case, negative, monkeypatch
):
    request = request_for(case)
    baseline = case["baseline"] + " [ev_001]"
    original = answer(baseline + " " + case["claim"])
    seen = {}
    codec_inputs = capture_codec(monkeypatch)

    def patch(messages):
        data = repair_data(messages, codec_inputs)
        plan = data["source_evidence_combinations"]
        assert_navigation_only(plan)
        assert plan["candidate_fragment_ids"]
        assert len(data["protected_exact_claims"]) == 1
        assert data["protected_exact_claims"][0]["text"] == baseline
        assert len(data["editable_claim_ids"]) == 1
        canonical = {
            row["fragment_id"]: row
            for row in map_fragments(request.evidence, request.source_map)[0]
        }
        candidates = {row["fragment_id"]: row for row in data["source_repair_candidates"]}
        for fid in plan["candidate_fragment_ids"]:
            assert fid.startswith("span_") and fid in candidates and fid in canonical
            assert candidates[fid]["exact_text"] == canonical[fid]["exact_text"]
        seen["plan"] = deepcopy(plan)
        return {
            "edits": [
                {"claim_id": data["editable_claim_ids"][0], "replacement_text": case["repair"]}
            ],
            "append_answer_text": "",
        }

    transport = Script(
        [original, negative_check, patch, lambda m: final_combined_check(m, negative=negative)]
    )
    output = GenerationService(transport).generate(request, RequestBudget(max_calls=4))
    assert len(transport.calls) == output.budget["consumed_calls"] == 4
    assert [row["stage"] for row in output.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert transport.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert [row["revision"] for row in output.checks] == [0, 1]
    assert not output.checks[0]["source_relation_assessment"]["accepted"]
    assert seen["plan"]["candidate_fragment_ids"]
    assert_assessed_sources_are_canonical(output, request, 0)
    assert_assessed_sources_are_canonical(output, request, 1)
    if negative:
        assert output.response is None and output.error["code"] == "SEMANTIC_CHECK_FAILED"
        assert output.delivered_projection == {}
        assert output.checks[-1]["publication_block"]["stop_reason"] == "final_recheck_rejected"
        assert not output.checks[-1]["source_relation_assessment"]["accepted"]
    else:
        assert output.succeeded, output.error
        assert output.response["answer_text"].startswith(baseline)
        assert output.checks[-1]["source_relation_assessment"]["accepted"]


@pytest.mark.parametrize("case", CASES)
def test_normal_supported_generation_does_not_invoke_combination_or_patch(case):
    transport = Script([answer(case["baseline"] + " [ev_001]"), unit_checker])
    output = GenerationService(transport).generate(request_for(case), RequestBudget(max_calls=4))
    assert output.succeeded, output.error
    assert len(transport.calls) == output.budget["consumed_calls"] == 2
    assert [row["stage"] for row in output.attempts] == ["generation", "joint_check"]


@pytest.mark.parametrize("calls", [2, 3])
def test_insufficient_budget_never_performs_an_unchecked_local_patch(calls):
    case = CASES[1].values[0]
    transport = Script([answer(case["baseline"] + " [ev_001] " + case["claim"]), negative_check])
    output = GenerationService(transport).generate(
        request_for(case), RequestBudget(max_calls=calls)
    )
    assert output.response is None and output.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert len(transport.calls) == output.budget["consumed_calls"] == 2
    block = output.checks[-1]["publication_block"]
    assert block["stop_reason"] == "insufficient_calls_for_repair_and_recheck"
    assert block["required_calls_for_repair_and_recheck"] == 2
