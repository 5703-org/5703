"""Authored lexical/query boundaries; no fabricated formal textbook outcomes."""

import hashlib
import json
from copy import deepcopy

import pytest
from generation import coverage_v3, coverage_v4, coverage_v5, teaching_plan_v6
from generation.unit_definition_plan_v1 import CATALOG_SHA256, UNIT_NAMES, plan

GAS = (
    "In the ideal gas law PV = nRT, why must temperature be expressed in kelvin, "
    "and which pressure and volume units are consistent with R = 8.314 J mol-1 K-1?"
)
UNIT_FACET = "which pressure and volume units are consistent with R = 8.314 J mol-1 K-1"


def supplied(question, request=None):
    literal = request if request is not None else question
    start = question.index(literal)
    return {
        "version": "question_requirements_v5",
        "requirement_source_text": question,
        "original_message": question,
        "required_knowledge": [
            {
                "id": "requirement_01",
                "request": literal,
                "verbatim_request": literal,
                "origin": "verbatim_question_structure_v5",
                "intent": "explanation",
                "relation": "explanation",
                "objects": [],
                "conditions": ["Authored condition preserved verbatim"],
                "request_span": {
                    "coordinate_space": "requirement_source_text",
                    "start": start,
                    "end": start + len(literal),
                },
            }
        ],
        "preserved_constraints": {
            "negation": ["without heating"],
            "quantities_and_units": [{"text": "8.314 J mol-1 K-1"}],
        },
    }


def report_for(question, context):
    return coverage_v4.assess_evidence_coverage(question, [], context)


def evidence(identity, text="Authored source fixture; no semantic certification."):
    return {
        "chunk_id": identity,
        "evidence_id": "ev_" + identity,
        "text": text,
        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
        "asset_id": "fixture_asset",
        "processing_id": "fixture_processing",
    }


def test_original_gas_request_is_decomposed_without_changing_any_requirement_or_constraint():
    context = supplied(GAS, UNIT_FACET)
    report = report_for(GAS, context)
    before = deepcopy((context, report))
    result = plan(GAS, report, context)
    assert result["query"] == (
        "SI unit definitions for joule, mole, kelvin. Units of pressure, volume."
    )
    assert result["status"] == "planned_auxiliary_unit_definitions"
    assert [row["literal"] for row in result["aliases"]] == ["J", "mol", "K"]
    assert result["semantic_sufficiency"] is None and result["source_relation_verified"] is None
    assert (context, report) == before
    assert "8.314" in context["required_knowledge"][0]["request"]
    assert context["preserved_constraints"] == before[0]["preserved_constraints"]
    literal = context["required_knowledge"][0]["request"]
    for alias in result["aliases"]:
        assert literal[alias["start"] : alias["end"]] == alias["literal"]


@pytest.mark.parametrize(
    "question,names",
    [
        ("Which units describe energy equal to 2.5 J without heating?", ["joule"]),
        (
            "Which units describe pressure of -2.5 Pa at constant temperature?",
            ["pascal"],
        ),
        ("What is the SI unit definition of 14 N for force?", ["newton"]),
        ("What is the SI unit definition of 60 Hz for frequency?", ["hertz"]),
        ("What are the SI definitions of joules and pascals?", ["joule", "pascal"]),
        ("Explain unit J and work.", ["joule"]),
        (
            "Which mass units apply to 2 kg and which length units to 3 m?",
            ["kilogram", "metre"],
        ),
    ],
)
def test_common_explicit_unit_queries_are_not_a_single_gas_question_rule(question, names):
    context = supplied(question)
    result = plan(question, report_for(question, context), context)
    assert [row["unit_name"] for row in result["aliases"]] == names
    assert result["query"] is not None
    assert context["requirement_source_text"] == question


@pytest.mark.parametrize(
    "question,status",
    [
        ("Which units match 8.314 j mol-1 K-1?", "unknown_unit_token"),
        ("Which pressure units match 2 pa?", "unknown_unit_token"),
        ("Which units match 3 kPa?", "unknown_unit_token"),
        ("Which units match 2 J foo-1?", "unknown_unit_token"),
        ("Which units describe 2 N2 molecules?", "unknown_unit_token"),
        ("Which units describe 2 J N2?", "unknown_unit_token"),
        ("Which volume units describe 3 m3?", "unknown_unit_token"),
        (
            "Which units are required for the second lesson?",
            "unknown_unit_token",
        ),
        (
            "Which units explain moles on skin?",
            "unknown_unit_token",
        ),
        (
            "Explain the unit of a mole.",
            "ambiguous_named_unit_without_physical_context",
        ),
        (
            "Which units apply to a second?",
            "ambiguous_named_unit_without_physical_context",
        ),
        (
            "Explain unit A in our course.",
            "ambiguous_unit_label_without_physical_context",
        ),
        (
            "What is the definition of unit J?",
            "ambiguous_unit_label_without_physical_context",
        ),
        ("Which units apply to the variable N?", "no_unambiguous_named_unit"),
        ("What is the unit of variable J?", "no_unambiguous_named_unit"),
        ("Explain RAG and RNA.", "not_applicable"),
        ("Compare DNA and RNA.", "not_applicable"),
        ("Explain ragweed allergy.", "not_applicable"),
        ("Describe work allocation.", "not_applicable"),
    ],
)
def test_unknown_ambiguous_case_mismatched_and_unrelated_requests_keep_previous_query(
    question, status
):
    context = supplied(question)
    old = report_for(question, context)
    current = coverage_v5.assess_evidence_coverage(
        question, [], context, base_version=coverage_v4.VERSION
    )
    assert current["coverage_query_plan"]["status"] == status
    assert current["coverage_query_plan"]["query"] is None
    assert current["targeted_query"] == old["targeted_query"]
    assert current["candidate_coverage"] == old["candidate_coverage"]


