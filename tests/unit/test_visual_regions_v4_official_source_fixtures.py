"""Optional exact-source regression fixtures; no raw source text is embedded."""

from __future__ import annotations

from hashlib import file_digest
from pathlib import Path

import pymupdf
import pytest

from pipelines.visual_candidate_boundaries import is_inline_reference, rectangular_table_body
from pipelines.visual_regions import _identity
from pipelines.visual_regions_v4 import extract_page_regions

PROJECT = Path(__file__).resolve().parents[2]
SOURCES = {
    "biology-2e": (
        "4d1f413fd779f114838cdaeab7859dcb2922ca7529230d3bfd7d36a77b4e27b6",
        "Biology 2e",
    ),
    "anatomy-and-physiology-2e": (
        "aa2e577b2083c343f4d57b38f00dd935dd2d98befdb38c0f368d72d636d0ff46",
        "Anatomy and Physiology 2e",
    ),
    "chemistry-2e": (
        "fd89db1b8a1fee06b8ad3e8982f4f4b34bde4e93654a4ce28b724f8c0efe98d6",
        "Chemistry 2e",
    ),
}
CASES = (
    ("biology-2e", 1429, "Table 47.2", None, 1429),
    ("anatomy-and-physiology-2e", 858, "Table 20.2", (4, 3), None),
    ("anatomy-and-physiology-2e", 905, "Table 20.11", None, 906),
    ("anatomy-and-physiology-2e", 1062, "Table 23.6", None, 1063),
    ("anatomy-and-physiology-2e", 1169, "Table 25.3", (11, 1), None),
    ("anatomy-and-physiology-2e", 1309, "Table 28.4", None, 1310),
    ("chemistry-2e", 1058, "Table 21.4", None, 1059),
)


@pytest.mark.parametrize("slug,physical_page,label,body_shape,target_page", CASES)
def test_exact_official_source_retains_body_or_distinct_reference(
    slug, physical_page, label, body_shape, target_page
):
    source_hash, title = SOURCES[slug]
    path = PROJECT / "artifacts/openstax/originals" / f"{slug}-{source_hash}.pdf"
    if not path.is_file():
        pytest.skip("Exact official original is not present; synthetic fixtures still run")
    with path.open("rb") as stream:
        assert file_digest(stream, "sha256").hexdigest() == source_hash
    with pymupdf.open(path) as document:
        records = extract_page_regions(
            document[physical_page - 1],
            source_sha256=source_hash,
            book=title,
            physical_page=physical_page,
        )
    # Exact six source pages have one caption-start candidate for the given label.
    record = next(
        item
        for item in records
        if item["kind"] == "table_candidate" and item["details"].get("label") == label
    )
    assert record["physical_pdf_page"] == physical_page
    assert record["region_id"] == _identity(record)
    assert record["details"]["answer_evidence_eligible"] is False
    assert record["status"] == "needs_structure_review"
    if body_shape is not None:
        assert rectangular_table_body(record)
        assert (record["details"]["rows"], record["details"]["columns"]) == body_shape
        assert not is_inline_reference(record)
    else:
        assert is_inline_reference(record)
        assert not rectangular_table_body(record)
        assert record["details"]["cells"] is None
        locator = record["details"]["reference_target_locator"]
        assert locator["source_sha256"] == source_hash
        assert locator["physical_pdf_page"] == target_page
        assert locator["bbox_points"] != record["bbox_points"]
        assert locator["target_previous_region_id"] != record["details"]["previous_region_id"]
