"""Generic authored semantic controls; scripted verdicts are not model quality evidence."""

from copy import deepcopy
from dataclasses import replace

import pytest

from generation import GenerationService, ModelConfig, RequestBudget
from generation.adapters import chat_value
from generation.source_relations_v2 import VERSION
from generation.teaching_plan_v6 import freeze_generation_policy
from retrieval.source_spans import text_hash
from test_answer_core_v5 import req
from test_enhancement_generation import Script
from test_source_relation_contract import check_input
from test_source_relation_units_v2 import (
    assert_assessed_sources_are_canonical,
    unit_checker,
)


CASES = [
    pytest.param(
        "Each batch forms six widgets. Five widgets return to the input pool. "
        "One widget is exported.",
        "Each batch forms six widgets and exports a net six widgets [ev_001].",
        "exports a net",
        "Gross production is six; the selected source exports only one per batch.",
        id="gross_as_net",
    ),
    pytest.param(
        "One operation accepts one parcel. A batch contains six operations. "
        "Each batch exports one crate.",
        "One operation accepts one parcel and exports one crate [ev_001].",
        "exports one",
        "The selected export count belongs to one batch, not one operation.",
        id="batch_as_operation",
    ),
    pytest.param(
        "Each operation produces two packets. Three packets form one shipment.",
        "Each operation produces two packets and therefore produces two shipments [ev_001].",
        "therefore",
        "A packet count does not establish the asserted downstream shipment count.",
        id="precursor_as_downstream",
    ),
    pytest.param(
        "One batch exports one packet. Six batches supply the packets for one shipment.",
        "One packet leaves for a shipment, and this requires six batches [ev_001].",
        "this requires",
        "The referent mixes the exported packet count with the downstream shipment batch.",
        id="ambiguous_quantity_referent",
    ),
]

IDENTITY_SOURCE = "The operation releases two fragments. These fragments are called sprockets."
IDENTITY_CLAIM = "The operation releases two sprockets [ev_001]."


def _request(source, question="Explain the process and its output roles."):
    value = req(
        question=question,
        source_relation_policy=VERSION,
        generation_policy=freeze_generation_policy(),
        config=ModelConfig(provider="mock", window_tokens=32768, tokenizer_provider="estimate"),
    )
    evidence = deepcopy(value.evidence)
    evidence[0].update(text=source, text_hash=text_hash(source), section="Authored process")
    mapping = deepcopy(value.source_map)
    mapping["c1"].update(chunk_text=source, chunk_hash=text_hash(source))
    mapping["c1"]["units"][0].update(cleaned_text=source, text_hash=text_hash(source))
    mapping["c1"]["spans"][0].update(end=len(source), chunk_end=len(source))
    return replace(value, evidence=evidence, source_map=mapping)


def _verdict(
    *,
    negative_text=None,
    status="partial",
    reason="Authored missing predicate.",
    unit_category_only=False,
    claim_identity=True,
):
    def authored(messages):
        data = check_input(messages)
        value = unit_checker(messages)
        fragments = {row["fragment_id"]: row for row in data["SOURCE_FRAGMENTS"]}
        binding = {row["claim_id"]: row for row in data["ACTUAL_CITATION_BINDINGS"]}
        unit_text = {
            row["claim_id"]: {unit["unit_id"]: unit["text"] for unit in row["units"]}
            for row in data["SOURCE_SYNTACTIC_UNITS"]
        }
        # Aggregates deliberately remain optimistic: the unit judgment is the
        # independent rejection signal exercised by these controls.
        assert value["body_ok"] is True and value["complete_answer"] is True
        changed = 0
        for row in value["claims"]:
            if row["basis"] != "textbook":
                continue
            assert row["status"] == "supported"
            allowed = binding[row["claim_id"]]["citations"][0]["allowed_fragment_ids"]
            category = [
                fid
                for fid in allowed
                if fragments[fid]["exact_text"] == "The operation releases two fragments."
            ]
            claim_ids = allowed if claim_identity else category
            row["citations"][0]["fragment_ids"] = list(claim_ids)
            for unit in row["units"]:
                unit["fragment_ids"] = list(category if unit_category_only else allowed)
                if (
                    negative_text is not None
                    and negative_text in unit_text[row["claim_id"]][unit["unit_id"]]
                ):
                    unit.update(status=status, relation_preserved=False, reason=reason)
                    changed += 1
        if negative_text is not None:
            assert changed == 1
        return value

    return authored


