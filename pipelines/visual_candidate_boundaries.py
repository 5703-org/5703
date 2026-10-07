"""Pure consumer boundaries for table bodies and distinct-locator PDF references."""

from __future__ import annotations

import copy
import json
import math
import re


def is_inline_reference(item: dict) -> bool:
    return (
        item.get("kind") == "table_candidate"
        and item.get("details", {}).get("record_role") == "inline_table_reference"
    )


def rectangular_table_body(item: dict) -> bool:
    if is_inline_reference(item):
        return False
    detail = item.get("details", {})
    cells = detail.get("cells")
    rows, columns = detail.get("rows"), detail.get("columns")
    shaped = bool(
        type(rows) is int
        and type(columns) is int
        and rows > 0
        and columns > 0
        and isinstance(cells, list)
        and len(cells) == rows
        and all(isinstance(row, list) and len(row) == columns for row in cells)
    )
    return shaped and (
        item.get("extractor_revision")
        not in {"pymupdf_visual_regions_v4", "pymupdf_visual_regions_v5"}
        or all(value is None or isinstance(value, str) for row in cells for value in row)
    )


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _box(value):
    return (
        isinstance(value, list)
        and len(value) == 4
        and all(type(x) in (int, float) and math.isfinite(x) for x in value)
        and 0 <= value[0] < value[2]
        and 0 <= value[1] < value[3]
    )


def _page_size(value):
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in value)
    )


def _within_page(box, size):
    return _box(box) and _page_size(size) and box[2] <= size[0] and box[3] <= size[1]


def validate_v4_source_geometry(item: dict) -> None:
    if item.get("extractor_revision") in {
        "pymupdf_visual_regions_v4",
        "pymupdf_visual_regions_v5",
    } and not _within_page(
        item.get("bbox_points"), item.get("details", {}).get("page_size_points")
    ):
        raise ValueError("V4 source geometry must stay inside its declared native PDF page")


def validate_reference_record(item: dict, *, physical_pages: int) -> None:
    validate_v4_source_geometry(item)
    if not is_inline_reference(item):
        return
    detail = item["details"]
    if any(detail.get(key) is not None for key in ("rows", "columns", "cells")) or detail.get(
        "cells_with_native_layout"
    ):
        raise ValueError("A reference must not carry target cells as a source-page table")
    if detail.get("source_reference_bbox_points") != item["bbox_points"]:
        raise ValueError("A reference must retain its source-page geometry")
    state = detail.get("reference_resolution_state")
    target = detail.get("reference_target_locator")
    if state == "unresolved_target" and target is None:
        return
    if state != "linked_candidate" or not isinstance(target, dict):
        raise ValueError("A reference must record an explicit linked or unresolved state")
    link = detail.get("native_pdf_link", {})
    point = link.get("target_point_points")
    page = target.get("physical_pdf_page")
    if (
        target.get("source_sha256") != item["source_sha256"]
        or type(page) is not int
        or not 1 <= page <= physical_pages
        or not _within_page(target.get("bbox_points"), target.get("page_size_points"))
        or target.get("label") != detail.get("label")
        or not _hash(target.get("target_candidate_region_id"))
        or not _hash(target.get("target_previous_region_id"))
        or target.get("target_extractor_revision") != "pymupdf_visual_regions_v3"
        or target.get("status") != "needs_structure_review"
        or target.get("answer_evidence_eligible") is not False
        or link.get("kind") != "internal_pdf_goto"
        or link.get("source_physical_pdf_page") != item["physical_pdf_page"]
        or link.get("target_physical_pdf_page") != page
        or not _within_page(link.get("source_link_bbox_points"), detail.get("page_size_points"))
    ):
        raise ValueError("A reference target must retain same-source PDF link provenance")
    if target["target_previous_region_id"] == detail.get("previous_region_id") or (
        page == item["physical_pdf_page"] and target["bbox_points"] == item["bbox_points"]
    ):
        raise ValueError("A reference target must be a distinct source region")
    if (
        not isinstance(point, list)
        or len(point) != 2
        or not all(type(value) in (int, float) and math.isfinite(value) for value in point)
    ):
        raise ValueError("A PDF destination must retain a finite native target point")
    if not (
        0 <= point[0] <= target["page_size_points"][0]
        and 0 <= point[1] <= target["page_size_points"][1]
    ):
        raise ValueError("A native PDF destination point must stay inside the target page")
    if (
        target.get("association_basis")
        != "native_pdf_goto_page_and_unique_standalone_same_label_candidate"
        or target.get("destination_point_table_containment_verified") is not False
        or target.get("semantic_association_verified") is not False
    ):
        raise ValueError("A reference must retain the limited mechanical association basis")


