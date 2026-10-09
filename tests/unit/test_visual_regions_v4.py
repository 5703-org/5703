"""Pure PDF fixtures for opt-in V4 source and reference boundaries."""

from __future__ import annotations

import copy

import pymupdf
import pytest

from pipelines import visual_regions
from pipelines.native_tables_v1 import recover_native_grids
from pipelines.native_tables_v2 import recover_caption_bounded_grid, recover_unruled_single_column
from pipelines.visual_candidate_boundaries import (
    is_inline_reference,
    rectangular_table_body,
    validate_reference_record,
    validate_reference_targets,
)
from pipelines.visual_regions_v4 import extract_page_regions, _source_table_caption
from pipelines.visual_regions_v3 import extract_page_regions as v3_extract
from pipelines.visual_candidate_boundaries import validate_v3_parent_lineage


def _caption(page):
    return next(
        line["bbox"] for line in visual_regions._text_lines(page) if line["text"] == "TABLE 9.9"
    )


def _ruled(
    page,
    *,
    partial=False,
    callout=True,
    descriptive=False,
    caption_label="TABLE 9.9",
    caption_y=225,
):
    for y in (120, 150, 180, 210):
        page.draw_line((72, y), (540, y), width=0.6)
    page.draw_line((240, 150), (240, 178 if partial else 210), width=0.6)
    for y, left, right in ((140, "H1", "H2"), (170, "A", "B"), (200, "C", "D")):
        page.insert_text((90, y), left, fontsize=9)
        page.insert_text((260, y), right, fontsize=9)
    if descriptive:
        page.insert_text(
            (72, caption_y), caption_label, fontsize=7.5, fontname="hebo", color=(1, 0, 0)
        )
        page.insert_text((115, caption_y), " Synthetic descriptive caption.", fontsize=7.5)
    else:
        page.insert_text((72, caption_y), caption_label, fontsize=7.5)
    if callout:
        page.draw_line((72, 242), (540, 242), width=0.6)
        page.draw_line((72, 242), (72, 330), width=0.6)
        page.draw_line((540, 242), (540, 330), width=0.6)
        page.insert_text((90, 268), "Separate callout", fontsize=10)


def test_caption_barrier_excludes_separate_callout_without_weakening_grid_checks():
    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        _ruled(page)
        assert recover_native_grids(page) == []
        candidate = recover_caption_bounded_grid(page, list(_caption(page)))
        assert candidate is not None
        assert (candidate["rows"], candidate["columns"]) == (3, 2)
        assert candidate["cells"] == [["H1", "H2"], ["A", "B"], ["C", "D"]]
        assert candidate["native_rule_scope"]["native_paths_clipped_or_invented"] is False
        assert candidate["answer_evidence_eligible"] is False
        assert "Separate callout" not in str(candidate["cells"])


def test_caption_barrier_still_rejects_partial_interior_vertical_rule():
    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        _ruled(page, partial=True)
        assert recover_caption_bounded_grid(page, list(_caption(page))) is None


def _unruled(page, *, styled_heading=True):
    if styled_heading:
        page.insert_text((215, 180), "List heading", fontsize=9, color=(0, 0.5, 0.7))
    for i, value in enumerate(("Alpha value", "Beta value", "Gamma value")):
        page.insert_text((210, 200 + i * 12.6), value, fontsize=9)
    page.insert_text((210, 245), "TABLE 9.9", fontsize=7.5)


def test_unruled_single_column_preserves_body_and_separate_heading():
    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        _unruled(page)
        candidate = recover_unruled_single_column(page, list(_caption(page)))
        assert candidate is not None
        assert candidate["cells"] == [["Alpha value"], ["Beta value"], ["Gamma value"]]
        assert candidate["heading_candidate"]["native_text"] == "List heading"
        assert candidate["header_row_verified"] is False
        assert candidate["native_words_assigned_exactly_once"] is True
        assert candidate["native_glyphs_assigned_exactly_once"] is True
        assert all(
            cell["raw_table_extract_text"] is None for cell in candidate["cells_with_native_layout"]
        )


def test_unruled_paragraph_without_separate_heading_remains_unresolved():
    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        _unruled(page, styled_heading=False)
        assert recover_unruled_single_column(page, list(_caption(page))) is None


