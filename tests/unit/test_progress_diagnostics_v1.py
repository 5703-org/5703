"""Administrator projections expose planning counts without raw memory/source content."""

from types import SimpleNamespace

from app.modules.answering.diagnostics import processing_projection
from generation.teaching_plan import build_teaching_plan
from generation.evidence_coverage import assess_evidence_coverage
from generation.coverage_v3 import assess_evidence_coverage as distributed_coverage


def test_safe_progress_and_context_projection_excludes_raw_private_fields():
    secret = "private-memory-source-content"
    plan = build_teaching_plan(
        "Hint", {"teaching_mode": "hint", "help_level": 1, "current_step": 2}
    )
    plan["private_source"] = secret
    coverage = assess_evidence_coverage(
        "Explain photosynthesis",
        [{"chunk_id": "c1", "evidence_id": "ev_001", "text": "Photosynthesis captures light."}],
    )
    coverage["private_labels"] = secret
    row = SimpleNamespace(
        release_id="release",
        command={},
        trace={
            "progress_plan": plan,
            "context_coverage": coverage,
            "memory_stage": {
                "status": "ready",
                "policy_version": "query_conditioned_memory_v3",
                "candidate_count": 3,
                "selected_count": 1,
                "source_reread_count": 1,
                "raw_sources": secret,
            },
            "retrieval_execution": {
                "coverage_supplement": {
                    "retrieval_passes": 1,
                    "added_chunk_ids": ["new"],
                    "raw_response": secret,
                }
            },
        },
    )
    actual = processing_projection(row, None).model_dump()
    assert actual["progress_plan"]["current_step"] == 2
    assert actual["progress_plan"]["action"] == "recall_concept"
    assert actual["context_coverage"]["supplementary_retrieval_passes"] == 1
    assert actual["memory"]["selected_count"] == 1
    assert secret not in str(actual)
    assert "matched_evidence" not in str(actual)


def test_admin_projection_keeps_distributed_coverage_conservative_without_source_text():
    coverage = distributed_coverage(
        "Compare diffusion and osmosis.",
        [
            {"chunk_id": "c1", "evidence_id": "ev_001", "text": "Diffusion moves particles."},
            {"chunk_id": "c2", "evidence_id": "ev_002", "text": "Osmosis moves water."},
        ],
    )
    row = SimpleNamespace(
        release_id="release",
        command={},
        trace={"context_coverage": coverage},
    )
    actual = processing_projection(row, None).model_dump()["context_coverage"]
    assert actual["version"] == "context_coverage_v3"
    assert actual["estimate"] == "partial"
    assert actual["candidate_coverage"]["status"] == "partial"
    assert actual["distributed_requirement_ids"] == ["requirement_01"]
    assert actual["semantic_status"] is None
    assert "Diffusion moves particles" not in str(actual)
