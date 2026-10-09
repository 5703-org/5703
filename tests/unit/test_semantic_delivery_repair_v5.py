"""Authored native routing controls, not measurements of model semantic accuracy."""

import json
from copy import deepcopy

import pytest

from generation import GenerationService, RequestBudget
from test_answer_core_v5 import checker
from test_enhancement_generation import Script
from test_example_source_entailment_v5 import (
    COMPOUND,
    PARAPHRASE,
    OUTSIDE,
    SOURCE,
    checker_data,
    draft,
    judgment,
    source_request,
)


def _data(messages):
    original = next(row for row in messages if row["content"].startswith("{"))
    return checker_data([original])


def _negative(*, status="partial", aggregate=True, snapshots=None, mutate=None):
    def authored(messages):
        value = checker(messages)
        first = value["claims"][0]
        first.update(
            basis="textbook",
            status=status,
            citations=first.get("citations", []),
            reason="Authored fixture: the core is supported but the added assertion is not.",
        )
        value.update(
            body_ok=False,
            complete_answer=True,
            coverage="supported_partial" if aggregate else "full",
            missing_facets=["Source support for an optional added assertion."] if aggregate else [],
            limitations_explicit=not aggregate,
            reason="Authored negative contract fixture; not independent semantic evidence.",
        )
        if mutate:
            mutate(value, _data(messages))
        if snapshots is not None:
            snapshots.append(deepcopy(value))
        return value

    return authored


def _run(sequence, *, value=None, calls=4):
    request = value or source_request()
    original = deepcopy((request.question, request.evidence, request.source_map))
    script = Script(sequence)
    outcome = GenerationService(adapter=script, checker_adapter=script).generate(
        request, RequestBudget(max_calls=calls, max_active_seconds=180)
    )
    assert (request.question, request.evidence, request.source_map) == original
    assert request.evidence[0]["text"] == SOURCE and len(SOURCE) == 165
    return outcome, script


def _stages(script):
    return [kwargs["request_context"]["purpose"] for _messages, kwargs in script.calls]


def _accepted(outcome, text):
    assert outcome.succeeded, outcome.error
    assert outcome.response["answer_text"] == text
    assert outcome.delivered_projection["response"] == outcome.response
    assert (
        outcome.delivered_projection["content_hash"]
        == outcome.checks[-1]["delivered_projection_hash"]
    )
    assert outcome.checks[-1]["accepted"] is True
    assert outcome.checks[-1]["validation_state"] == "validated"
    assert outcome.attribution["check_state"] == "model_checked"
    assert outcome.token_budget["claim_support"]["accepted"] is True
    assert all(row["support"]["human_rating"] is None for row in outcome.attribution["claims"])


def _capture(record_property, name, outcome, script):
    record_property(
        "authored_semantic_delivery_control",
        json.dumps(
            {
                "control": name,
                "stages": _stages(script),
                "consumed_calls": outcome.budget["consumed_calls"],
                "native_accepted": outcome.succeeded,
                "error_code": (outcome.error or {}).get("code"),
                "checker_diagnostics": [
                    {
                        "raw_typed_judgment": row.get("typed_judgment_raw_aliases"),
                        "raw_normalized_judgment": row.get("judgment_raw_aliases"),
                        "original_inconsistencies": row.get("original_checker_inconsistencies"),
                        "routing": row.get("semantic_negative_routing"),
                        "accepted": row["accepted"],
                    }
                    for row in outcome.checks
                ],
                "fixture_verdict_is_semantic_accuracy_evidence": False,
                "human_rating": None,
            }
        ),
    )


