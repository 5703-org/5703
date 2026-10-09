"""Failure-boundary checks for the frozen visual-source evaluation."""

from __future__ import annotations

import csv
import json
from unittest.mock import Mock

import pymupdf
import pytest

from evaluation.week09_continuation import visual_formal


def test_frozen_visual_selection_rejects_a_pretend_human_label(tmp_path, monkeypatch):
    """Authored fixtures exercise label rejection, not actual corpus qualification."""
    review_fields = (
        "reviewer_id",
        "original_page_match",
        "structure_correct",
        "caption_or_symbol_correct",
        "notes",
    )
    rows = [
        {"region_id": f"authored-region-{index:03d}", **dict.fromkeys(review_fields, "")}
        for index in range(120)
    ]
    rows[0]["structure_correct"] = "yes"
    edited = tmp_path / "authored-review.csv"
    with edited.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=("region_id", *review_fields))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "scope": "full_originals",
        "books": [
            {
                "slug": f"authored-book-{index}",
                "source_path": f"authored-book-{index}.pdf",
                "source_sha256": "0" * 64,
            }
            for index in range(4)
        ],
    }
    current = tmp_path / "authored-current.json"
    previous = tmp_path / "authored-previous.json"
    for path in (current, previous):
        path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(visual_formal, "REVIEW", edited)
    monkeypatch.setattr(visual_formal, "CURRENT", current)
    monkeypatch.setattr(visual_formal, "PREVIOUS", previous)
    catalog_access = Mock(side_effect=AssertionError("Catalog access before label rejection"))
    source_hash_access = Mock(side_effect=AssertionError("PDF hash access before label rejection"))
    pdf_open = Mock(side_effect=AssertionError("PDF open before label rejection"))
    monkeypatch.setattr(visual_formal, "_catalog", catalog_access)
    monkeypatch.setattr(visual_formal, "sha256", source_hash_access)
    monkeypatch.setattr(visual_formal.pymupdf, "open", pdf_open)
    output = tmp_path / "freeze"
    with pytest.raises(ValueError, match="entirely unlabeled"):
        visual_formal.freeze(output)
    catalog_access.assert_not_called()
    source_hash_access.assert_not_called()
    pdf_open.assert_not_called()
    assert not output.exists()


def test_paired_visual_comparison_requires_the_same_region_identity():
    current = {
        "physical_pdf_page": 7,
        "kind": "figure_image",
        "native_text": "Figure 2.1",
        "details": {"image_md5": "aaa"},
        "bbox_points": [1, 2, 3, 4],
        "region_id": "new",
    }
    other = {**current, "details": {"image_md5": "bbb"}, "region_id": "old"}
    with pytest.raises(ValueError, match="No old-region counterpart"):
        visual_formal._closest(current, [other])


def test_visual_table_shape_does_not_certify_unreconstructed_or_invalid_cells():
    unresolved = {"kind": "table_candidate", "details": {"cells": None}}
    assert visual_formal._table_shape(unresolved)["shape_consistent"] is None
    inconsistent = {
        "kind": "table_candidate",
        "details": {"cells": [["a"], ["b", "c"]], "rows": 2, "columns": 2},
    }
    assert visual_formal._table_shape(inconsistent)["shape_consistent"] is False


def test_visual_locator_detects_old_off_page_rectangle():
    pdf = pymupdf.open()
    page = pdf.new_page(width=100, height=100)
    page.insert_text((10, 20), "E = mc2")
    case = {
        "kind": "formula_candidate",
        "bbox": [5, 5, 80, 30],
        "prior_bbox": [5, 5, 120, 30],
        "native_text": "E = mc2",
    }
    checked = visual_formal._geometry(page, case)
    assert checked["candidate_inside_visible_page"] is True
    assert checked["previous_inside_visible_page"] is False
    assert checked["native_text_exact_line_recovered"] is True
    pdf.close()
