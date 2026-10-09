"""Rule-derived grids, false-positive boundaries and strict continuation checks."""

import copy

import pymupdf
import pytest

from pipelines.native_tables_v1 import (
    continuation_compatible,
    match_caption_grid,
    recover_native_grids,
)
from pipelines.visual_regions import extract_page_regions as extract_legacy
from pipelines.visual_regions_v3 import extract_page_regions


def _grid(page, *, x=60, y=100, scale=1, words=True, vertical=True, end_row=3):
    xs = [x, x + 80 * scale, x + 200 * scale]
    ys = [y + number * 30 * scale for number in range(4)]
    for value in ys:
        page.draw_rect(
            pymupdf.Rect(xs[0], value, xs[-1], value + 0.4 * scale), color=None, fill=(0, 0, 0)
        )
    if vertical:
        page.draw_line((xs[1], ys[1]), (xs[1], ys[end_row]), color=(0, 0, 0), width=0.25)
    if words:
        for row, entries in enumerate(
            [("Name", "Meaning"), ("Alpha", "First item"), ("Beta", "Second item")]
        ):
            for col, value in enumerate(entries):
                page.insert_text(
                    (xs[col] + 5 * scale, ys[row] + 20 * scale), value, fontsize=10 * scale
                )
    return xs, ys


@pytest.mark.parametrize("x,y,scale", [(40, 60, 0.8), (140, 210, 1.3)])
def test_native_fill_rules_recover_translated_scaled_open_borders(x, y, scale):
    with pymupdf.open() as doc:
        page = doc.new_page()
        _grid(page, x=x, y=y, scale=scale)
        grids = recover_native_grids(page)
    assert len(grids) == 1
    grid = grids[0]
    assert (grid["rows"], grid["columns"]) == (3, 2)
    assert grid["cells"][1] == ["Alpha", "First item"]
    assert grid["native_words_assigned_exactly_once"]
    assert grid["status"] == "needs_structure_review"
    assert grid["semantic_quality"] is None and not grid["answer_evidence_eligible"]


@pytest.mark.parametrize(
    "words,vertical,end_row", [(False, True, 3), (True, False, 3), (True, True, 2)]
)
def test_empty_decoration_unpartitioned_text_and_partial_vertical_are_not_grids(
    words, vertical, end_row
):
    with pymupdf.open() as doc:
        page = doc.new_page()
        _grid(page, words=words, vertical=vertical, end_row=end_row)
        assert recover_native_grids(page) == []


def test_distinct_same_width_tables_keep_separate_rows_and_caption_binding():
    with pymupdf.open() as doc:
        page = doc.new_page()
        _grid(page, y=90)
        _grid(page, y=400)
        grids = recover_native_grids(page)
    assert len(grids) == 2
    assert [grid["rows"] for grid in grids] == [3, 3]
    assert match_caption_grid([60, 183, 150, 197], grids) == grids[0]
    assert match_caption_grid([60, 20, 150, 34], grids) == grids[0]
    assert match_caption_grid([500, 180, 550, 200], grids) is None
    assert match_caption_grid([60, 700, 150, 714], grids) is None


def test_glyph_subscript_native_baselines_and_raw_text_are_retained():
    with pymupdf.open() as doc:
        page = doc.new_page()
        _grid(page, words=False)
        for point, text, size in [
            ((65, 120), "Formula", 10),
            ((145, 120), "Name", 10),
            ((65, 150), "H", 10),
            ((72.5, 152), "2", 7),
            ((78, 150), "O", 10),
            ((145, 150), "Water", 10),
            ((65, 180), "N", 10),
            ((145, 180), "Other", 10),
        ]:
            page.insert_text(point, text, fontsize=size)
        grid = recover_native_grids(page)[0]
    cell = next(
        cell
        for cell in grid["cells_with_native_layout"]
        if cell["row"] == 1 and cell["column"] == 0
    )
    assert cell["position_ordered_text_candidate"].replace(" ", "") == "H2O"
    assert len({glyph["origin_points"][1] for glyph in cell["native_glyphs"]}) == 2
    assert {glyph["font_size"] for glyph in cell["native_glyphs"]} == {7, 10}
    assert cell["raw_table_extract_text"] == grid["cells"][1][0]


def _fragment(page, label="Table 7.1", header=None, width=200):
    return {
        "source_sha256": "a" * 64,
        "physical_pdf_page": page,
        "bbox_points": [60, 700 if page == 1 else 100, 60 + width, 780 if page == 1 else 200],
        "details": {
            "label": label,
            "columns": 2,
            "cells": [header or ["Name", "Meaning"], ["A", "B"]],
            "x_boundaries_points": [60, 60 + width * 0.4, 60 + width],
            "page_size_points": [612, 792],
        },
    }


def test_continuation_requires_source_adjacency_label_header_width_and_column_alignment():
    first, second = _fragment(1), _fragment(2)
    assert continuation_compatible(first, second)
    variants = []
    for key, value in [("physical_pdf_page", 3), ("source_sha256", "b" * 64)]:
        variant = copy.deepcopy(second)
        variant[key] = value
        variants.append(variant)
    variants.extend(
        [
            _fragment(2, label="Table 7.2"),
            _fragment(2, header=["Different", "Meaning"]),
            _fragment(2, width=250),
        ]
    )
    variant = copy.deepcopy(second)
    variant["details"]["x_boundaries_points"][1] += 30
    variants.append(variant)
    variant = copy.deepcopy(second)
    variant["details"]["page_size_points"][1] += 100
    variants.append(variant)
    variant = copy.deepcopy(second)
    variant["bbox_points"][1] = 300
    variants.append(variant)
    assert all(not continuation_compatible(first, variant) for variant in variants)


def test_explicit_successor_keeps_legacy_bytes_and_new_unapproved_identity():
    with pymupdf.open() as doc:
        page = doc.new_page()
        _grid(page)
        page.insert_text((60, 208), "TABLE 7.1 Values")
        args = {"source_sha256": "a" * 64, "book": "Authored fixture", "physical_page": 1}
        legacy_before = extract_legacy(page, **args)
        current = extract_page_regions(page, **args)
        assert extract_legacy(page, **args) == legacy_before
    assert len(current) == len(legacy_before)
    table = next(row for row in current if row["kind"] == "table_candidate")
    old = next(row for row in legacy_before if row["kind"] == "table_candidate")
    assert table["extractor_revision"] == "pymupdf_visual_regions_v3"
    assert table["details"]["previous_region_id"] == old["region_id"]
    assert table["region_id"] != old["region_id"]
    assert table["details"]["cells"][1] == ["Alpha", "First item"]
    assert table["status"] == "needs_structure_review"
    assert not table["details"]["answer_evidence_eligible"]


def test_actual_page_successor_continuation_links_preserve_each_fragment_header():
    with pymupdf.open() as doc:
        first = doc.new_page(width=612, height=792)
        _grid(first, y=660)
        first.insert_text((60, 768), "TABLE 7.1 Values")
        second = doc.new_page(width=612, height=792)
        _grid(second, y=90)
        second.insert_text((60, 198), "TABLE 7.1 Values")
        rows = extract_page_regions(
            doc[0], source_sha256="a" * 64, book="Authored fixture", physical_page=1
        )
        table = next(row for row in rows if row["kind"] == "table_candidate")
        links = table["details"]["continuation_candidates"]
    assert len(links) == 1 and links[0]["physical_pdf_page"] == 2
    assert links[0]["cells"][0] == table["details"]["cells"][0]
    assert not links[0]["answer_evidence_eligible"]
