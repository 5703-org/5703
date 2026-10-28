"""Explicit opt-in table candidates with separate native PDF reference locators."""

from __future__ import annotations

import copy
import re

import pymupdf

from pipelines import visual_regions as legacy
from pipelines import visual_regions_v3 as previous
from pipelines.native_tables_v1 import continuation_compatible
from pipelines.visual_candidate_boundaries import rectangular_table_body
from pipelines.native_tables_v2 import (
    RECOVERY_CONFIGURATION,
    recover_caption_bounded_grid,
    recover_unruled_single_column,
)

EXTRACTOR_REVISION = "pymupdf_visual_regions_v4"
_STANDALONE_TABLE = re.compile(r"\s*TABLE\s+\d+(?:\.\d+)?\s*", re.I)


def _caption(page, region):
    matches = [
        line["bbox"] for line in legacy._text_lines(page) if line["text"] == region["native_text"]
    ]
    return min(
        matches,
        key=lambda box: min(
            abs(box[1] - region["bbox_points"][3]), abs(box[3] - region["bbox_points"][1])
        ),
        default=region["bbox_points"],
    )


def _reference_links(page, caption):
    return [
        link
        for link in page.get_links()
        if link.get("kind") == pymupdf.LINK_GOTO and pymupdf.Rect(caption).intersects(link["from"])
    ]


def _bind_reference(page, region, caption, links, source_sha256, book):
    detail = region["details"]
    detail["record_role"] = "inline_table_reference"
    detail["source_reference_bbox_points"] = legacy._box(caption)
    region["bbox_points"] = legacy._box(caption)
    detail["previous_table_structure"] = {
        key: copy.deepcopy(detail.get(key)) for key in ("rows", "columns", "cells")
    }
    for key in ("rows", "columns", "cells"):
        detail[key] = None
    # Historical native structures stay in the previous-structure field, never as
    # an on-page body for this reference. A reference is not a table recovery.
    for key in (
        "cells_with_native_layout",
        "x_boundaries_points",
        "y_boundaries_points",
        "recovery_revision",
        "recovery_configuration",
        "native_word_count",
        "native_words_assigned_exactly_once",
        "native_glyphs_assigned_exactly_once",
        "continuation_candidates",
    ):
        detail.pop(key, None)
    detail["reference_resolution_state"] = "unresolved_target"
    detail["reference_target_locator"] = None
    detail["limitation"] = (
        "This candidate records a source-page table reference, not a table body. Target cells remain at a distinct target locator. It cannot be accepted as a complete table or used as answer evidence."
    )
    if len(links) != 1 or page.parent is None:
        detail["reference_resolution_reason"] = "No unique same-document native PDF destination."
        return
    link = links[0]
    target_index = link.get("page")
    if type(target_index) is not int or not 0 <= target_index < len(page.parent):
        detail["reference_resolution_reason"] = (
            "Native destination is outside the current source PDF."
        )
        return
    detail["native_pdf_link"] = {
        "kind": "internal_pdf_goto",
        "source_physical_pdf_page": page.number + 1,
        "source_link_bbox_points": legacy._box(link["from"]),
        "target_physical_pdf_page": target_index + 1,
        "target_point_points": list(link["to"]),
    }
    targets = previous.extract_page_regions(
        page.parent[target_index],
        source_sha256=source_sha256,
        book=book,
        physical_page=target_index + 1,
    )
    targets = [
        target
        for target in targets
        if target["kind"] == "table_candidate"
        and target["details"].get("label") == detail.get("label")
        and _source_table_caption(page.parent[target_index], target)
    ]
    if len(targets) != 1:
        detail["reference_resolution_reason"] = (
            "The PDF destination has no unique same-label standalone table caption."
        )
        return
    target = targets[0]
    detail["reference_resolution_state"] = "linked_candidate"
    detail["reference_target_locator"] = {
        "source_sha256": source_sha256,
        "physical_pdf_page": target_index + 1,
        "bbox_points": copy.deepcopy(target["bbox_points"]),
        "page_size_points": [
            page.parent[target_index].rect.width,
            page.parent[target_index].rect.height,
        ],
        "label": detail["label"],
        "target_candidate_region_id": target["region_id"],
        "target_extractor_revision": previous.EXTRACTOR_REVISION,
        "target_previous_region_id": target["details"]["previous_region_id"],
        "status": "needs_structure_review",
        "answer_evidence_eligible": False,
        "association_basis": "native_pdf_goto_page_and_unique_standalone_same_label_candidate",
        "destination_point_table_containment_verified": False,
        "semantic_association_verified": False,
    }


