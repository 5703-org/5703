"""Opt-in V5 native formula context; immutable V4 payloads remain exact parents."""

from __future__ import annotations

import copy

import pymupdf

from pipelines.native_formula_context_v1 import recover_formula_context
from pipelines.visual_regions import _identity
from pipelines import visual_regions_v4 as previous

EXTRACTOR_REVISION = "pymupdf_visual_regions_v5"


def extract_page_regions(
    page: pymupdf.Page, *, source_sha256: str, book: str, physical_page: int
) -> list[dict]:
    """Retain every V4 candidate and source locator; add unapproved native context."""
    parents = previous.extract_page_regions(
        page, source_sha256=source_sha256, book=book, physical_page=physical_page
    )
    result = []
    for parent in parents:
        region = copy.deepcopy(parent)
        region["extractor_revision"] = EXTRACTOR_REVISION
        detail = region["details"]
        detail["previous_version_region_id"] = parent["region_id"]
        detail["previous_version_extractor_revision"] = previous.EXTRACTOR_REVISION
        if region["kind"] == "formula_candidate":
            detail["formula_context"] = recover_formula_context(page, parent)
        region["region_id"] = _identity(region)
        result.append(region)
    return result