@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_named_negative_with_aggregate_conflict_uses_repair_and_fresh_check(
    record_property, status
):
    snapshots = []
    out, script = _run(
        [
            draft(COMPOUND),
            _negative(status=status, snapshots=snapshots),
            draft(PARAPHRASE),
            judgment(),
        ]
    )
    assert _stages(script) == ["generation", "joint_check", "semantic_repair", "joint_recheck"]
    assert out.budget["consumed_calls"] == 4
    first = out.checks[0]
    assert first["typed_judgment_raw_aliases"] == snapshots[0]
    assert first["judgment_raw_aliases"]["body_ok"] is False
    assert first["judgment_raw_aliases"]["complete_answer"] is True
    assert first["judgment_raw_aliases"]["coverage"] == "supported_partial"
    assert first["judgment_raw_aliases"]["limitations_explicit"] is False
    assert first["judgment_raw_aliases"]["claims"][0]["status"] == status
    assert first["accepted"] is False
    assert first["original_checker_inconsistencies"] == [
        {"code": "COMPLETE_PARTIAL_WITHOUT_LIMITS"}
    ]
    route = first["semantic_negative_routing"]
    assert route["route"] == "semantic_repair"
    assert route["judgment_changed"] is False and route["publication_override"] is False
    assert route["independent_semantic_evaluation"] is False
    assert route["deferred_aggregate_issues"] == [
        {
            "origin": "checker_inconsistency",
            "code": "COMPLETE_PARTIAL_WITHOUT_LIMITS",
        }
    ]
    assert any(row.get("code") == "CLAIM_" + status.upper() for row in route["retained_negatives"])
    assert _data(script.calls[1][0])["CLAIMS"][0]["text"] == COMPOUND
    assert _data(script.calls[3][0])["CLAIMS"][0]["text"] == PARAPHRASE
    assert first["projection_hash"] != out.checks[-1]["projection_hash"]
    assert all(row["sufficiency"] == "sufficient" for row in snapshots[0]["requirements"])
    assert all(not row["missing_information"] for row in snapshots[0]["requirements"])
    _accepted(out, PARAPHRASE)
    _capture(record_property, "aggregate_negative_" + status, out, script)


def test_initial_faithful_paraphrase_needs_only_the_original_two_calls(record_property):
    out, script = _run([draft(PARAPHRASE), judgment()])
    assert _stages(script) == ["generation", "joint_check"]
    assert out.budget["consumed_calls"] == 2
    assert "Sunshine" not in SOURCE
    assert "semantic_negative_routing" not in out.checks[0]
    _accepted(out, PARAPHRASE)
    _capture(record_property, "initial_meaning_preserving_paraphrase", out, script)


def test_explicit_general_knowledge_example_retains_its_separate_basis(record_property):
    value = source_request(general=True)
    script = Script([draft(OUTSIDE, cited=False), judgment()])
    out = GenerationService(adapter=script, checker_adapter=script).generate(
        value, RequestBudget(max_calls=2, max_active_seconds=180)
    )
    assert "In textbook mode, a preference for examples" in script.calls[0][0][0]["content"]
    assert _stages(script) == ["generation", "joint_check"]
    assert out.succeeded, out.error
    assert out.response["citations"] == []
    assert out.delivered_projection["citation_views"] == []
    assert out.attribution["claims"][0]["support"]["basis"] == "general_knowledge"
    assert out.checks[-1]["accepted"] is True
    assert "semantic_negative_routing" not in out.checks[0]
    _capture(record_property, "explicit_general_knowledge_basis", out, script)


def test_negative_final_fresh_judgment_never_publishes(record_property):
    out, script = _run(
        [
            draft(COMPOUND),
            _negative(),
            draft(COMPOUND),
            _negative(),
        ]
    )
    assert _stages(script) == ["generation", "joint_check", "semantic_repair", "joint_recheck"]
    assert out.budget["consumed_calls"] == 4
    assert not out.succeeded and out.response is None and not out.delivered_projection
    assert out.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert all(row["accepted"] is False for row in out.checks)
    assert out.checks[-1]["judgment_raw_aliases"]["claims"][0]["status"] == "partial"
    assert out.checks[-1]["semantic_negative_routing"]["publication_override"] is False
    _capture(record_property, "final_negative_remains_unpublished", out, script)


@pytest.mark.parametrize(
    "defect,code",
    [
        ("identity", "CLAIM_IDENTITY_MISMATCH"),
        ("fragment", "FRAGMENT_IDENTITY_MISMATCH"),
        ("requirement_quote", "REQUIREMENT_SOURCE_QUOTE_INVALID"),
        ("schema", "CHECKER_SCHEMA_INVALID"),
    ],
)
def test_invalid_contract_stays_on_checker_contract_path(record_property, defect, code):
    def mutate(value, _data):
        if defect == "identity":
            value["claims"][0]["claim_id"] = "foreign_claim"
        elif defect == "fragment":
            value["claims"][0]["citations"][0]["fragment_ids"] = ["F999"]
        elif defect == "requirement_quote":
            value["requirements"][0]["evidence"][0]["quote"] = "Invented source quotation."
        else:
            del value["non_repetitive_next_action"]

    out, script = _run(
        [
            draft(COMPOUND),
            _negative(mutate=mutate),
            _negative(aggregate=False),
        ],
        calls=3,
    )
    assert _stages(script) == ["generation", "joint_check", "checker_contract_repair"]
    assert code in {row["code"] for row in out.checks[0]["checker_inconsistencies"]}
    assert "semantic_negative_routing" not in out.checks[0]
    assert not out.succeeded and out.response is None and not out.delivered_projection
    assert all(row["accepted"] is False for row in out.checks)
    _capture(record_property, "contract_exclusion_" + defect, out, script)


