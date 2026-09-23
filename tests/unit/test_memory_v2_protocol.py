"""Registered study integrity and honest missing-data denominators."""

from collections import Counter
from copy import deepcopy

import pytest

from evaluation.enhancement.protocol import digest
from evaluation.memory_v2.catalogue import generation_input
from evaluation.memory_v2.protocol import (
    schedule,
    require_oracle_confirmation,
    freeze_study,
    outcome_counts,
)


def trajectories():
    return [{"id": f"MV{i:02d}"} for i in range(12)]


def tasks():
    """Independent structural fixtures, without formal study questions or labels."""
    return [
        {
            "id": f"test-{i}",
            "family": f"family-{i}",
            "question": "Authored protocol transport fixture",
            "turns": ["A hint"],
            "critical_answer": "PRIVATE FIXTURE REFERENCE",
            "source_requirement": {"book": f"book-{i // 6}"},
            "teaching_task": i % 2 == 0,
        }
        for i in range(24)
    ]


def test_schedule_preserves_external_rows_and_each_factor():
    rows = schedule(tasks(), trajectories())
    assert Counter(r["study"] for r in rows) == {"A": 72, "B": 72, "C": 48, "T": 180, "M": 180}
    assert len({r["id"] for r in rows}) == 552
    assert sum(r["external_requirement"] is not None for r in rows) == 24
    assert rows == schedule(tasks(), trajectories())
    assert all(r["status"] == "planned" for r in rows)


def test_generated_input_excludes_private_reference_and_oracle():
    private = tasks()[0]
    private["oracle_confirmation"] = {"reviewer_id": "real-reviewer"}
    assert set(generation_input(private)) == {"id", "question", "turns"}
    assert private["critical_answer"] not in str(generation_input(private))


def test_same_family_paraphrases_cannot_inflate_independence():
    values = tasks()
    values[1]["family"] = values[0]["family"]
    with pytest.raises(ValueError, match="families"):
        schedule(values, trajectories())


def test_oracle_requires_actual_identity_and_exact_source():
    task = tasks()[0]
    source_hash = digest({"source": "verified fragment"})
    with pytest.raises(ValueError, match="not been supplied"):
        require_oracle_confirmation(task, source_hash)
    task["oracle_confirmation"] = {
        "reviewer_id": "Codex",
        "confirmed_at": "2026-09-20T01:00:00+00:00",
        "sufficient": True,
        "evidence_sha256": source_hash,
        "coverage": ["required point"],
    }
    with pytest.raises(ValueError, match="not a human"):
        require_oracle_confirmation(task, source_hash)
    task["oracle_confirmation"]["reviewer_id"] = "authored-test-reviewer"
    assert require_oracle_confirmation(task, source_hash)["sufficient"] is True
    with pytest.raises(ValueError, match="does not identify"):
        require_oracle_confirmation(task, digest({"source": "different fragment"}))


def test_failed_missing_unjudged_outputs_remain_in_denominators():
    planned = [{"id": str(i)} for i in range(5)]
    outputs = [
        {"id": "0", "status": "answer"},
        {"id": "1", "status": "answer"},
        {"id": "2", "status": "failed"},
        {"id": "3", "status": "waiting_external"},
    ]
    summary = outcome_counts(planned, outputs, [{"id": "0", "correct": True}])
    assert summary["delivery"]["value"] == 0.4
    assert summary["judgment_coverage"]["value"] == 0.5
    assert summary["correct_among_judged_delivered"]["value"] == 1
    assert summary["end_to_end_correct_conservative"]["value"] == 0.2
    assert summary["unrecorded"] == 1
    with pytest.raises(ValueError, match="Duplicate"):
        outcome_counts(planned, outputs + [outputs[0]], [])
    with pytest.raises(ValueError, match="outside"):
        outcome_counts(planned, [{"id": "unknown", "status": "answer"}], [])


def test_formal_freeze_requires_checkpoint_and_cannot_change(tmp_path):
    destination = tmp_path / "freeze.json"
    with pytest.raises(ValueError, match="complete executable"):
        freeze_study(destination, tasks(), trajectories(), {})
    checkpoint = {
        key: {"test": "authored fixture"}
        for key in (
            "source_hashes",
            "protocol_hashes",
            "model_config",
            "checker_config",
            "corpus",
            "retrieval_hashes",
            "memory_extraction_sha256",
            "memory_gating_sha256",
        )
    }
    original = freeze_study(destination, tasks(), trajectories(), checkpoint)
    assert freeze_study(destination, tasks(), trajectories(), checkpoint) == original
    changed = deepcopy(checkpoint)
    changed["model_config"] = {"test": "changed"}
    with pytest.raises(ValueError, match="different bytes"):
        freeze_study(destination, tasks(), trajectories(), changed)