def _run(source, claim, verdict, *, short_answer=None, calls=2, later=None):
    request = _request(source)
    before = deepcopy((request.question, request.evidence, request.source_map))
    proposed = chat_value("answer", claim, citations=["ev_001"], short_answer=short_answer)
    script = Script([proposed, verdict] + (later or []))
    outcome = GenerationService(adapter=script, checker_adapter=script).generate(
        request, RequestBudget(max_calls=calls, max_active_seconds=180)
    )
    assert (request.question, request.evidence, request.source_map) == before
    return outcome, script, request


def _assert_negative(outcome, request, reason, *, check_index=0):
    assert outcome.response is None and not outcome.delivered_projection
    assert outcome.error["code"] == "SEMANTIC_CHECK_FAILED"
    check = outcome.checks[check_index]
    assert check["checker_inconsistencies"] == []
    assert check["accepted"] is False
    raw = check["typed_judgment_raw_aliases"]
    assert raw["body_ok"] is True and raw["complete_answer"] is True
    assert all(row.get("status") == "supported" for row in raw["claims"])
    negatives = [
        unit for row in raw["claims"] for unit in row["units"] if unit["status"] != "supported"
    ]
    assert len(negatives) == 1 and negatives[0]["reason"] == reason
    assert negatives[0]["relation_preserved"] is False
    assessment = check["source_relation_assessment"]
    assert assessment["accepted"] is False
    assert assessment["source_entailment_locally_certified"] is False
    assert_assessed_sources_are_canonical(outcome, request, check_index)


@pytest.mark.parametrize("source,claim,target,reason", CASES)
@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_quantity_unit_negative_outweighs_optimistic_aggregates(
    source, claim, target, reason, status
):
    outcome, script, request = _run(
        source, claim, _verdict(negative_text=target, status=status, reason=reason)
    )
    _assert_negative(outcome, request, reason)
    assert [row["stage"] for row in outcome.attempts] == ["generation", "joint_check"]
    assert len(script.calls) == outcome.budget["consumed_calls"] == 2


@pytest.mark.parametrize("claim_identity", [False, True])
def test_unselected_identity_cannot_be_filled_from_available_or_claim_level_fragment(
    claim_identity,
):
    reason = "This unit selects only the generic category; its product identity is not established."
    outcome, _, request = _run(
        IDENTITY_SOURCE,
        IDENTITY_CLAIM,
        _verdict(
            negative_text="sprockets",
            reason=reason,
            unit_category_only=True,
            claim_identity=claim_identity,
        ),
    )
    _assert_negative(outcome, request, reason)
    check = outcome.checks[0]
    raw = check["typed_judgment_raw_aliases"]["claims"][0]
    category_id = raw["units"][0]["fragment_ids"][0]
    assert len(raw["units"][0]["fragment_ids"]) == 1
    assert len(raw["citations"][0]["fragment_ids"]) == (2 if claim_identity else 1)
    unit = check["source_relation_assessment_raw_aliases"]["claims"][0]["obligations"][0]
    assert unit["fragment_ids"] == [category_id]
    assert [row["quote"] for row in unit["source_quotes"]] == [
        "The operation releases two fragments."
    ]


@pytest.mark.parametrize(
    "source,claim",
    [
        (IDENTITY_SOURCE, IDENTITY_CLAIM),
        (
            "Each batch forms six widgets. Five widgets return to the input pool. One widget is exported.",
            "Each batch forms six widgets, of which one widget is exported and five return to the input pool [ev_001].",
        ),
    ],
)
def test_authored_complete_identity_or_accounting_bindings_keep_full_semantic_path(source, claim):
    outcome, script, request = _run(source, claim, _verdict())
    assert outcome.succeeded, outcome.error
    assert outcome.response["answer_text"] == claim
    assert_assessed_sources_are_canonical(outcome, request)
    assert len(script.calls) == outcome.budget["consumed_calls"] == 2
    assert script.calls[1][1]["response_schema_name"] == "joint_check_source_relations_v2"