def _reference_fixture():
    document = pymupdf.open()
    source = document.new_page(width=612, height=792)
    document.new_page(width=612, height=792)
    source = document[0]
    source.insert_text(
        (72, 200), "Table 9.9 describes the example data.", fontsize=9, color=(0, 0.5, 0.7)
    )
    source.insert_link(
        {
            "kind": pymupdf.LINK_GOTO,
            "from": pymupdf.Rect(72, 189, 114, 204),
            "page": 1,
            "to": pymupdf.Point(0, 120),
        }
    )
    _ruled(document[1], callout=False)
    # Reload from native PDF bytes so link destinations reflect saved PDF state.
    data = document.tobytes()
    document.close()
    return pymupdf.open(stream=data, filetype="pdf")


def _reference_records():
    with _reference_fixture() as document:
        source = extract_page_regions(
            document[0], source_sha256="a" * 64, book="Fixture", physical_page=1
        )
        target = extract_page_regions(
            document[1], source_sha256="a" * 64, book="Fixture", physical_page=2
        )
    reference = next(item for item in source if is_inline_reference(item))
    return reference, target


def test_pdf_link_keeps_reference_page_separate_from_target_table():
    reference, target = _reference_records()
    assert reference["physical_pdf_page"] == 1
    assert reference["details"]["reference_target_locator"]["physical_pdf_page"] == 2
    assert reference["details"]["cells"] is None
    assert not rectangular_table_body(reference)
    assert reference["details"]["previous_extractor_revision"] == visual_regions.EXTRACTOR_REVISION
    assert (
        reference["details"]["previous_candidate_extractor_revision"] == "pymupdf_visual_regions_v3"
    )
    validate_reference_record(reference, physical_pages=2)
    validate_reference_targets([reference, *target])


def test_reference_consumer_rejects_cells_impersonating_source_page():
    reference, _ = _reference_records()
    reference["details"].update(rows=1, columns=1, cells=[["Target text"]])
    assert not rectangular_table_body(reference)
    with pytest.raises(ValueError, match="target cells"):
        validate_reference_record(reference, physical_pages=2)


def test_same_page_pdf_link_still_binds_a_distinct_table_region():
    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        page.insert_text((72, 90), "Table 9.9 describes the example data.", fontsize=9)
        _ruled(page, callout=False)
        page.insert_link(
            {
                "kind": pymupdf.LINK_GOTO,
                "from": pymupdf.Rect(72, 79, 114, 94),
                "page": 0,
                "to": pymupdf.Point(0, 120),
            }
        )
        data = document.tobytes()
    with pymupdf.open(stream=data, filetype="pdf") as document:
        records = extract_page_regions(
            document[0], source_sha256="a" * 64, book="Fixture", physical_page=1
        )
    reference = next(item for item in records if is_inline_reference(item))
    assert reference["details"]["reference_resolution_state"] == "linked_candidate"
    locator = reference["details"]["reference_target_locator"]
    assert locator["physical_pdf_page"] == reference["physical_pdf_page"] == 1
    assert locator["bbox_points"] != reference["bbox_points"]
    assert locator["target_previous_region_id"] != reference["details"]["previous_region_id"]
    assert reference["details"]["cells"] is None
    validate_reference_record(reference, physical_pages=1)
    validate_reference_targets(records)


@pytest.mark.parametrize(
    "field,value",
    [("physical_pdf_page", 1), ("source_sha256", "b" * 64), ("target_candidate_region_id", "bad")],
)
def test_reference_consumer_rejects_invalid_target_locator(field, value):
    reference, _ = _reference_records()
    reference["details"]["reference_target_locator"][field] = value
    with pytest.raises(ValueError):
        validate_reference_record(reference, physical_pages=2)


def test_reference_consumer_rejects_missing_or_mismatched_catalog_target():
    reference, targets = _reference_records()
    with pytest.raises(ValueError, match="distinct matching"):
        validate_reference_targets([reference])
    tampered = copy.deepcopy(targets)
    next(item for item in tampered if item["kind"] == "table_candidate")["physical_pdf_page"] = 1
    with pytest.raises(ValueError, match="distinct matching"):
        validate_reference_targets([reference, *tampered])


def test_wrong_physical_page_argument_is_rejected():
    with _reference_fixture() as document:
        with pytest.raises(ValueError, match="physical locator"):
            extract_page_regions(
                document[0], source_sha256="a" * 64, book="Fixture", physical_page=2
            )


def test_consumer_rejects_source_bbox_outside_native_page():
    reference, _ = _reference_records()
    reference["bbox_points"][2] = 700
    reference["details"]["source_reference_bbox_points"] = list(reference["bbox_points"])
    with pytest.raises(ValueError, match="source geometry"):
        validate_reference_record(reference, physical_pages=2)


