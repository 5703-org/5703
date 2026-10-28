"""Native ruled-table candidates with retained glyph geometry and review status.

Only source drawing paths and native characters are used. No book/page lookup,
transcription dictionary or assumed correct row count participates in recovery.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import median

import pymupdf

TABLE_RECOVERY_REVISION = "native_ruled_tables_v1"
RECOVERY_CONFIGURATION = {
    "coordinate_tolerance_points": 1.5,
    "maximum_filled_rule_thickness_points": 1.5,
    "minimum_rule_length_points": 40.0,
    "minimum_vertical_length_points": 6.0,
    "minimum_vertical_body_coverage": 0.9,
    "maximum_header_height_points": 100.0,
    "maximum_rows": 200,
    "maximum_columns": 50,
    "maximum_native_glyphs": 100000,
    "maximum_caption_distance_points": 80.0,
    "continuation_width_relative_tolerance": 0.01,
    "continuation_boundary_relative_tolerance": 0.01,
    "continuation_previous_bottom_fraction": 0.8,
    "continuation_next_top_fraction": 0.25,
}


def _cluster(values: list[float], tolerance: float) -> list[float]:
    groups: list[list[float]] = []
    for value in sorted(values):
        if groups and value - groups[-1][0] <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [median(group) for group in groups]


def _inside(box: tuple | list, boundary: list[float]) -> bool:
    x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return boundary[0] <= x < boundary[2] and boundary[1] <= y < boundary[3]


def native_glyphs(page: pymupdf.Page) -> list[dict]:
    """Keep native order, baseline and size; candidate ordering remains separate."""
    flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    result = []
    for bi, block in enumerate(page.get_text("rawdict", flags=flags)["blocks"]):
        if block.get("type") != 0:
            continue
        for li, line in enumerate(block.get("lines", [])):
            for si, span in enumerate(line.get("spans", [])):
                for ci, char in enumerate(span.get("chars", [])):
                    result.append(
                        {
                            "character": char["c"],
                            "bbox_points": list(char["bbox"]),
                            "origin_points": list(char["origin"]),
                            "font_size": span["size"],
                            "font_flags": span["flags"],
                            "native_order": [bi, li, si, ci],
                        }
                    )
    return result


def _position_text(glyphs: list[dict]) -> str:
    if not glyphs:
        return ""
    tolerance = max(glyph["font_size"] for glyph in glyphs) * 0.6
    lines: list[list[dict]] = []
    for glyph in sorted(
        glyphs, key=lambda item: (sum(item["bbox_points"][1::2]) / 2, item["native_order"])
    ):
        centre = sum(glyph["bbox_points"][1::2]) / 2
        matches = [
            line
            for line in lines
            if abs(centre - median(sum(item["bbox_points"][1::2]) / 2 for item in line))
            <= tolerance
        ]
        if matches:
            matches[-1].append(glyph)
        else:
            lines.append([glyph])
    return "\n".join(
        "".join(
            item["character"]
            for item in sorted(
                line, key=lambda item: (item["bbox_points"][0], item["native_order"])
            )
        ).strip()
        for line in lines
    )


def _rules(page: pymupdf.Page) -> tuple[list[tuple], list[tuple]]:
    horizontal = []
    vertical = []
    c = RECOVERY_CONFIGURATION
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if drawing["type"] in {"f", "fs"}:
            if (
                rect.width >= c["minimum_rule_length_points"]
                and rect.height <= c["maximum_filled_rule_thickness_points"]
            ):
                horizontal.append((rect.x0, rect.x1, rect.y0))
            if (
                rect.height >= c["minimum_vertical_length_points"]
                and rect.width <= c["maximum_filled_rule_thickness_points"]
            ):
                vertical.append((rect.x0, rect.y0, rect.y1))
        for item in drawing["items"]:
            if item[0] != "l":
                continue
            a, b = item[1:3]
            if abs(a.y - b.y) <= 0.1 and abs(a.x - b.x) >= c["minimum_rule_length_points"]:
                horizontal.append((min(a.x, b.x), max(a.x, b.x), (a.y + b.y) / 2))
            if abs(a.x - b.x) <= 0.1 and abs(a.y - b.y) >= c["minimum_vertical_length_points"]:
                vertical.append(((a.x + b.x) / 2, min(a.y, b.y), max(a.y, b.y)))
    return horizontal, vertical


def recover_native_grids(page: pymupdf.Page) -> list[dict]:
    """Find source-derived open-border grids without caption/page coordinates."""
    c = RECOVERY_CONFIGURATION
    tolerance = c["coordinate_tolerance_points"]
    horizontal, vertical = _rules(page)
    spans: list[list[tuple]] = []
    for rule in sorted(horizontal):
        group = next(
            (
                group
                for group in spans
                if abs(group[0][0] - rule[0]) <= tolerance
                and abs(group[0][1] - rule[1]) <= tolerance
            ),
            None,
        )
        if group is None:
            spans.append([rule])
        else:
            group.append(rule)
    candidates = []
    for span in spans:
        left, right = median(rule[0] for rule in span), median(rule[1] for rule in span)
        ys = _cluster([rule[2] for rule in span], tolerance)
        if len(ys) < 3:
            continue
        interior = [rule for rule in vertical if left + tolerance < rule[0] < right - tolerance]
        components: list[list[tuple]] = []
        for rule in sorted(interior, key=lambda item: item[1]):
            matching = [
                group
                for group in components
                if rule[1] <= max(item[2] for item in group) + tolerance
                and rule[2] >= min(item[1] for item in group) - tolerance
            ]
            if matching:
                group = matching[0]
                group.append(rule)
                for other in matching[1:]:
                    group.extend(other)
                    components.remove(other)
            else:
                components.append([rule])
        for component in components:
            top = min(rule[1] for rule in component)
            bottom = max(rule[2] for rule in component)
            row_lines = [y for y in ys if top - tolerance <= y <= bottom + tolerance]
            if len(row_lines) < 2:
                continue
            following = [y for y in ys if y > row_lines[-1] + tolerance]
            typical_gap = median(b - a for a, b in zip(row_lines, row_lines[1:]))
            if following and following[0] - row_lines[-1] <= typical_gap * 1.6:
                # A partial interior rule cannot certify the remaining aligned rows.
                continue
            preceding = [y for y in ys if y < row_lines[0] - tolerance]
            if preceding and row_lines[0] - preceding[-1] <= c["maximum_header_height_points"]:
                row_lines.insert(0, preceding[-1])
            body_height = bottom - top
            complete = [
                rule[0]
                for rule in component
                if rule[2] - rule[1] >= body_height * c["minimum_vertical_body_coverage"]
            ]
            xs = [left, *_cluster(complete, tolerance), right]
            if (
                len(xs) < 3
                or len(row_lines) < 3
                or len(xs) - 1 > c["maximum_columns"]
                or len(row_lines) - 1 > c["maximum_rows"]
            ):
                continue
            boundary = [left, row_lines[0], right, row_lines[-1]]
            if not page.rect.contains(pymupdf.Rect(boundary)):
                continue
            finder = page.find_tables(
                clip=pymupdf.Rect(boundary),
                vertical_strategy="explicit",
                horizontal_strategy="explicit",
                vertical_lines=xs,
                horizontal_lines=row_lines,
            )
            if len(finder.tables) != 1:
                continue
            table = finder.tables[0]
            raw_cells = table.extract()
            if len(raw_cells) != len(row_lines) - 1 or any(
                len(row) != len(xs) - 1 for row in raw_cells
            ):
                continue
            words = [word for word in page.get_text("words") if _inside(word[:4], boundary)]
            if not words:
                continue
            glyphs = [
                glyph for glyph in native_glyphs(page) if _inside(glyph["bbox_points"], boundary)
            ]
            if len(glyphs) > c["maximum_native_glyphs"]:
                continue
            cell_details = []
            assignments: defaultdict[tuple, int] = defaultdict(int)
            for ri, row in enumerate(raw_cells):
                for ci, text in enumerate(row):
                    box = [xs[ci], row_lines[ri], xs[ci + 1], row_lines[ri + 1]]
                    chars = [glyph for glyph in glyphs if _inside(glyph["bbox_points"], box)]
                    selected_words = [word for word in words if _inside(word[:4], box)]
                    for word in selected_words:
                        assignments[tuple(word)] += 1
                    cell_details.append(
                        {
                            "row": ri,
                            "column": ci,
                            "bbox_points": box,
                            "raw_table_extract_text": text,
                            "native_textbox_text": page.get_textbox(pymupdf.Rect(box)),
                            "native_glyphs": chars,
                            "position_ordered_text_candidate": _position_text(chars),
                        }
                    )
            if any(assignments[tuple(word)] != 1 for word in words):
                continue
            candidates.append(
                {
                    "recovery_revision": TABLE_RECOVERY_REVISION,
                    "bbox_points": boundary,
                    "rows": len(raw_cells),
                    "columns": len(xs) - 1,
                    "cells": raw_cells,
                    "x_boundaries_points": xs,
                    "y_boundaries_points": row_lines,
                    "cells_with_native_layout": cell_details,
                    "native_word_count": len(words),
                    "native_words_assigned_exactly_once": True,
                    "status": "needs_structure_review",
                    "answer_evidence_eligible": False,
                    "semantic_quality": None,
                }
            )
    return sorted(candidates, key=lambda item: (item["bbox_points"][1], item["bbox_points"][0]))


def match_caption_grid(caption_bbox: list | tuple, grids: list[dict]) -> dict | None:
    """Require a nearby, horizontally overlapping grid; ambiguity stays unresolved."""
    c = RECOVERY_CONFIGURATION
    matches = []
    for grid in grids:
        box = grid["bbox_points"]
        overlap = min(box[2], caption_bbox[2]) - max(box[0], caption_bbox[0])
        distance = min(abs(box[1] - caption_bbox[3]), abs(box[3] - caption_bbox[1]))
        if overlap > 0 and distance <= c["maximum_caption_distance_points"]:
            matches.append((distance, grid))
    matches.sort(key=lambda item: item[0])
    if not matches or (
        len(matches) > 1 and matches[1][0] - matches[0][0] <= c["coordinate_tolerance_points"]
    ):
        return None
    return matches[0][1]


def continuation_compatible(first: dict, second: dict) -> bool:
    """Adjacent same-source label/header/relative-width boundaries must all agree."""
    if (
        first["source_sha256"] != second["source_sha256"]
        or first["physical_pdf_page"] + 1 != second["physical_pdf_page"]
    ):
        return False
    a, b = first["details"], second["details"]
    if (
        not a.get("cells")
        or not b.get("cells")
        or a.get("label") != b.get("label")
        or a["columns"] != b["columns"]
    ):
        return False
    page_a, page_b = a.get("page_size_points"), b.get("page_size_points")
    if not page_a or not page_b:
        return False
    if any(abs(x - y) > max(x, y) * 0.01 for x, y in zip(page_a, page_b, strict=True)):
        return False
    if (
        first["bbox_points"][3]
        < page_a[1] * RECOVERY_CONFIGURATION["continuation_previous_bottom_fraction"]
        or second["bbox_points"][1]
        > page_b[1] * RECOVERY_CONFIGURATION["continuation_next_top_fraction"]
    ):
        return False

    def normalize(value: object) -> str:
        return " ".join(str(value or "").split())

    if [normalize(value) for value in a["cells"][0]] != [
        normalize(value) for value in b["cells"][0]
    ]:
        return False
    width_a = first["bbox_points"][2] - first["bbox_points"][0]
    width_b = second["bbox_points"][2] - second["bbox_points"][0]
    if (
        abs(width_a - width_b)
        > max(width_a, width_b) * RECOVERY_CONFIGURATION["continuation_width_relative_tolerance"]
    ):
        return False
    xs_a, xs_b = a.get("x_boundaries_points"), b.get("x_boundaries_points")
    if not xs_a or not xs_b:
        return False
    return all(
        abs((x - xs_a[0]) / width_a - (y - xs_b[0]) / width_b)
        <= RECOVERY_CONFIGURATION["continuation_boundary_relative_tolerance"]
        for x, y in zip(xs_a, xs_b, strict=True)
    )
