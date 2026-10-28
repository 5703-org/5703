"""Explicit opt-in visual candidates; legacy v2 identities remain untouched."""

from __future__ import annotations

import copy

import pymupdf

from pipelines import visual_regions as legacy
from pipelines.native_tables_v1 import (
    RECOVERY_CONFIGURATION,
    continuation_compatible,
    match_caption_grid,
    recover_native_grids,
)

EXTRACTOR_REVISION = "pymupdf_visual_regions_v3"


def _page_regions(
    page: pymupdf.Page, *, source_sha256: str, book: str, physical_page: int
) -> list[dict]:
    previous = legacy.extract_page_regions(
        page, source_sha256=source_sha256, book=book, physical_page=physical_page
    )
    result = []
    grids = None
    for old in previous:
        region = copy.deepcopy(old)
        region["extractor_revision"] = EXTRACTOR_REVISION
        region["details"]["previous_region_id"] = old["region_id"]
        region["details"]["previous_extractor_revision"] = legacy.EXTRACTOR_REVISION
        if region["kind"] == "table_candidate":
            region["details"]["answer_evidence_eligible"] = False
            region["details"]["page_size_points"] = [page.rect.width, page.rect.height]
        if region["kind"] == "table_candidate":
            if grids is None:
                grids = recover_native_grids(page)
            captions = [
                line["bbox"]
                for line in legacy._text_lines(page)
                if line["text"] == region["native_text"]
            ]
            caption_bbox = min(
                captions,
                key=lambda box: min(
                    abs(box[1] - region["bbox_points"][3]), abs(box[3] - region["bbox_points"][1])
                ),
                default=region["bbox_points"],
            )
            recovered = match_caption_grid(caption_bbox, grids)
            if recovered and old["details"].get("cells") is not None:
                recovered_box = pymupdf.Rect(recovered["bbox_points"])
                recovered_box += (-1.5, -1.5, 1.5, 1.5)
                if not recovered_box.contains(pymupdf.Rect(old["bbox_points"])):
                    recovered = None
            if recovered:
                region["details"]["previous_table_structure"] = {
                    key: copy.deepcopy(old["details"].get(key))
                    for key in ["rows", "columns", "cells"]
                }
                region["details"]["native_caption_bbox_points"] = legacy._box(caption_bbox)
                region["bbox_points"] = legacy._box(recovered["bbox_points"])
                region["details"].update(
                    {
                        key: copy.deepcopy(value)
                        for key, value in recovered.items()
                        if key not in {"bbox_points", "status"}
                    }
                )
                region["details"]["recovery_configuration"] = copy.deepcopy(RECOVERY_CONFIGURATION)
                region["details"]["limitation"] = (
                    "Native drawing-derived grid and glyph-order candidates require source structure, notation and semantic review before any answer-evidence use."
                )
        region["region_id"] = legacy._identity(region)
        result.append(region)
    return result


def extract_page_regions(
    page: pymupdf.Page, *, source_sha256: str, book: str, physical_page: int
) -> list[dict]:
    """Recover unresolved grids and retain strict adjacent-page join candidates."""
    regions = _page_regions(
        page, source_sha256=source_sha256, book=book, physical_page=physical_page
    )
    recovered = [
        region
        for region in regions
        if region["kind"] == "table_candidate" and region["details"].get("recovery_revision")
    ]
    document = page.parent
    if recovered and document is not None:
        for index in [page.number - 1, page.number + 1]:
            if index < 0 or index >= len(document):
                continue
            neighboring = _page_regions(
                document[index], source_sha256=source_sha256, book=book, physical_page=index + 1
            )
            for region in recovered:
                for other in neighboring:
                    if other["kind"] != "table_candidate":
                        continue
                    first, second = (other, region) if index < page.number else (region, other)
                    if continuation_compatible(first, second):
                        region["details"].setdefault("continuation_candidates", []).append(
                            {
                                "physical_pdf_page": other["physical_pdf_page"],
                                "previous_region_id": other["details"]["previous_region_id"],
                                "bbox_points": other["bbox_points"],
                                "cells": other["details"]["cells"],
                                "policy": "Adjacent physical page, same source/table label, identical normalized header and compatible native column widths; independent content approval remains required.",
                                "answer_evidence_eligible": False,
                            }
                        )
                        region["region_id"] = legacy._identity(region)
    return regions