def test_consumer_rejects_native_point_outside_target_page():
    reference, _ = _reference_records()
    reference["details"]["native_pdf_link"]["target_point_points"] = [700, 900]
    with pytest.raises(ValueError, match="destination point"):
        validate_reference_record(reference, physical_pages=2)


def test_consumer_retains_page_label_association_without_claiming_point_containment():
    reference, _ = _reference_records()
    reference["details"]["native_pdf_link"]["target_point_points"] = [600, 780]
    validate_reference_record(reference, physical_pages=2)
    locator = reference["details"]["reference_target_locator"]
    assert locator["destination_point_table_containment_verified"] is False
    assert locator["semantic_association_verified"] is False


def test_v4_rectangular_body_rejects_non_text_cells_and_retains_native_nulls():
    item = {
        "extractor_revision": "pymupdf_visual_regions_v4",
        "kind": "table_candidate",
        "details": {
            "record_role": "table_body_candidate",
            "rows": 1,
            "columns": 1,
            "cells": [[{"invented": "text"}]],
        },
    }
    assert not rectangular_table_body(item)
    item["details"]["cells"] = [[None]]
    assert rectangular_table_body(item)


def test_descriptive_footer_requires_complete_native_body_and_caption_style():
    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        _ruled(page, callout=False, descriptive=True)
        target = next(
            item
            for item in v3_extract(page, source_sha256="a" * 64, book="Fixture", physical_page=1)
            if item["kind"] == "table_candidate"
        )
        assert _source_table_caption(page, target)
        no_body = copy.deepcopy(target)
        no_body["details"]["cells_with_native_layout"] = []
        assert not _source_table_caption(page, no_body)


def test_descriptive_footer_rejects_prefixed_label_collision_and_paragraph_position():
    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        _ruled(page, callout=False, descriptive=True, caption_label="TABLE 9.90")
        target = next(
            item
            for item in v3_extract(page, source_sha256="a" * 64, book="Fixture", physical_page=1)
            if item["kind"] == "table_candidate"
        )
        target["details"]["label"] = "Table 9.9"
        assert not _source_table_caption(page, target)
    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        _ruled(page, callout=False, descriptive=True, caption_y=90)
        target = next(
            item
            for item in v3_extract(page, source_sha256="a" * 64, book="Fixture", physical_page=1)
            if item["kind"] == "table_candidate"
        )
        assert not _source_table_caption(page, target)


def test_descriptive_footer_rejects_linked_caption():
    with pymupdf.open() as document:
        document.new_page(width=612, height=792)
        document.new_page(width=612, height=792)
        page = document[0]
        _ruled(page, callout=False, descriptive=True)
        page.insert_link(
            {
                "kind": pymupdf.LINK_GOTO,
                "from": pymupdf.Rect(72, 215, 115, 230),
                "page": 1,
                "to": pymupdf.Point(0, 120),
            }
        )
        data = document.tobytes()
    with pymupdf.open(stream=data, filetype="pdf") as document:
        page = document[0]
        target = next(
            item
            for item in v3_extract(page, source_sha256="a" * 64, book="Fixture", physical_page=1)
            if item["kind"] == "table_candidate"
        )
        assert not _source_table_caption(page, target)


def test_exact_parent_sidecar_rejects_forged_v3_claim_or_source_page():
    with _reference_fixture() as document:
        parents = [
            item
            for index in (0, 1)
            for item in v3_extract(
                document[index], source_sha256="a" * 64, book="Fixture", physical_page=index + 1
            )
        ]
        current = [
            item
            for index in (0, 1)
            for item in extract_page_regions(
                document[index], source_sha256="a" * 64, book="Fixture", physical_page=index + 1
            )
        ]
    validate_v3_parent_lineage(current, parents)
    changed = copy.deepcopy(current)
    changed[0]["details"]["previous_candidate_region_id"] = "b" * 64
    with pytest.raises(ValueError, match="one-to-one"):
        validate_v3_parent_lineage(changed, parents)
    changed = copy.deepcopy(current)
    changed[0]["physical_pdf_page"] = 2
    with pytest.raises(ValueError, match="source, page"):
        validate_v3_parent_lineage(changed, parents)
    with pytest.raises(ValueError, match="one-to-one"):
        validate_v3_parent_lineage(current, [*parents, parents[0]])