def extract_page_regions(
    page: pymupdf.Page, *, source_sha256: str, book: str, physical_page: int
) -> list[dict]:
    """Preserve V2 registry lineage and explicit V3 candidate provenance."""
    if physical_page != page.number + 1:
        raise ValueError("The physical locator must match the loaded PDF page")
    originals = previous.extract_page_regions(
        page, source_sha256=source_sha256, book=book, physical_page=physical_page
    )
    result = []
    for old in originals:
        region = copy.deepcopy(old)
        region["extractor_revision"] = EXTRACTOR_REVISION
        detail = region["details"]
        detail["page_size_points"] = [page.rect.width, page.rect.height]
        # previous_region_id remains the original V2 registry FK; V3 is additive.
        detail["previous_candidate_region_id"] = old["region_id"]
        detail["previous_candidate_extractor_revision"] = previous.EXTRACTOR_REVISION
        if region["kind"] == "table_candidate":
            detail["answer_evidence_eligible"] = False
            detail["semantic_quality"] = None
            caption = _caption(page, region)
            links = _reference_links(page, caption)
            if links:
                _bind_reference(page, region, caption, links, source_sha256, book)
            else:
                detail["record_role"] = "table_body_candidate"
                if detail.get("cells") is None and _STANDALONE_TABLE.fullmatch(
                    region["native_text"]
                ):
                    recovered = recover_caption_bounded_grid(
                        page, caption
                    ) or recover_unruled_single_column(page, caption)
                    if recovered:
                        detail["previous_table_structure"] = {
                            key: copy.deepcopy(old["details"].get(key))
                            for key in ("rows", "columns", "cells")
                        }
                        detail["native_caption_bbox_points"] = legacy._box(caption)
                        region["bbox_points"] = legacy._box(recovered["bbox_points"])
                        detail.update(
                            {
                                key: copy.deepcopy(value)
                                for key, value in recovered.items()
                                if key not in {"bbox_points", "status"}
                            }
                        )
                        detail["recovery_configuration"] = copy.deepcopy(RECOVERY_CONFIGURATION)
                        detail["limitation"] = (
                            "Native structure candidates require independent source, reading-order, notation and semantic review. Automatic recovery grants no approval or answer eligibility."
                        )
                        if (
                            page.parent is not None
                            and detail["structure_role"] == "caption_bounded_ruled_table"
                        ):
                            for index in (page.number - 1, page.number + 1):
                                if not 0 <= index < len(page.parent):
                                    continue
                                for other in previous.extract_page_regions(
                                    page.parent[index],
                                    source_sha256=source_sha256,
                                    book=book,
                                    physical_page=index + 1,
                                ):
                                    if other["kind"] != "table_candidate":
                                        continue
                                    first, second = (
                                        (other, region) if index < page.number else (region, other)
                                    )
                                    if continuation_compatible(first, second):
                                        detail.setdefault("continuation_candidates", []).append(
                                            {
                                                "physical_pdf_page": other["physical_pdf_page"],
                                                "previous_region_id": other["details"][
                                                    "previous_region_id"
                                                ],
                                                "bbox_points": other["bbox_points"],
                                                "cells": other["details"]["cells"],
                                                "policy": "Strict same-source adjacent-page header and geometry compatibility; separate review remains required.",
                                                "answer_evidence_eligible": False,
                                            }
                                        )
        region["region_id"] = legacy._identity(region)
        result.append(region)
    return result


def _source_table_caption(page, region) -> bool:
    """Bare labels or styled descriptive footers; paragraphs never qualify."""
    caption = _caption(page, region)
    if _reference_links(page, caption):
        return False
    if _STANDALONE_TABLE.fullmatch(region["native_text"]):
        return True
    match = legacy._CAPTION.match(region["native_text"])
    if (
        match is None
        or match.group(1) != "TABLE"
        or f"Table {match.group(2)}" != region["details"].get("label")
    ):
        return False
    detail = region["details"]
    if (
        not rectangular_table_body(region)
        or not detail.get("recovery_revision")
        or len(detail.get("cells_with_native_layout", [])) != detail["rows"] * detail["columns"]
        or detail.get("native_words_assigned_exactly_once") is not True
    ):
        return False
    body = region["bbox_points"]
    if not (
        0 <= caption[1] - body[3] <= RECOVERY_CONFIGURATION["maximum_caption_distance_points"]
        and min(caption[2], body[2]) > max(caption[0], body[0])
    ):
        return False
    flags = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    native_lines = [
        line
        for block in page.get_text("dict", flags=flags)["blocks"]
        if block.get("type") == 0
        for line in block.get("lines", [])
        if "".join(span["text"] for span in line["spans"]).strip() == region["native_text"]
    ]
    if len(native_lines) != 1:
        return False
    spans = [span for span in native_lines[0]["spans"] if span["text"].strip()]
    expected_label = f"TABLE {match.group(2)}"
    return bool(
        len(spans) >= 2
        and spans[0]["text"].strip() == expected_label
        and spans[0]["flags"] & 16
        and spans[0]["color"] != 0
        and any(
            span["flags"] != spans[0]["flags"] or span["color"] != spans[0]["color"]
            for span in spans[1:]
        )
    )
