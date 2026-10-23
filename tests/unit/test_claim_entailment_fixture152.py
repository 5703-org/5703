"""Offline evidence/annotation regression. No test performs semantic inference.

The reviewed labels are data, not production checker inputs or scientific
certificates. Tests validate exact captured spans, source ownership, selections,
portable UTF-8 integrity and preservation of the separately reviewed controls.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parents[1] / "fixtures" / "claim_entailment152.json"


def load_fixture():
    raw = FIXTURE.read_bytes()
    return json.loads(raw.decode("utf-8", errors="strict"))


DATA = load_fixture()


def eligible_pairs(case):
    return {
        (row["evidence_id"], fid)
        for row in case["eligible_bindings"]
        for fid in row["allowed_fragment_ids"]
    }


def selected_pairs(case):
    return {
        (row["evidence_id"], fid)
        for row in case["returned_citations"]
        if row["relation"] == "supporting"
        for fid in row["fragment_ids"]
    }


def validate_record_integrity(case, fixture):
    """Check archived provenance only; do not derive a semantic label."""
    claim, context = case["claim"], case["context_id"]
    assert set(claim["evidence_ids"]) == {row["evidence_id"] for row in case["eligible_bindings"]}
    selected = selected_pairs(case)
    assert selected and selected <= eligible_pairs(case)
    for row in case["returned_citations"]:
        assert len(row["fragment_ids"]) == len(set(row["fragment_ids"]))
    for eid, fid in selected:
        fragment = fixture["fragments"][context + ":" + fid]
        assert fragment["context_id"] == context and fragment["fragment_id"] == fid
        assert fragment["evidence_id"] == eid
        text = fragment["exact_text"]
        assert (
            text
            and hashlib.sha256(text.encode("utf-8")).hexdigest()
            == fragment["exact_text_utf8_sha256"]
        )
    if case["origin"] == "captured151":
        surface = fixture["contexts"][context]["answer_surfaces"][claim["answer_field"]]
        assert 0 <= claim["start"] < claim["end"] <= len(surface)
        assert surface[claim["start"] : claim["end"]] == claim["text"]
    else:
        assert claim["start"] == 0 and claim["end"] == len(claim["text"])
        assert case["checker_observation"] is None
    annotation = case["offline_annotation"]
    assert annotation["whole_proposition_status"] in {
        "supported",
        "partial",
        "unsupported",
        "contradicted",
    }
    assert (
        annotation["human_rating"] is None and annotation["machine_entailment_certified"] is False
    )
    assert annotation["rationale"]


@pytest.mark.parametrize("case", DATA["cases"], ids=lambda case: case["case_id"])
def test_exact_fixture_provenance_and_spans(case):
    validate_record_integrity(case, DATA)


def test_sources_are_portable_strict_utf8_exact_fragments():
    for key, fragment in DATA["fragments"].items():
        assert key == fragment["context_id"] + ":" + fragment["fragment_id"]
        assert fragment["exact_text"].encode("utf-8").decode("utf-8") == fragment["exact_text"]
        assert (
            hashlib.sha256(fragment["exact_text"].encode()).hexdigest()
            == fragment["exact_text_utf8_sha256"]
        )
    short = DATA["contexts"]["J02"]["answer_surfaces"]["short_answer"]
    assert short.startswith("No\u2014")  # Preserve the actual captured em dash.
    assert all(row["encoding"] == "UTF-8-strict" for row in DATA["source_files"])


def test_actual_minimal_failure_keeps_selection_eligibility_and_foreign_scope_separate():
    case = next(
        row
        for row in DATA["cases"]
        if row["claim"]["claim_id"] == "claim_b127bd853dc518bf5b4a4efe_1"
    )
    assert (case["claim"]["start"], case["claim"]["end"]) == (134, 275)
    assert selected_pairs(case) == {("ev_002", "F007"), ("ev_002", "F013")}
    assert ("ev_002", "F015") in eligible_pairs(case) - selected_pairs(case)
    foreign = DATA["fragments"]["J02:F042"]
    assert (foreign["evidence_id"], foreign["fragment_id"]) not in eligible_pairs(case)
    diagnostic = case["provenance_diagnostics"]
    assert diagnostic["eligible_unselected_reason_references"] == ["F015"]
    assert diagnostic["foreign_scoped_available_diagnostic_fragments"] == ["F042"]
    assert diagnostic["raw_reason_foreign_references"] == []
    assert (
        "F015" in case["checker_observation"]["reason"]
        and "F042" not in case["checker_observation"]["reason"]
    )
    assert case["checker_observation"]["status"] == "supported"
    assert case["offline_annotation"]["whole_proposition_status"] == "partial"


@pytest.mark.parametrize(
    "identity", ["CONTROL_MATERIAL_PARAPHRASE", "CONTROL_COMPLEMENTARY_PARAPHRASE"]
)
def test_recorded_independent_annotations_retain_valid_paraphrases(identity):
    case = next(row for row in DATA["cases"] if row["case_id"] == identity)
    assert case["offline_annotation"]["whole_proposition_status"] == "supported"
    assert not case["offline_annotation"]["unestablished_parts"]
    assert len(selected_pairs(case)) >= 2
    if identity == "CONTROL_COMPLEMENTARY_PARAPHRASE":
        assert len({eid for eid, _fid in selected_pairs(case)}) == 2


def test_recorded_annotation_retains_source_entailed_conditional_causal_claim():
    case = next(
        row for row in DATA["cases"] if row["case_id"] == "CONTROL_ENTAILED_CONDITIONAL_CAUSAL"
    )
    assert case["offline_annotation"]["whole_proposition_status"] == "supported"
    assert selected_pairs(case) == {("ev_004", "F023")}
    assert "example" in case["offline_annotation"]["rationale"]


def test_negative_annotations_keep_supported_premises_and_contradiction_distinct():
    cases = {row["case_id"]: row for row in DATA["cases"]}
    causal = cases["CONTROL_UNSUPPORTED_CAUSAL_LINK"]["offline_annotation"]
    assert causal["whole_proposition_status"] == "unsupported"
    assert len(causal["supported_parts"]) == 2 and causal["unestablished_parts"]
    assert set(causal["acceptable_negative_checker_statuses"]) == {"partial", "unsupported"}
    opposite = cases["CONTROL_CONTRADICTED_WATER_ENTITY"]["offline_annotation"]
    assert opposite["whole_proposition_status"] == "contradicted"
    assert opposite["native_checker_status_for_annotation"] == "unsupported"


def test_structural_membership_does_not_compute_whole_proposition_entailment():
    # Every recorded case is structurally legal; the independent labels include
    # partial, unsupported and contradiction cases despite legal membership.
    for case in DATA["cases"]:
        validate_record_integrity(case, DATA)
    statuses = {row["offline_annotation"]["whole_proposition_status"] for row in DATA["cases"]}
    assert statuses == {"supported", "partial", "unsupported", "contradicted"}
    assert DATA["safety_boundary"]["membership_and_exact_quotes_certify_entailment"] is False


def test_recorded151_factual_positive_and_negative_controls_are_preserved():
    captured = [row for row in DATA["cases"] if row["origin"] == "captured151"]
    assert len(captured) == 8
    assert (
        sum(
            row["offline_annotation"]["whole_proposition_status"] == "supported" for row in captured
        )
        == 7
    )
    assert (
        sum(row["offline_annotation"]["whole_proposition_status"] == "partial" for row in captured)
        == 1
    )
    assert DATA["preserved151"] == {
        "strict_whole_answer_quality": "1/2",
        "raw_outputs_mutated": False,
    }


def test_source_text_tamper_is_an_integrity_failure_not_a_semantic_verdict():
    changed = deepcopy(DATA)
    case = changed["cases"][0]
    _eid, fid = next(iter(selected_pairs(case)))
    changed["fragments"][case["context_id"] + ":" + fid]["exact_text"] += " Added source text."
    with pytest.raises(AssertionError):
        validate_record_integrity(case, changed)


def test_foreign_citation_tamper_is_rejected_by_provenance_only():
    case = deepcopy(
        next(
            row
            for row in DATA["cases"]
            if row["claim"]["claim_id"] == "claim_b127bd853dc518bf5b4a4efe_1"
        )
    )
    case["returned_citations"] = [
        {"evidence_id": "ev_007", "fragment_ids": ["F042"], "relation": "supporting"}
    ]
    with pytest.raises(AssertionError):
        validate_record_integrity(case, DATA)


def test_fixture_annotations_are_offline_and_candidate150_remains_disabled():
    boundary = DATA["safety_boundary"]
    assert boundary["production_input"] is False and boundary["provider_input"] is False
    assert boundary["Main_hook"] is False and boundary["new_pipeline_or_schema"] is False
    assert boundary["candidate150_default"] == "OFF"
    assert boundary["human_ratings"] is None
