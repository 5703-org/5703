"""Authored import-only fixtures; no real human ratings are created."""

import csv
import json
import pytest
from scripts.verify import week09_memory_reviews as review


def setup(tmp_path):
    review.write(tmp_path / "review-packets.json", [{"review_id": "MR-001"}])
    review.write(
        tmp_path / "coordinator-only/mapping.json",
        {
            "MR-001": {
                "case_id": "authored-unit-fixture",
                "arm": "rules",
                "selected": False,
                "delivery_status": "unavailable",
            },
        },
    )
    review.write(
        tmp_path / "coordinator-only/manifest.json",
        {
            "packets_sha256": review.sha(tmp_path / "review-packets.json"),
            "mapping_sha256": review.sha(tmp_path / "coordinator-only/mapping.json"),
        },
    )
    return tmp_path / "ratings.csv", tmp_path / "result.json"


def form(path, **value):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=review.FIELDS)
        writer.writeheader()
        writer.writerow({"review_id": "MR-001", **value})


def test_blank_import_remains_missing(tmp_path):
    path, result = setup(tmp_path)
    form(path)
    review.import_reviews(tmp_path, [path], result)
    data = json.loads(result.read_text())
    assert data["human_ratings"] == 0
    assert data["arms"]["rules"]["compliance_mean"] is None


def test_missing_answer_cannot_receive_compliance_score(tmp_path):
    path, result = setup(tmp_path)
    form(path, reviewer_id="authored-test-reviewer", preference_followed="1")
    with pytest.raises(ValueError, match="unavailable"):
        review.import_reviews(tmp_path, [path], result)


def test_duplicate_reviewer_and_item_rejected(tmp_path):
    path, result = setup(tmp_path)
    form(path, reviewer_id="authored-test-reviewer", preference_followed="NA")
    with pytest.raises(ValueError, match="unique"):
        review.import_reviews(tmp_path, [path, path], result)


def test_whitespace_is_normalized_before_aggregation(tmp_path):
    path, result = setup(tmp_path)
    form(
        path,
        reviewer_id="authored-test-reviewer",
        preference_applicable=" 1 ",
        preference_followed=" NA ",
    )
    review.import_reviews(tmp_path, [path], result)
    assert json.loads(result.read_text())["arms"]["rules"]["omission_ratings"] == 1


def test_changed_packet_rejected(tmp_path):
    path, result = setup(tmp_path)
    form(path)
    review.write(tmp_path / "review-packets.json", [])
    with pytest.raises(AssertionError):
        review.import_reviews(tmp_path, [path], result)
