"""Versioned distributed coverage tests using authored source fixtures."""

from generation import coverage_v2, coverage_v3, teaching_plan_v2, teaching_plan_v3


QUESTION = "Compare diffusion and osmosis."
COMPLEMENTARY = [
    {"evidence_id": "ev_001", "chunk_id": "diffusion", "text": "Diffusion moves particles."},
    {"evidence_id": "ev_002", "chunk_id": "osmosis", "text": "Osmosis moves water."},
]


def test_complementary_chunks_avoid_a_redundant_targeted_retrieval():
    old = coverage_v2.assess_evidence_coverage(QUESTION, COMPLEMENTARY)
    current = coverage_v3.assess_evidence_coverage(QUESTION, COMPLEMENTARY)
    assert old["candidate_coverage"]["status"] == "partial"
    assert old["targeted_query"] is not None
    assert current["candidate_coverage"]["status"] == "partial"
    assert current["distributed_requirement_ids"] == ["requirement_01"]
    assert current["targeted_query"] is None
    point = current["candidate_coverage"]["requirements"][0]
    assert point["distributed_across_passages"] is True
    assert point["single_passage_covered"] is False
    assert point["semantic_sufficiency"] is None
    assert {row["evidence_id"] for row in point["matched_evidence"]} == {
        "ev_001",
        "ev_002",
    }
    calls = []
    final, report, trace = coverage_v3.supplement_once(
        QUESTION,
        COMPLEMENTARY,
        None,
        teaching_plan_v3.freeze_generation_policy(),
        retrieve=lambda *_: calls.append("retrieve") or [],
        rerank=lambda _, rows: rows,
        screen=lambda _, rows: (rows, {}),
        checkpoint=lambda *_: None,
    )
    assert final == COMPLEMENTARY
    assert report["semantic_sufficiency"] is None
    assert trace["retrieval_passes"] == 0 and calls == []


def test_packing_loss_remains_visible_and_cannot_claim_semantic_sufficiency():
    report = coverage_v3.assess_evidence_coverage(
        QUESTION,
        COMPLEMENTARY,
        selected_evidence=COMPLEMENTARY[:1],
        excluded_evidence=[{"chunk_id": "osmosis", "reason": "evidence_ceiling"}],
    )
    assert report["candidate_coverage"]["status"] == "partial"
    assert report["packed_coverage"]["status"] == "partial"
    assert report["context_sufficiency_estimate"] == "partial"
    assert report["budget_lost_requirement_ids"] == ["requirement_01"]
    assert report["semantic_sufficiency"] is None


def test_an_actual_missing_concept_still_gets_one_bounded_lookup():
    source = COMPLEMENTARY[:1]
    calls = []

    def retrieve(query, limit):
        calls.append((query, limit))
        return COMPLEMENTARY[1:]

    final, report, trace = coverage_v3.supplement_once(
        QUESTION,
        source,
        None,
        teaching_plan_v3.freeze_generation_policy(),
        retrieve=retrieve,
        rerank=lambda _, rows: rows,
        screen=lambda _, rows: (rows, {}),
        checkpoint=lambda *_: None,
    )
    assert len(calls) == trace["retrieval_passes"] == 1
    assert calls[0][1] == 10
    assert final == COMPLEMENTARY
    assert report["candidate_coverage"]["status"] == "partial"
    assert trace["added_chunk_ids"] == ["osmosis"]


def test_split_negation_and_conditions_are_never_marked_complete():
    report = coverage_v3.assess_evidence_coverage(
        "Compare diffusion and osmosis without a membrane.",
        [
            {
                "evidence_id": "ev_001",
                "chunk_id": "c1",
                "text": "Diffusion occurs without a membrane.",
            },
            {"evidence_id": "ev_002", "chunk_id": "c2", "text": "Osmosis requires a membrane."},
        ],
    )
    assert report["context_sufficiency_estimate"] == "partial"
    assert report["distributed_requirement_ids"] == ["requirement_01"]
    assert report["semantic_sufficiency"] is None


def test_frozen_v2_policy_and_plan_keep_their_original_identity():
    prior = teaching_plan_v2.freeze_generation_policy()
    current = teaching_plan_v3.freeze_generation_policy()
    assert prior["version"] == "generation_controls_v2"
    assert prior["coverage_version"] == "context_coverage_v2"
    assert current["version"] == "generation_controls_v3"
    assert current["coverage_version"] == "context_coverage_v3"
    assert teaching_plan_v2.build_teaching_plan(QUESTION, None, policy=prior)["version"] == (
        "progress_action_plan_v2"
    )
    assert teaching_plan_v3.build_teaching_plan(QUESTION, None, policy=current)["version"] == (
        "progress_action_plan_v3"
    )
