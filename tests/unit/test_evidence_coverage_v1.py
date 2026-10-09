"""Automatic context estimates, whole-source preservation and one bounded supplement."""

from copy import deepcopy
import hashlib

import pytest

from generation.evidence_coverage import assess_evidence_coverage, supplement_once
from generation.teaching_plan import freeze_generation_policy


def evidence(identity, text):
    return {
        "evidence_id": "ev_" + identity,
        "chunk_id": identity,
        "text": text,
        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
    }


def facets():
    return {
        "facet_origin": "explicit_clauses",
        "requested_facets": [
            {
                "id": "light",
                "request": "Explain light absorption",
                "terms": ["light", "absorption"],
            },
            {"id": "carbon", "request": "Explain carbon fixation", "terms": ["carbon", "fixation"]},
        ],
    }


def test_context_coverage_and_draft_support_are_separate():
    report = assess_evidence_coverage(
        "Explain carbon fixation", [evidence("1", "Carbon fixation uses the supplied material.")]
    )
    assert report["context_sufficiency_estimate"] == "lexically_complete"
    assert report["draft_support"] is None and report["semantic_sufficiency"] is None
    assert report["human_rating"] is None


def test_budget_loss_names_complementary_requirements_and_retains_exclusions():
    rows = [
        evidence("1", "Light absorption begins this process."),
        evidence("2", "Carbon fixation proceeds under suitable conditions."),
    ]
    excluded = [{"chunk_id": "2", "reason": "evidence_ceiling"}]
    before = deepcopy(rows)
    report = assess_evidence_coverage(
        "Explain both stages.",
        rows,
        facets(),
        selected_evidence=rows[:1],
        excluded_evidence=excluded,
    )
    assert report["candidate_coverage"]["status"] == "lexically_complete"
    assert report["packed_coverage"]["status"] == "partial"
    assert report["budget_lost_requirement_ids"] == ["carbon"]
    assert report["budget_exclusions"] == excluded
    assert not report[
        "targeted_query"
    ]  # Packing loss calls for repacking, not duplicate retrieval.
    assert rows == before


def test_dna_rna_comparison_names_axes_with_inspectable_origins():
    rows = [
        evidence("1", "DNA contains the sugar deoxyribose and the base thymine."),
        evidence("2", "RNA contains ribose and uracil."),
    ]
    report = assess_evidence_coverage("Compare DNA and RNA.", rows)
    assert len(report["candidate_coverage"]["requirements"]) == 8
    assert "dna_structure" in report["candidate_coverage"]["missing_requirement_ids"]
    assert "dna_sugar" not in report["candidate_coverage"]["missing_requirement_ids"]
    assert report["targeted_query"].startswith("Compare DNA and RNA.")


def test_entities_and_axes_must_cooccur_in_a_passage():
    rows = [
        evidence("1", "DNA has a double-stranded helix."),
        evidence("2", "RNA carries information."),
    ]
    report = assess_evidence_coverage("Compare DNA and RNA structure.", rows)
    assert report["candidate_coverage"]["missing_requirement_ids"] == ["rna_structure"]


def test_a_simple_lexical_miss_does_not_trigger_repeat_retrieval():
    report = assess_evidence_coverage(
        "Why does ATP provide energy?", [evidence("1", "ATP stores energy.")]
    )
    assert report["context_sufficiency_estimate"] == "partial"
    assert report["targeted_query"] is None


def test_one_targeted_pass_merges_complementary_sources_and_preserves_original_question():
    rows = [evidence("1", "Light absorption begins this process.")]
    additional = evidence("2", "Carbon fixation requires these conditions.")
    calls, checkpoints = [], []

    def retrieve(query, limit):
        calls.append((query, limit))
        return [additional]

    actual, report, trace = supplement_once(
        "Explain both stages at constant temperature.",
        rows,
        facets(),
        freeze_generation_policy(),
        retrieve=retrieve,
        rerank=lambda q, values: values,
        screen=lambda q, values: (values, {}),
        checkpoint=lambda phase, data: checkpoints.append(phase),
    )
    assert actual == rows + [additional]
    assert len(calls) == 1 and calls[0][1] == 10
    assert calls[0][0].startswith("Explain both stages at constant temperature.")
    assert trace["retrieval_passes"] == 1 and trace["added_chunk_ids"] == ["2"]
    assert report["context_sufficiency_estimate"] == "lexically_complete"
    assert checkpoints == ["retrieving", "reranking", "completed"]


def test_an_unsatisfied_supplement_stops_after_one_pass():
    calls = []
    result, report, trace = supplement_once(
        "Explain both stages",
        [evidence("1", "Light absorption")],
        facets(),
        freeze_generation_policy(),
        retrieve=lambda q, n: calls.append(q) or [],
        rerank=lambda q, rows: rows,
        screen=lambda q, rows: (rows, {}),
        checkpoint=lambda phase, data: None,
    )
    assert len(calls) == 1
    assert report["context_sufficiency_estimate"] == "partial"
    assert trace["reason"] == "completed"


def test_cancellation_checkpoint_prevents_the_extra_retrieval():
    calls = []

    def cancelled(phase, trace):
        raise RuntimeError("cancelled")

    with pytest.raises(RuntimeError, match="cancelled"):
        supplement_once(
            "Explain both stages",
            [evidence("1", "Light absorption")],
            facets(),
            freeze_generation_policy(),
            retrieve=lambda q, n: calls.append(q),
            rerank=lambda q, rows: rows,
            screen=lambda q, rows: (rows, {}),
            checkpoint=cancelled,
        )
    assert calls == []


@pytest.mark.parametrize("fault", ["limit", "membership", "identity"])
def test_bad_supplement_cannot_change_sources_or_escape_its_bound(fault):
    original = evidence("1", "Light absorption")
    incoming = (
        [evidence(str(i + 2), "Carbon fixation") for i in range(11)]
        if fault == "limit"
        else [evidence("1", "Changed carbon fixation")]
    )
    with pytest.raises(ValueError):
        supplement_once(
            "Explain both stages",
            [original],
            facets(),
            freeze_generation_policy(),
            retrieve=lambda q, n: incoming,
            rerank=lambda q, rows: [] if fault == "membership" else rows,
            screen=lambda q, rows: (rows, {}),
            checkpoint=lambda phase, data: None,
        )