def validate_reference_targets(items: list[dict]) -> None:
    by_legacy = {item["details"]["previous_region_id"]: item for item in items}
    for item in items:
        if (
            not is_inline_reference(item)
            or item["details"].get("reference_resolution_state") != "linked_candidate"
        ):
            continue
        locator = item["details"]["reference_target_locator"]
        target = by_legacy.get(locator["target_previous_region_id"])
        if (
            target is None
            or is_inline_reference(target)
            or target["kind"] != "table_candidate"
            or target["source_sha256"] != locator["source_sha256"]
            or target["physical_pdf_page"] != locator["physical_pdf_page"]
            or target["bbox_points"] != locator["bbox_points"]
            or target["details"].get("page_size_points") != locator["page_size_points"]
            or target["details"].get("label") != locator["label"]
            or target["details"].get("previous_candidate_region_id")
            != locator["target_candidate_region_id"]
        ):
            raise ValueError(
                "The linked target must exist as a distinct matching candidate in this immutable book catalog"
            )


def validate_v3_parent_lineage(items: list[dict], parents: list[dict]) -> None:
    """Verify every claimed V3 parent against a separate hash-pinned catalog."""
    by_id = {parent["region_id"]: parent for parent in parents}
    legacy_ids = {parent["details"]["previous_region_id"] for parent in parents}
    claimed = [item["details"].get("previous_candidate_region_id") for item in items]
    if (
        len(by_id) != len(parents)
        or len(legacy_ids) != len(parents)
        or len(items) != len(parents)
        or set(claimed) != set(by_id)
        or len(set(claimed)) != len(items)
    ):
        raise ValueError("V4 requires a complete one-to-one immutable V3 parent catalog")
    for item in items:
        parent = by_id[item["details"]["previous_candidate_region_id"]]
        if (
            parent.get("extractor_revision") != "pymupdf_visual_regions_v3"
            or any(
                parent[key] != item[key]
                for key in ("source_sha256", "book", "physical_pdf_page", "kind")
            )
            or parent["details"]["previous_region_id"] != item["details"]["previous_region_id"]
        ):
            raise ValueError(
                "V4 parent identity, source, page, kind or original V2 lineage differs"
            )


def validate_v4_parent_lineage(items: list[dict], parents: list[dict]) -> None:
    """Removing V5 additions must recover the exact canonical V4 JSON payload."""
    by_id = {parent["region_id"]: parent for parent in parents}
    claimed = [item["details"].get("previous_version_region_id") for item in items]
    if (
        len(by_id) != len(parents)
        or len(items) != len(parents)
        or set(claimed) != set(by_id)
        or len(set(claimed)) != len(items)
    ):
        raise ValueError("V5 requires a complete one-to-one immutable V4 parent catalog")
    for item in items:
        parent = by_id[item["details"]["previous_version_region_id"]]
        if (
            item.get("extractor_revision") != "pymupdf_visual_regions_v5"
            or parent.get("extractor_revision") != "pymupdf_visual_regions_v4"
            or item["details"].get("previous_version_extractor_revision")
            != "pymupdf_visual_regions_v4"
        ):
            raise ValueError("V5 requires explicit immutable V4 parent provenance")
        restored = copy.deepcopy(item)
        restored["extractor_revision"] = "pymupdf_visual_regions_v4"
        restored["region_id"] = parent["region_id"]
        for key in (
            "previous_version_region_id",
            "previous_version_extractor_revision",
            "formula_context",
        ):
            restored["details"].pop(key, None)
        if json.dumps(restored, sort_keys=True, ensure_ascii=False, allow_nan=False) != json.dumps(
            parent, sort_keys=True, ensure_ascii=False, allow_nan=False
        ):
            raise ValueError("V5 must preserve the exact V4 candidate content and source locator")