@pytest.mark.parametrize("basis", ["problem_input", "derived_calculation"])
def test_mixed_given_or_derivation_variant_is_excluded_from_new_route(record_property, basis):
    value = source_request()
    value.question += " The example value is 2. Use x + x."
    text = COMPOUND + (
        " The example value is 2."
        if basis == "problem_input"
        else " Using the given value, 2 + 2 = 4."
    )

    def mutate(check, data):
        second = data["CLAIMS"][1]
        row = {
            "claim_id": second["claim_id"],
            "basis": basis,
            "status": "supported",
            "reason": "Authored valid mixed-basis fixture; excluded from the new route.",
        }
        if basis == "problem_input":
            row["problem_quote"] = "The example value is 2."
        else:
            row.update(
                citations=[],
                derivation={
                    "formula_basis": "problem_input",
                    "formula_fragment_id": None,
                    "formula_quote": "x + x",
                    "expression": "x+x",
                    "inputs": [
                        {
                            "name": "x",
                            "value": "2",
                            "unit": "",
                            "quote": "The example value is 2.",
                            "origin": "problem_input",
                            "fragment_id": None,
                        }
                    ],
                    "result": "4",
                    "result_quote": "4",
                    "result_unit": "",
                    "units_consistent": True,
                    "formula_applicable": True,
                },
            )
        check["claims"][1] = row

    out, script = _run(
        [
            draft(text),
            _negative(mutate=mutate),
            _negative(aggregate=False, mutate=mutate),
        ],
        value=value,
        calls=3,
    )
    assert _stages(script) == ["generation", "joint_check", "checker_contract_repair"]
    first = out.checks[0]
    assert first["checker_inconsistencies"] == [{"code": "COMPLETE_PARTIAL_WITHOUT_LIMITS"}]
    assert first["typed_judgment_raw_aliases"]["claims"][1]["basis"] == basis
    assert "semantic_negative_routing" not in first
    assert not out.succeeded and out.response is None and not out.delivered_projection
    _capture(record_property, "mixed_basis_exclusion_" + basis, out, script)


BAD_OPENING = "Photosynthesis is how a plant uses light to make its own food."
APPROVED_BODY = (
    "Light energy is captured and stored as chemical energy in sugars [ev_001]. "
    "Light supplies energy to turn carbon dioxide and water into sugars [ev_001]. "
    "Oxygen is released [ev_001]."
)
APPROVED_SHORT = (
    "Photosynthesis captures light energy and stores chemical energy in sugars [ev_001]."
)


@pytest.mark.parametrize("preserve", [True, False])
def test_style_repair_preserves_approved_spans_or_stops_before_fresh_checker(
    record_property, preserve
):
    value = source_request()
    value.question = "Explain photosynthesis more simply."
    initial = draft(BAD_OPENING + " " + APPROVED_BODY)
    initial["short_answer"] = APPROVED_SHORT
    repaired = draft(APPROVED_BODY if preserve else PARAPHRASE)
    repaired["short_answer"] = APPROVED_SHORT
    out, script = _run(
        [
            initial,
            _negative(status="unsupported", aggregate=False),
            repaired,
            judgment(),
        ],
        value=value,
    )
    feedback = json.loads(script.calls[2][0][-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    approved = feedback["protected_exact_claims"]
    assert len(approved) == 4
    assert all(row["text"] != BAD_OPENING for row in approved)
    assert any(
        row["answer_field"] == "short_answer" and row["text"] == APPROVED_SHORT for row in approved
    )
    assert "Copy every protected_exact_claims text verbatim" in script.calls[2][0][-1]["content"]
    if preserve:
        assert _stages(script) == ["generation", "joint_check", "semantic_repair", "joint_recheck"]
        assert all(row["text"] in out.response[row["answer_field"]] for row in approved)
        _accepted(out, APPROVED_BODY)
    else:
        assert _stages(script) == ["generation", "joint_check", "semantic_repair"]
        assert out.budget["consumed_calls"] == 3
        assert out.error["code"] == "REPAIR_CHANGED_APPROVED_CONTENT"
        assert len(out.checks) == 1
        assert not out.succeeded and out.response is None and not out.delivered_projection
    _capture(record_property, "protected_style_spans_" + str(preserve), out, script)
