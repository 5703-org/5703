"""Synthetic review-form tests; no project evidence or actual ratings are changed."""

import copy
import csv
import json
import pytest
from evaluation.week09.review import export, import_reviews
from tests.unit.test_week09_review import example


def forms(folder, names):
    paths = []
    for number, reviewer_names in enumerate(names, 1):
        path = folder / f"reviewer-{number}/ratings.csv"
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        for row, name in zip(rows, reviewer_names, strict=True):
            row.update(
                reviewer_name=name,
                publication_appropriate="yes",
                reason="Authored unit fixture only.",
            )
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        paths.append(path)
    return paths


def records():
    first, second = example(), example()
    second["schedule"]["id"] = "dev-2"
    return [first, second]


def test_boundary_uses_same_request_constraints_across_arms(tmp_path):
    rows = records()
    for number, row in enumerate(rows):
        row["request"].update(
            generation_policy={"arm": ["A", "D"][number]}, teaching_condition="T2"
        )
        row["request"]["teaching_context"].update(
            current_step=2, help_level=2, task_type="process_reasoning"
        )
    folder = tmp_path / "review"
    export(rows, [], folder)
    packets = json.loads((folder / "reviewer-1/packets.json").read_text())["packets"]
    assert all(p["current_step"] == 2 for p in packets)
    assert packets[0]["allowed_disclosure"] == packets[1]["allowed_disclosure"]
    assert "one next causal link" in packets[0]["allowed_disclosure"]["constraint"]
    assert all("generation_policy" not in p for p in packets)


@pytest.mark.parametrize(
    "name", ["reviewer-1/packets.json", "reviewer-2/review.html", "coordinator-only/mapping.json"]
)
def test_changed_evidence_or_mapping_rejects_scores(tmp_path, name):
    folder = tmp_path / "review"
    export([example()], [], folder)
    path = folder / name
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="integrity"):
        import_reviews(folder, [folder / "reviewer-1/ratings.csv"])


def test_blank_forms_remain_valid_and_missing(tmp_path):
    folder = tmp_path / "review"
    export([example()], [], folder)
    result = import_reviews(
        folder, [folder / "reviewer-1/ratings.csv", folder / "reviewer-2/ratings.csv"]
    )
    assert result["scored_rows"] == 0 and result["false_block_rate"] is None


def test_mixed_names_in_one_scored_form_rejected(tmp_path):
    folder = tmp_path / "review"
    export(records(), [], folder)
    with pytest.raises(ValueError, match="one stable"):
        import_reviews(folder, forms(folder, [["Unit Reviewer One", "Unit Reviewer Two"]]))


def test_same_normalized_name_cannot_fill_both_independent_forms(tmp_path):
    folder = tmp_path / "review"
    export(records(), [], folder)
    with pytest.raises(ValueError, match="distinct"):
        import_reviews(
            folder,
            forms(
                folder, [["Unit Reviewer", "Unit Reviewer"], [" unit   reviewer ", "UNIT REVIEWER"]]
            ),
        )


def test_two_distinct_stable_names_preserve_rating_denominators(tmp_path):
    folder = tmp_path / "review"
    export(records(), [], folder)
    result = import_reviews(
        folder, forms(folder, [["Unit Reviewer One"] * 2, ["Unit Reviewer Two"] * 2])
    )
    assert result["scored_rows"] == 4 and result["human_publishable_ratings"] == 4
    assert result["false_block_rate"] == 1.0