@pytest.mark.parametrize(
    "defect",
    [
        "missing_source",
        "bad_start",
        "bool_start",
        "wrong_space",
        "changed_request",
        "changed_verbatim",
    ],
)
def test_unverified_source_coordinates_never_replace_the_old_query(defect):
    context = supplied(GAS, UNIT_FACET)
    point = context["required_knowledge"][0]
    if defect == "missing_source":
        del context["requirement_source_text"]
    elif defect == "bad_start":
        point["request_span"]["start"] += 1
    elif defect == "bool_start":
        point["request_span"]["start"] = True
    elif defect == "wrong_space":
        point["request_span"]["coordinate_space"] = "standalone_query"
    elif defect == "changed_request":
        point["request"] += " without heating"
    else:
        point["verbatim_request"] += " without heating"
    old = report_for(GAS, context)
    current = coverage_v5.assess_evidence_coverage(
        GAS, [], context, base_version=coverage_v4.VERSION
    )
    assert current["coverage_query_plan"]["status"] == "unverified_current_requirement_coordinates"
    assert current["targeted_query"] == old["targeted_query"]


def test_no_missing_lexical_requirement_creates_a_new_supplement():
    question = "Which units describe energy of 2 J?"
    context = supplied(question)
    row = evidence("all", question)
    calls = []
    final, report, trace = coverage_v5.supplement_once(
        question,
        [row],
        context,
        teaching_plan_v6.freeze_generation_policy(),
        base_version=coverage_v4.VERSION,
        retrieve=lambda *_: calls.append("retrieve") or [],
        rerank=lambda _, values: values,
        screen=lambda _, values: (values, {}),
        checkpoint=lambda *_: calls.append("checkpoint"),
    )
    assert calls == [] and trace["retrieval_passes"] == 0
    assert final == [row] and report["semantic_sufficiency"] is None


def test_one_ten_candidate_lookup_preserves_original_rows_and_has_no_second_lookup():
    context = supplied(GAS, UNIT_FACET)
    original = evidence("original")
    supplemental = evidence("supplemental")
    before = deepcopy((context, original))
    calls, stages = [], []

    def retrieve(query, limit):
        calls.append((query, limit))
        return [supplemental]

    final, report, trace = coverage_v5.supplement_once(
        GAS,
        [original],
        context,
        teaching_plan_v6.freeze_generation_policy(),
        base_version=coverage_v4.VERSION,
        retrieve=retrieve,
        rerank=lambda _, rows: rows,
        screen=lambda _, rows: (rows, {}),
        checkpoint=lambda stage, _: stages.append(stage),
    )
    assert len(calls) == 1 and calls[0][1] == 10
    assert final == [original, supplemental]
    assert trace["retrieval_passes"] == 1 and trace["added_chunk_ids"] == ["supplemental"]
    assert trace["query"].startswith("SI unit definitions")
    assert stages == ["retrieving", "reranking", "completed"]
    assert report["semantic_sufficiency"] is None and report["draft_support"] is None
    assert (context, original) == before


@pytest.mark.parametrize(
    "defect,error",
    [
        ("too_many", "COVERAGE_SUPPLEMENT_CANDIDATE_LIMIT"),
        ("duplicate", "COVERAGE_SUPPLEMENT_CANDIDATE_LIMIT"),
        ("rerank_missing", "COVERAGE_SUPPLEMENT_MEMBERSHIP_CHANGED"),
        ("screen_foreign", "COVERAGE_SUPPLEMENT_SCREEN_MEMBERSHIP_CHANGED"),
        ("changed_text", "COVERAGE_SUPPLEMENT_SOURCE_CHANGED"),
        ("changed_hash", "COVERAGE_SUPPLEMENT_SOURCE_CHANGED"),
        ("changed_asset", "COVERAGE_SUPPLEMENT_SOURCE_CHANGED"),
        ("changed_processing", "COVERAGE_SUPPLEMENT_SOURCE_CHANGED"),
    ],
)
def test_existing_source_candidate_membership_and_source_identity_guards_remain(defect, error):
    original = evidence("original")
    rows = [deepcopy(original)]
    if defect == "too_many":
        rows = [evidence(str(i)) for i in range(11)]
    elif defect == "duplicate":
        rows = [deepcopy(original), deepcopy(original)]
    elif defect.startswith("changed_"):
        field = {
            "text": "text",
            "hash": "text_hash",
            "asset": "asset_id",
            "processing": "processing_id",
        }[defect[8:]]
        rows[0][field] += "_changed"
    with pytest.raises(ValueError, match=error):
        coverage_v5.supplement_once(
            GAS,
            [original],
            supplied(GAS, UNIT_FACET),
            teaching_plan_v6.freeze_generation_policy(),
            base_version=coverage_v4.VERSION,
            retrieve=lambda *_: rows,
            rerank=lambda _, values: [] if defect == "rerank_missing" else values,
            screen=lambda _, values: (
                ([evidence("foreign")], {}) if defect == "screen_foreign" else (values, {})
            ),
            checkpoint=lambda *_: None,
        )


