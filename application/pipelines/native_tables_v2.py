"""Conservative caption-bounded and unruled native table candidates.

These helpers do not approve source content. Coordinates, cells and glyphs come
from the current PDF; no textbook/page dictionary or expected row count is used.
"""

from __future__ import annotations

import copy
from statistics import median

import pymupdf

from pipelines.native_tables_v1 import (
    RECOVERY_CONFIGURATION as RULED_CONFIGURATION,
    _inside,
    _position_text,
    match_caption_grid,
    native_glyphs,
    recover_native_grids,
)

TABLE_RECOVERY_REVISION = "native_caption_bounded_tables_v2"
RECOVERY_CONFIGURATION = {
    **RULED_CONFIGURATION,
    "minimum_unruled_body_lines": 3,
    "maximum_unruled_width_fraction": 0.55,
    "maximum_unruled_gap_relative_deviation": 0.15,
    "maximum_unruled_caption_gap_points": 20.0,
    "maximum_unruled_heading_gap_points": 25.0,
}


class _CaptionBoundedPage:
    """Retain entire native drawing paths above a footer caption, never clip them."""

    def __init__(self, page: pymupdf.Page, caption_top: float):
        self.page = page
        self.caption_top = caption_top

    def __getattr__(self, name):
        return getattr(self.page, name)

    def get_drawings(self):
        tolerance = RECOVERY_CONFIGURATION["coordinate_tolerance_points"]
        return [
            drawing
            for drawing in self.page.get_drawings()
            if drawing["rect"].y1 < self.caption_top - tolerance
        ]


def recover_caption_bounded_grid(page: pymupdf.Page, caption_bbox: list) -> dict | None:
    """Use a real footer caption as a barrier between a table and lower callouts."""
    proxy = _CaptionBoundedPage(page, caption_bbox[1])
    grids = recover_native_grids(proxy)
    recovered = match_caption_grid(caption_bbox, grids)
    if recovered is None or recovered["bbox_points"][3] >= caption_bbox[1]:
        return None
    result = copy.deepcopy(recovered)
    result["recovery_revision"] = TABLE_RECOVERY_REVISION
    result["structure_role"] = "caption_bounded_ruled_table"
    result["native_rule_scope"] = {
        "caption_bbox_points": list(caption_bbox),
        "policy": "Only complete native drawing paths strictly above the source footer caption; V1 partial-grid, coverage, shape and word-conservation checks remain intact.",
        "native_paths_clipped_or_invented": False,
    }
    return result


def _text(line: dict) -> str:
    return "".join(span["text"] for span in line.get("spans", [])).strip()


def _styles(lines: list[dict]) -> set[tuple]:
    return {
        (round(span["size"], 3), span["font"], span["flags"], span["color"])
        for line in lines
        for span in line.get("spans", [])
        if span.get("text", "").strip()
    }


def recover_unruled_single_column(page: pymupdf.Page, caption_bbox: list) -> dict | None:
    """Require one narrow block, consistent lines and a separate styled heading."""
    c = RECOVERY_CONFIGURATION
    tolerance = c["coordinate_tolerance_points"]
    flags = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    blocks = [
        block for block in page.get_text("dict", flags=flags)["blocks"] if block.get("type") == 0
    ]
    preceding = [
        block
        for block in blocks
        if 0 <= caption_bbox[1] - block["bbox"][3] <= c["maximum_unruled_caption_gap_points"]
        and block["bbox"][0] <= caption_bbox[0] + tolerance
        and block["bbox"][2] >= caption_bbox[2] - tolerance
    ]
    if len(preceding) != 1:
        return None
    body = preceding[0]
    lines = body.get("lines", [])
    if not c["minimum_unruled_body_lines"] <= len(lines) <= c["maximum_rows"]:
        return None
    if any(not _text(line) for line in lines) or len(_styles(lines)) != 1:
        return None
    if any(abs(line["bbox"][0] - body["bbox"][0]) > tolerance for line in lines):
        return None
    width = body["bbox"][2] - body["bbox"][0]
    if width <= 0 or width > page.rect.width * c["maximum_unruled_width_fraction"]:
        return None
    baselines = [line["spans"][0]["origin"][1] for line in lines]
    gaps = [b - a for a, b in zip(baselines, baselines[1:])]
    typical_gap = median(gaps)
    if typical_gap <= 0 or any(
        abs(gap - typical_gap) > typical_gap * c["maximum_unruled_gap_relative_deviation"]
        for gap in gaps
    ):
        return None
    headings = [
        block
        for block in blocks
        if len(block.get("lines", [])) == 1
        and 0 <= body["bbox"][1] - block["bbox"][3] <= c["maximum_unruled_heading_gap_points"]
        and body["bbox"][0] - tolerance
        <= block["bbox"][0]
        < block["bbox"][2]
        <= body["bbox"][2] + tolerance
        and _styles(block["lines"]) != _styles(lines)
    ]
    if len(headings) != 1 or not _text(headings[0]["lines"][0]):
        return None
    boundary = list(body["bbox"])
    if not page.rect.contains(pymupdf.Rect(boundary)):
        return None
    y_boundaries = [
        boundary[1],
        *[(lines[i - 1]["bbox"][3] + lines[i]["bbox"][1]) / 2 for i in range(1, len(lines))],
        boundary[3],
    ]
    words = [word for word in page.get_text("words") if _inside(word[:4], boundary)]
    glyphs = [glyph for glyph in native_glyphs(page) if _inside(glyph["bbox_points"], boundary)]
    if not words or not glyphs or len(glyphs) > c["maximum_native_glyphs"]:
        return None
    assignments = [0 for _ in words]
    glyph_assignments = [0 for _ in glyphs]
    cells, layout = [], []
    for ri, line in enumerate(lines):
        box = [boundary[0], y_boundaries[ri], boundary[2], y_boundaries[ri + 1]]
        chars = []
        for gi, glyph in enumerate(glyphs):
            if _inside(glyph["bbox_points"], box):
                chars.append(glyph)
                glyph_assignments[gi] += 1
        for wi, word in enumerate(words):
            if _inside(word[:4], box):
                assignments[wi] += 1
        cells.append([_text(line)])
        layout.append(
            {
                "row": ri,
                "column": 0,
                "bbox_points": box,
                "raw_table_extract_text": None,
                "native_textbox_text": page.get_textbox(pymupdf.Rect(box)),
                "native_glyphs": chars,
                "position_ordered_text_candidate": _position_text(chars),
                "native_line_text": _text(line),
            }
        )
    if any(count != 1 for count in assignments + glyph_assignments):
        return None
    heading = headings[0]
    return {
        "recovery_revision": TABLE_RECOVERY_REVISION,
        "structure_role": "unruled_single_column_table",
        "bbox_points": boundary,
        "rows": len(cells),
        "columns": 1,
        "cells": cells,
        "x_boundaries_points": [boundary[0], boundary[2]],
        "y_boundaries_points": y_boundaries,
        "cells_with_native_layout": layout,
        "native_word_count": len(words),
        "native_words_assigned_exactly_once": True,
        "native_glyphs_assigned_exactly_once": True,
        "heading_candidate": {
            "native_text": _text(heading["lines"][0]),
            "bbox_points": list(heading["bbox"]),
            "semantic_role_verified": False,
        },
        "header_row_verified": False,
        "status": "needs_structure_review",
        "answer_evidence_eligible": False,
        "semantic_quality": None,
        "policy": "Body rows derive from native lines. The separately styled heading is retained separately; no header or cell relationship is semantically approved.",
    }
