"""Source-bound PDF visual-region candidates, separate from the released corpus.

This extractor records visible geometry and native text. It never treats an image,
formula candidate or automatically reconstructed table as verified textbook prose.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable

import pymupdf


EXTRACTOR_REVISION = "pymupdf_visual_regions_v2"
_CAPTION = re.compile(r"^\s*(FIGURE|TABLE)\s+(\d+(?:\.\d+)?)\b", re.I)
_MATH = re.compile(r"[=≈≠≤≥∑∫√∆Δ⇌→←×÷±]|\b(?:sin|cos|log)\s*\(", re.I)


def _box(value: Iterable[float]) -> list[float]:
    return [round(float(component), 3) for component in value]


def _identity(record: dict) -> str:
    data = {key: value for key, value in record.items() if key != "region_id"}
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _record(
    *,
    source_sha256: str,
    book: str,
    physical_page: int,
    kind: str,
    bbox: Iterable[float],
    native_text: str,
    status: str,
    details: dict,
) -> dict:
    result = {
        "extractor_revision": EXTRACTOR_REVISION,
        "book": book,
        "source_sha256": source_sha256,
        "physical_pdf_page": physical_page,
        "kind": kind,
        "bbox_points": _box(bbox),
        "native_text": native_text.strip(),
        "status": status,
        "details": details,
    }
    result["region_id"] = _identity(result)
    return result


def _text_lines(page: pymupdf.Page) -> list[dict]:
    # IMAGE flags are disabled so extracting one page never copies its image bytes.
    flags = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    lines = []
    for block in page.get_text("dict", flags=flags)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line.get("spans", [])).strip()
            if text:
                lines.append({"text": text, "bbox": line["bbox"]})
    return lines


def _caption_below(image_bbox: tuple, captions: list[dict]) -> dict | None:
    x0, _, x1, y1 = image_bbox
    candidates = [
        (caption["bbox"][1] - y1, caption)
        for caption in captions
        if caption["kind"] == "figure"
        and 0 <= caption["bbox"][1] - y1 <= 125
        and caption["bbox"][2] >= x0
        and caption["bbox"][0] <= x1
    ]
    return min(candidates, key=lambda value: value[0])[1] if candidates else None


def extract_page_regions(
    page: pymupdf.Page, *, source_sha256: str, book: str, physical_page: int
) -> list[dict]:
    """Record image, caption, detected table and formula candidates on one PDF page."""
    lines = _text_lines(page)
    captions = []
    for line in lines:
        match = _CAPTION.match(line["text"])
        if match:
            captions.append(
                {
                    "kind": "figure" if match.group(1).lower() == "figure" else "table",
                    "label": f"{match.group(1).title()} {match.group(2)}",
                    "bbox": line["bbox"],
                    "text": line["text"],
                }
            )

    regions = []
    for image in page.get_image_info(hashes=True):
        raw_bbox = pymupdf.Rect(image["bbox"])
        visible_bbox = raw_bbox & page.rect
        bbox = tuple(visible_bbox if not visible_bbox.is_empty else raw_bbox)
        # Tiny icons and background tiles cannot be assumed to be textbook figures.
        if (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) < 900:
            continue
        caption = _caption_below(bbox, captions)
        regions.append(
            _record(
                source_sha256=source_sha256,
                book=book,
                physical_page=physical_page,
                kind="figure_image",
                bbox=bbox,
                native_text=caption["text"] if caption else "",
                status="needs_visual_review"
                if not visible_bbox.is_empty
                else "needs_geometry_review",
                details={
                    "caption_label": caption["label"] if caption else None,
                    "image_md5": image["digest"].hex(),
                    "pixel_width": image["width"],
                    "pixel_height": image["height"],
                    "raw_bbox_points": _box(raw_bbox),
                    "clipped_to_page": raw_bbox != visible_bbox,
                    "limitation": "Image semantics are not recovered by native PDF extraction.",
                },
            )
        )

    table_captions = [caption for caption in captions if caption["kind"] == "table"]
    if table_captions:
        detected = list(page.find_tables().tables)
        for caption in table_captions:
            # Multiple same-label captions on a continuation page remain separate.
            nearest = min(
                detected,
                key=lambda table: abs(table.bbox[1] - caption["bbox"][3]),
                default=None,
            )
            if nearest is None:
                details = {
                    "label": caption["label"],
                    "rows": None,
                    "columns": None,
                    "cells": None,
                    "limitation": "A table caption was found, but no cells were reconstructed.",
                }
                bbox = caption["bbox"]
            else:
                cells = nearest.extract()
                details = {
                    "label": caption["label"],
                    "rows": nearest.row_count,
                    "columns": nearest.col_count,
                    "cells": cells,
                    "limitation": "Automatic table geometry and reading order need source review.",
                }
                bbox = nearest.bbox
            regions.append(
                _record(
                    source_sha256=source_sha256,
                    book=book,
                    physical_page=physical_page,
                    kind="table_candidate",
                    bbox=bbox,
                    native_text=caption["text"],
                    status="needs_structure_review",
                    details=details,
                )
            )

    for line in lines:
        value = line["text"]
        if (
            len(value) > 130
            or len(value) < 3
            or _CAPTION.match(value)
            or not _MATH.search(value)
            or not any(character.isalpha() or character.isdigit() for character in value)
        ):
            continue
        regions.append(
            _record(
                source_sha256=source_sha256,
                book=book,
                physical_page=physical_page,
                kind="formula_candidate",
                bbox=line["bbox"],
                native_text=value,
                status="needs_formula_review",
                details={
                    "limitation": "A symbol or equality pattern is only a candidate; symbols and layout may be incomplete."
                },
            )
        )
    return regions
