"""Actual-score import revisions, independent adjudication and portable inputs."""

import csv
from datetime import datetime, timezone

import pytest

from evaluation.enhancement.protocol import RUBRIC_VERSION, freeze
from evaluation.enhancement.review import (
    FIELDS,
    SCORES,
    agreement,
    import_adjudication,
    import_review,
)
from evaluation.enhancement.runner import resolve_source


def ratings(path, reviewer, items):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for identity, supported in items:
            writer.writerow(
                {
                    "review_id": identity,
                    "reviewer_id": reviewer,
                    "rubric_version": RUBRIC_VERSION,
                    **dict.fromkeys(SCORES, "1"),
                    "supported": str(supported),
                    "reason": "Synthetic import test only",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            )


def test_partial_revision_preserves_other_scores_and_separate_adjudication(tmp_path):
    freeze(
        tmp_path / "coordinator-only-condition-key.json",
        {"items": [{"review_id": "a"}, {"review_id": "b"}]},
    )
    first, second, revised, decisions = [
        tmp_path / (n + ".csv") for n in ("one", "two", "revised", "decisions")
    ]
    ratings(first, "alice", [("a", 1), ("b", 1)])
    original = import_review(tmp_path, first, "alice")
    from pathlib import Path

    original_bytes = Path(original["artifact"]).read_bytes()
    ratings(second, "bob", [("a", 0), ("b", 1)])
    import_review(tmp_path, second, "bob")
    ratings(revised, "alice", [("b", 0)])
    import_review(tmp_path, revised, "alice")
    state = agreement(tmp_path)
    assert state["actual_ratings"] == 4
    assert state["agreement"]["supported"]["paired"] == 2
    assert len(state["disagreements"]) == 2
    ratings(decisions, "chair", [("a", 1)])
    import_adjudication(tmp_path, decisions, "chair")
    after = agreement(tmp_path)
    assert after["agreement"] == state["agreement"]
    assert len(after["adjudication"]) == 1
    assert Path(original["artifact"]).read_bytes() == original_bytes
    with pytest.raises(ValueError, match="Two independent"):
        import_review(tmp_path, decisions, "chair")


def test_portable_research_source_must_match_original_frozen_hash(tmp_path):
    source = tmp_path / "formal-source-v1"
    expected = freeze(source / "manifest.json", {"dataset": "authored fixture"})
    run = tmp_path / "formal-hints-v1"
    manifest = {
        "source_directory": str(tmp_path / "absent" / source.name),
        "source_manifest_sha256": expected["content_sha256"],
    }
    assert resolve_source(run, manifest) == source
    manifest["source_manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Matching frozen"):
        resolve_source(run, manifest)