def test_generation_and_final_recheck_receive_generic_rules_without_expanding_budget():
    source = "Each batch forms six widgets. Five widgets return to the input pool. One widget is exported."
    bad = "Each batch exports a net six widgets [ev_001]."
    corrected = (
        "Each batch exports one widget while five widgets return to the input pool [ev_001]."
    )
    reason = "Gross production is six; the selected source exports only one per batch."
    outcome, script, request = _run(
        source,
        bad,
        _verdict(negative_text="net six", reason=reason),
        calls=4,
        later=[chat_value("answer", corrected, citations=["ev_001"]), _verdict()],
    )
    assert outcome.succeeded, outcome.error
    assert outcome.response["answer_text"] == corrected
    assert [row["stage"] for row in outcome.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert len(script.calls) == outcome.budget["consumed_calls"] == outcome.budget["max_calls"] == 4
    for index in (0, 2):
        system = script.calls[index][0][0]["content"]
        assert "QUANTITY AND REFERENT SCOPE" in system
        assert (
            "gross production, net output, retained material and downstream product formation"
            in system
        )
        assert "omit unneeded numerical detail" in system
    for index in (1, 3):
        system = script.calls[index][0][0]["content"]
        assert "Named-quantity proof audit" in system
        assert "rather than merely listing fragment IDs" in system
        assert "claim/unit remains unselected proof here" in system
        assert "literal token overlap alone never establishes or disproves support" in system
        assert script.calls[index][1]["response_schema_name"] == "joint_check_source_relations_v2"
    assert script.calls[1][1]["response_schema"] == script.calls[3][1]["response_schema"]
    assert_assessed_sources_are_canonical(outcome, request, 0)
    assert_assessed_sources_are_canonical(outcome, request, 1)
    assert outcome.checks[0]["accepted"] is False
    assert outcome.checks[1]["accepted"] is True


def test_persistent_negative_after_bounded_repair_stays_unpublished():
    source = "The operation releases two fragments. These fragments are called sprockets."
    reason = "This unit selects only the generic category; its product identity is not established."
    negative = _verdict(negative_text="sprockets", reason=reason, unit_category_only=True)
    outcome, script, request = _run(
        source,
        IDENTITY_CLAIM,
        negative,
        calls=4,
        later=[chat_value("answer", IDENTITY_CLAIM, citations=["ev_001"]), negative],
    )
    _assert_negative(outcome, request, reason, check_index=0)
    _assert_negative(outcome, request, reason, check_index=1)
    assert [row["stage"] for row in outcome.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert len(script.calls) == outcome.budget["consumed_calls"] == 4


def test_named_identity_gap_in_short_answer_is_not_filled_from_body_selection():
    reason = "This short-answer unit selects the category without its selected naming relation."

    def authored(messages):
        data = check_input(messages)
        value = _verdict()(messages)
        field = {row["claim_id"]: row["answer_field"] for row in data["CLAIMS"]}
        category = next(
            row["fragment_id"]
            for row in data["SOURCE_FRAGMENTS"]
            if row["exact_text"] == "The operation releases two fragments."
        )
        changed = 0
        for row in value["claims"]:
            if field[row["claim_id"]] != "short_answer":
                continue
            for unit in row["units"]:
                unit.update(
                    status="partial",
                    fragment_ids=[category],
                    relation_preserved=False,
                    reason=reason,
                )
                changed += 1
        assert changed == 1
        return value

    outcome, _, request = _run(
        IDENTITY_SOURCE, IDENTITY_CLAIM, authored, short_answer=IDENTITY_CLAIM
    )
    _assert_negative(outcome, request, reason)
