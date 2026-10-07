"""Bounded native PDF context for review; no formula completion or correction."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata

import pymupdf

from pipelines.visual_regions import _box

CONTEXT_REVISION = "native_formula_context_v1"
CONTEXT_CONFIGURATION = {
    "neighboring_native_lines_each_side": 2,
    "maximum_context_glyphs": 4096,
    "maximum_line_gap_font_size_multiple": 2.5,
    "coordinate_tolerance_points": 0.002,
    "native_block_only": True,
    "cross_page_join": False,
    "native_text_correction": False,
}
_RELATION_END = re.compile(r"[=≈≠≤≥]\s*$")
_ARITHMETIC_END = re.compile(r"[+−\-×÷*/]\s*$")
_NUMERIC_RHS = re.compile(r"[=≈≠≤≥]\s*[+−\-]?\d+(?:\.\d+)?")


def _exact(first, second) -> bool:
    """JSON payload equality distinguishes booleans, integers and floats."""
    return json.dumps(first, sort_keys=True, ensure_ascii=False, allow_nan=False) == json.dumps(
        second, sort_keys=True, ensure_ascii=False, allow_nan=False
    )


def _quality(lines: list[dict]) -> dict:
    characters = [g["character"] for line in lines for g in line["native_glyphs"]]
    return {
        "replacement_character_count": sum(c.count("\ufffd") for c in characters),
        "control_character_count": sum(
            sum(unicodedata.category(c) == "Cc" and c not in "\t\n\r" for c in value)
            for value in characters
        ),
        "native_glyph_count": len(characters),
        "zero_extent_glyph_count": sum(
            g["bbox_points"][0] == g["bbox_points"][2] or g["bbox_points"][1] == g["bbox_points"][3]
            for line in lines
            for g in line["native_glyphs"]
        ),
        "corrected_characters": 0,
    }


def _hints(lines: list[dict], anchor_index: int) -> dict:
    value = lines[anchor_index]["native_text"]
    return {
        "relation_operator_at_anchor_line_end": bool(_RELATION_END.search(value)),
        "preceding_native_line_ends_arithmetic_operator": bool(
            anchor_index > 0 and _ARITHMETIC_END.search(lines[anchor_index - 1]["native_text"])
        ),
        "following_native_line_retained": anchor_index + 1 < len(lines),
        "anchor_parenthesis_count_differs": value.count("(") != value.count(")"),
        "numeric_relation_rhs_pattern_present": bool(_NUMERIC_RHS.search(value)),
        "hint_semantics_verified": False,
    }


def _native_lines(page: pymupdf.Page) -> list[list[dict]]:
    flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    blocks = []
    for bi, block in enumerate(page.get_text("rawdict", flags=flags)["blocks"]):
        if block.get("type") != 0:
            continue
        lines = []
        for li, line in enumerate(block.get("lines", [])):
            glyphs = [
                {
                    "character": char["c"],
                    "bbox_points": list(char["bbox"]),
                    "origin_points": list(char["origin"]),
                    "font_size": span["size"],
                    "font_flags": span["flags"],
                    "native_order": [bi, li, si, ci],
                }
                for si, span in enumerate(line.get("spans", []))
                for ci, char in enumerate(span.get("chars", []))
            ]
            lines.append(
                {
                    "native_order": [bi, li],
                    "native_text": "".join(g["character"] for g in glyphs).strip(),
                    "bbox_points": _box(line["bbox"]),
                    "native_bbox_points": list(line["bbox"]),
                    "direction": list(line.get("dir", (1.0, 0.0))),
                    "native_glyphs": glyphs,
                }
            )
        blocks.append(lines)
    return blocks


def _within(box: list, size: list, *, native_glyph: bool = False) -> bool:
    return (
        isinstance(box, list)
        and len(box) == 4
        and all(type(x) in (int, float) and math.isfinite(x) for x in box)
        and 0 <= box[0] <= box[2] <= size[0]
        and 0 <= box[1] <= box[3] <= size[1]
        and (native_glyph or (box[0] < box[2] and box[1] < box[3]))
    )


def _line_usable(line: dict, size: list) -> bool:
    return bool(
        line["native_text"]
        and line["native_glyphs"]
        and len(line["native_glyphs"]) <= CONTEXT_CONFIGURATION["maximum_context_glyphs"]
        and _exact(line["direction"], [1.0, 0.0])
        and _within(line["bbox_points"], size)
        and all(_within(g["bbox_points"], size, native_glyph=True) for g in line["native_glyphs"])
    )


def _adjacent(first: dict, second: dict) -> bool:
    a, b = first["bbox_points"], second["bbox_points"]
    font_size = max(g["font_size"] for line in (first, second) for g in line["native_glyphs"])
    return (
        second["native_order"][1] == first["native_order"][1] + 1
        and 0
        <= b[1] - a[1]
        <= font_size * CONTEXT_CONFIGURATION["maximum_line_gap_font_size_multiple"]
        and min(a[2], b[2]) > max(a[0], b[0])
    )


def recover_formula_context(page: pymupdf.Page, parent: dict) -> dict:
    """Keep whole adjacent lines from one native block; never merge their meaning."""
    size = [page.rect.width, page.rect.height]
    if parent["physical_pdf_page"] != page.number + 1:
        raise ValueError("The formula context locator must match the loaded PDF page")
    result = {
        "context_revision": CONTEXT_REVISION,
        "source_sha256": parent["source_sha256"],
        "physical_pdf_page": parent["physical_pdf_page"],
        "page_size_points": size,
        "anchor_parent_region_id": parent["region_id"],
        "anchor_text_sha256": hashlib.sha256(parent["native_text"].encode()).hexdigest(),
        "anchor_state": "unresolved_native_anchor",
        "anchor_native_order": None,
        "lines": [],
        "context_bbox_points": None,
        "newline_joined_native_text_candidate": "",
        "full_native_block_retained": False,
        "character_quality": _quality([]),
        "heuristic_hints": None,
        "semantic_completeness": None,
        "notation_verified": False,
        "answer_evidence_eligible": False,
    }
    matches = [
        (lines, index)
        for lines in _native_lines(page)
        for index, line in enumerate(lines)
        if line["native_text"] == parent["native_text"]
        and line["bbox_points"] == parent["bbox_points"]
    ]
    if len(matches) != 1:
        return result
    block, index = matches[0]
    if not _line_usable(block[index], size):
        return result
    low = high = index
    glyph_count = len(block[index]["native_glyphs"])
    radius = CONTEXT_CONFIGURATION["neighboring_native_lines_each_side"]
    for direction in (-1, 1):
        for distance in range(1, radius + 1):
            candidate_index = index + direction * distance
            if not 0 <= candidate_index < len(block):
                break
            neighbor = block[candidate_index]
            first, second = (neighbor, block[low]) if direction == -1 else (block[high], neighbor)
            if (
                not _line_usable(neighbor, size)
                or not _adjacent(first, second)
                or glyph_count + len(neighbor["native_glyphs"])
                > CONTEXT_CONFIGURATION["maximum_context_glyphs"]
            ):
                break
            glyph_count += len(neighbor["native_glyphs"])
            if direction == -1:
                low = candidate_index
            else:
                high = candidate_index
    selected = block[low : high + 1]
    result.update(
        anchor_state="unique_native_line",
        anchor_native_order=block[index]["native_order"],
        lines=selected,
        context_bbox_points=[
            min(line["bbox_points"][0] for line in selected),
            min(line["bbox_points"][1] for line in selected),
            max(line["bbox_points"][2] for line in selected),
            max(line["bbox_points"][3] for line in selected),
        ],
        newline_joined_native_text_candidate="\n".join(line["native_text"] for line in selected),
        full_native_block_retained=low == 0 and high + 1 == len(block),
        character_quality=_quality(selected),
        heuristic_hints=_hints(selected, index - low),
    )
    return result


def validate_formula_context(item: dict) -> None:
    """Validate bounded source provenance; this supplies no scientific approval."""
    detail = item["details"]
    context = detail.get("formula_context")
    if item["kind"] != "formula_candidate":
        if context is not None:
            raise ValueError("Only formula candidates can carry formula native context")
        return
    size = detail.get("page_size_points")
    if (
        not isinstance(size, list)
        or len(size) != 2
        or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in size)
    ):
        raise ValueError("Formula context requires positive finite native page dimensions")
    if not isinstance(context, dict) or any(
        key not in context or not _exact(context[key], value)
        for key, value in {
            "context_revision": CONTEXT_REVISION,
            "source_sha256": item["source_sha256"],
            "physical_pdf_page": item["physical_pdf_page"],
            "page_size_points": detail["page_size_points"],
            "anchor_parent_region_id": detail.get("previous_version_region_id"),
            "anchor_text_sha256": hashlib.sha256(item["native_text"].encode()).hexdigest(),
            "semantic_completeness": None,
            "notation_verified": False,
            "answer_evidence_eligible": False,
        }.items()
    ):
        raise ValueError("Formula context identity or unapproved source state differs")
    lines = context.get("lines")
    if (
        not isinstance(lines, list)
        or len(lines) > 1 + 2 * CONTEXT_CONFIGURATION["neighboring_native_lines_each_side"]
    ):
        raise ValueError("Formula native context exceeds its complete-line bound")
    if context.get("anchor_state") == "unresolved_native_anchor":
        if (
            lines
            or context.get("anchor_native_order") is not None
            or context.get("context_bbox_points") is not None
            or context.get("newline_joined_native_text_candidate") != ""
            or context.get("heuristic_hints") is not None
            or context.get("full_native_block_retained") is not False
            or not _exact(context.get("character_quality"), _quality([]))
        ):
            raise ValueError("An unresolved native anchor cannot claim context")
        return
    if context.get("anchor_state") != "unique_native_line" or not lines:
        raise ValueError("Formula context requires an explicit native anchor state")
    glyph_count = 0
    for line in lines:
        if not isinstance(line, dict):
            raise ValueError("Formula context lines must retain native provenance")
        order = line.get("native_order")
        glyphs = line.get("native_glyphs")
        if (
            not isinstance(order, list)
            or len(order) != 2
            or any(type(x) is not int or x < 0 for x in order)
            or not isinstance(glyphs, list)
            or not glyphs
            or not isinstance(line.get("native_text"), str)
            or not _exact(line.get("direction"), [1.0, 0.0])
            or not _within(line.get("bbox_points"), context["page_size_points"])
            or not _within(line.get("native_bbox_points"), context["page_size_points"])
            or not _exact(_box(line["native_bbox_points"]), line["bbox_points"])
        ):
            raise ValueError("Formula context line geometry or native order is invalid")
        previous_order = None
        for glyph in glyphs:
            glyph_order = glyph.get("native_order") if isinstance(glyph, dict) else None
            origin = glyph.get("origin_points") if isinstance(glyph, dict) else None
            if (
                not isinstance(glyph_order, list)
                or len(glyph_order) != 4
                or any(type(x) is not int or x < 0 for x in glyph_order)
                or glyph_order[:2] != order
                or (previous_order is not None and glyph_order <= previous_order)
                or not isinstance(glyph.get("character"), str)
                or not 1 <= len(glyph["character"]) <= 4
                or not _within(
                    glyph.get("bbox_points"), context["page_size_points"], native_glyph=True
                )
                or not isinstance(origin, list)
                or len(origin) != 2
                or any(type(x) not in (int, float) or not math.isfinite(x) for x in origin)
                or type(glyph.get("font_size")) not in (int, float)
                or not math.isfinite(glyph["font_size"])
                or glyph["font_size"] <= 0
                or type(glyph.get("font_flags")) is not int
            ):
                raise ValueError("Formula native glyph geometry or order is invalid")
            previous_order = glyph_order
        if "".join(g["character"] for g in glyphs).strip() != line["native_text"]:
            raise ValueError("Formula native line text differs from its retained glyphs")
        glyph_count += len(glyphs)
    if glyph_count > CONTEXT_CONFIGURATION["maximum_context_glyphs"] or any(
        a["native_order"][0] != b["native_order"][0] or not _adjacent(a, b)
        for a, b in zip(lines, lines[1:])
    ):
        raise ValueError("Formula context must remain a bounded adjacent native block")
    anchors = [
        index
        for index, line in enumerate(lines)
        if _exact(line["native_order"], context.get("anchor_native_order"))
        and line["native_text"] == item["native_text"]
        and _exact(line["bbox_points"], item["bbox_points"])
    ]
    radius = CONTEXT_CONFIGURATION["neighboring_native_lines_each_side"]
    if len(anchors) != 1 or anchors[0] > radius or len(lines) - anchors[0] - 1 > radius:
        raise ValueError("Formula native anchor must occur exactly once within context bounds")
    expected_box = [
        min(line["bbox_points"][0] for line in lines),
        min(line["bbox_points"][1] for line in lines),
        max(line["bbox_points"][2] for line in lines),
        max(line["bbox_points"][3] for line in lines),
    ]
    if (
        not _exact(context.get("context_bbox_points"), expected_box)
        or context.get("newline_joined_native_text_candidate")
        != "\n".join(line["native_text"] for line in lines)
        or not _exact(context.get("character_quality"), _quality(lines))
        or not _exact(context.get("heuristic_hints"), _hints(lines, anchors[0]))
        or type(context.get("full_native_block_retained")) is not bool
    ):
        raise ValueError("Formula context text, quality or heuristic provenance differs")


def validate_formula_context_against_page(item: dict, page: pymupdf.Page) -> None:
    """Recompute against the pinned original before staging; no DB is needed here."""
    parent = {
        key: item[key]
        for key in ("source_sha256", "physical_pdf_page", "native_text", "bbox_points")
    }
    parent["region_id"] = item["details"]["previous_version_region_id"]
    if not _exact(item["details"]["formula_context"], recover_formula_context(page, parent)):
        raise ValueError("Formula native context differs from the pinned original PDF page")
