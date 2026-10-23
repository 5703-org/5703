"""A whole-question fallback must not double reranker input or erase conditions."""

import pytest
from generation import coverage_v3, teaching_plan_v10


@pytest.mark.parametrize(
    "question",
    [
        "A sealed sample is at 283 K. Explain whether its pressure rises at fixed volume.",
        "Compare a 7 mmol dose and a 7 mol sample; do not assume equal quantities.",
        "Does the reaction remain spontaneous at 1 bar but not at 2 bar?",
        "Compare Co and CO. Keep case-sensitive chemical notation.",
    ],
)
def test_whole_question_fallback_stays_verbatim_and_missing_not_certified(question):
    understanding = {"required_knowledge": [{"id": "r1", "request": question.rstrip(".?!")}]}
    report = coverage_v3.assess_evidence_coverage(question, [], understanding)
    assert report["targeted_query"] == question
    assert (
        report["locatable_missing"][0]["request"]
        == understanding["required_knowledge"][0]["request"]
    )
    assert report["semantic_sufficiency"] is None
    assert report["candidate_coverage"]["missing_requirement_ids"] == ["r1"]
    calls = []
    evidence, after, trace = coverage_v3.supplement_once(
        question,
        [],
        understanding,
        teaching_plan_v10.freeze_generation_policy(),
        retrieve=lambda q, k: calls.append((q, k)) or [],
        rerank=lambda q, rows: rows,
        screen=lambda q, rows: (rows, {}),
        checkpoint=lambda *a: None,
    )
    assert calls == [(question, 10)]
    assert evidence == [] and after["semantic_sufficiency"] is None
    assert trace["retrieval_passes"] == 1


@pytest.mark.parametrize(
    "question,requirement",
    [
        ("Explain diffusion and osmosis.", "Explain osmosis"),
        ("Explain the result at 1 bar.", "Explain the result at 2 bar"),
        ("Explain why the rate does not rise.", "Explain why the rate does rise"),
        ("Explain Co.", "Explain CO"),
        ("Explain the mass in mg.", "Explain the mass in g"),
    ],
)
def test_different_requirements_keep_original_explicit_emphasis(question, requirement):
    report = coverage_v3.assess_evidence_coverage(
        question, [], {"required_knowledge": [{"id": "r1", "request": requirement}]}
    )
    assert report["targeted_query"] == question + "\nRequired knowledge: " + requirement


def test_fully_covered_requirement_still_needs_no_supplement():
    report = coverage_v3.assess_evidence_coverage(
        "Explain diffusion.",
        [{"chunk_id": "c1", "text": "Diffusion is particle movement."}],
        {"required_knowledge": [{"id": "r1", "request": "Diffusion"}]},
    )
    assert report["targeted_query"] is None
    assert report["semantic_sufficiency"] is None