def test_cancel_or_timeout_checkpoint_aborts_before_retrieval():
    calls = []

    def exhausted(*_):
        raise RuntimeError("Authored active budget or cancellation boundary")

    with pytest.raises(RuntimeError):
        coverage_v5.supplement_once(
            GAS,
            [],
            supplied(GAS, UNIT_FACET),
            teaching_plan_v6.freeze_generation_policy(),
            base_version=coverage_v4.VERSION,
            retrieve=lambda *_: calls.append("retrieve") or [],
            rerank=lambda _, values: values,
            screen=lambda _, values: (values, {}),
            checkpoint=exhausted,
        )
    assert calls == []


def test_alias_catalog_contains_only_names_and_is_hash_bound_not_equations():
    assert (
        CATALOG_SHA256
        == hashlib.sha256(
            json.dumps(UNIT_NAMES, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    assert all(name.isalpha() for name in UNIT_NAMES.values())
    assert not any("=" in name or "8.314" in name for name in UNIT_NAMES.values())


@pytest.mark.parametrize("suffix", ["m^3", "m³", "m^-3"])
def test_unambiguous_unit_power_keeps_the_exact_original_literal_and_does_not_invent_a_relation(
    suffix,
):
    question = "Which volume units describe 3 " + suffix + "?"
    context = supplied(question)
    original = deepcopy(context)
    result = plan(question, report_for(question, context), context)
    assert result["query"] == "SI unit definitions for metre. Units of volume."
    assert context == original
    assert result["source_relation_verified"] is None


@pytest.mark.parametrize("base", [coverage_v3, coverage_v4])
def test_non_unit_lookup_keeps_the_exact_request_frozen_base_estimate_and_query(base):
    question = "Explain the role of a catalyst."
    rows = [evidence("catalyst", "A catalyst speeds a reaction.")]
    context = supplied(question)
    old = base.assess_evidence_coverage(question, rows, context)
    current = coverage_v5.assess_evidence_coverage(
        question, rows, context, base_version=base.VERSION
    )
    for key in [
        "candidate_coverage",
        "packed_coverage",
        "targeted_query",
        "context_sufficiency_estimate",
    ]:
        assert current[key] == old[key]
    assert current["base_coverage_version"] == base.VERSION


def test_unknown_base_version_is_not_an_implicit_strategy_fallback():
    with pytest.raises(ValueError, match="UNKNOWN_COVERAGE_BASE_VERSION"):
        coverage_v5.assess_evidence_coverage(
            GAS, [], supplied(GAS, UNIT_FACET), base_version="unknown"
        )


@pytest.mark.parametrize("version", [None, "question_requirements_v4", "unknown"])
def test_unknown_requirement_producer_keeps_original_lookup(version):
    context = supplied(GAS, UNIT_FACET)
    context["version"] = version
    old = report_for(GAS, context)
    current = coverage_v5.assess_evidence_coverage(
        GAS, [], context, base_version=coverage_v4.VERSION
    )
    assert current["coverage_query_plan"]["status"] == "unsupported_requirement_producer"
    assert current["targeted_query"] == old["targeted_query"]


def test_new_policy_has_no_implicit_base_dispatch():
    with pytest.raises(TypeError, match="base_version"):
        coverage_v5.assess_evidence_coverage(GAS, [], supplied(GAS, UNIT_FACET))


@pytest.mark.parametrize(
    "origin,status",
    [
        ("verified_selected_source_referent_v1", "not_applicable"),
        ("unverified_origin", "unverified_current_requirement_coordinates"),
    ],
)
def test_source_bound_or_unknown_metadata_does_not_become_a_located_user_unit_request(
    origin, status
):
    context = supplied(GAS, UNIT_FACET)
    context["required_knowledge"][0]["origin"] = origin
    old = report_for(GAS, context)
    current = coverage_v5.assess_evidence_coverage(
        GAS, [], context, base_version=coverage_v4.VERSION
    )
    assert current["coverage_query_plan"]["status"] == status
    assert current["targeted_query"] == old["targeted_query"]
