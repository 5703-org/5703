"""Freeze and blind-review integrity for the practice-feedback addendum."""

import csv
import json
from pathlib import Path

import pytest

from evaluation.week09_continuation.practice_feedback_formal import load_catalogue
from evaluation.week09_continuation.practice_feedback_review import (
    REVIEW_FIELDS,
    import_ratings,
)


def case(identity: str, split: str, group: str) -> dict:
    locator = {"release_id": "release", "document_id": "book", "source_unit_id": "unit"}
    return {
        "id": identity,
        "family": "practice_feedback",
        "split": split,
        "concept_group": group,
        "source": {
            "title": "Biology 2e",
            "physical_pdf_page": 12,
            "support_quote": "source fact",
            "locator": locator,
        },
        "draft": {"kind": "mcq", "source": locator},
        "attempts": [
            {"response": {"selection": ["B"]}, "expected_rule_outcome": "incorrect"},
            {"response": {"selection": ["A"]}, "expected_rule_outcome": "correct"},
        ],
    }


def test_practice_freeze_rejects_concept_leakage_and_source_mismatch(tmp_path: Path):
    path = tmp_path / "catalogue.json"
    payload = {
        "schema": "week09_practice_feedback_catalogue_v1",
        "cases": [case("p", "pilot", "shared"), case("r", "reserved", "shared")],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="crosses pilot and reserved"):
        load_catalogue(path)
    payload["cases"][1]["concept_group"] = "new"
    payload["cases"][1]["draft"]["source"] = {"wrong": "source"}
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Practice source or kind"):
        load_catalogue(path)


def test_blank_review_import_stays_unscored_and_source_edit_is_rejected(tmp_path: Path):
    materials = tmp_path / "materials"
    materials.mkdir()
    review_id = "case-1"
    (materials / "coordinator-key.json").write_text(
        json.dumps({"rows": [{"review_id": review_id}]}), encoding="utf-8"
    )
    row = {field: "" for field in REVIEW_FIELDS}
    row.update(
        {
            "review_id": review_id,
            "source_title": "Biology 2e",
            "item_prompt": "What is osmosis?",
            "source_text": "Official passage",
        }
    )
    template = materials / "reviewer-A-blank.csv"
    with template.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    result = import_ratings(materials, template, "reviewer A", tmp_path / "blank-import.json")
    assert result["scheduled_rows"] == 1 and result["completed_rows"] == 0

    changed = tmp_path / "changed.csv"
    with changed.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerow({**row, "source_text": "Altered evidence"})
    with pytest.raises(ValueError, match="changed during review"):
        import_ratings(materials, changed, "reviewer A", tmp_path / "bad-import.json")
