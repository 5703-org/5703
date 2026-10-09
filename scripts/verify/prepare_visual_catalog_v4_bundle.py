"""Prepare a new immutable, unapproved V4 bundle; legacy artifacts are read-only."""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import shutil

from pipelines.native_tables_v2 import RECOVERY_CONFIGURATION, TABLE_RECOVERY_REVISION
from pipelines.visual_candidate_boundaries import (
    is_inline_reference,
    rectangular_table_body,
    validate_reference_record,
    validate_reference_targets,
    validate_v3_parent_lineage,
)
from pipelines.visual_regions import _identity
from scripts.verify.build_visual_region_catalog import ROOT, _sha256


def prepare_bundle(
    catalog_dir: Path, legacy_dir: Path, parent_v3_dir: Path, source_freeze: Path, output: Path
) -> dict:
    """No labels, DB, corpus, HTTP or provider action; write a dedicated new bundle."""
    current = json.loads((catalog_dir / "manifest.json").read_text(encoding="utf-8"))
    legacy = json.loads((legacy_dir / "manifest.json").read_text(encoding="utf-8"))
    parent_manifest = json.loads((parent_v3_dir / "manifest.json").read_text(encoding="utf-8"))
    if (
        current.get("extractor_revision") != "pymupdf_visual_regions_v4"
        or legacy.get("extractor_revision") != "pymupdf_visual_regions_v2"
        or current.get("scope") != "full_originals"
        or legacy.get("scope") != "full_originals"
        or len(current.get("books", [])) != 4
        or len(legacy.get("books", [])) != 4
    ):
        raise ValueError(
            "Complete four-book explicit V4 and immutable legacy V2 catalogs are required"
        )
    if (
        parent_manifest.get("extractor_revision") != "pymupdf_visual_regions_v3"
        or parent_manifest.get("scope") != "full_originals"
        or len(parent_manifest.get("books", [])) != 4
    ):
        raise ValueError("A complete immutable V3 parent catalog is required")
    frozen = json.loads(source_freeze.read_text(encoding="utf-8"))
    if not isinstance(frozen.get("before"), dict):
        raise ValueError("A current software source snapshot with exact before hashes is required")
    required_source_paths = {
        "pipelines/native_tables_v2.py",
        "pipelines/visual_regions_v4.py",
        "pipelines/visual_candidate_boundaries.py",
        "scripts/verify/build_visual_region_catalog.py",
        "scripts/verify/prepare_visual_catalog_v4_bundle.py",
        "backend/app/modules/learning_product/visual_catalog_versions.py",
    }
    if not required_source_paths.issubset(frozen["before"]):
        raise ValueError(
            "The source freeze must pin the integrated V4 producer and consumer implementation"
        )
    for relative, expected in frozen["before"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or _sha256(path) != expected:
            raise ValueError("Current implementation differs from the supplied source freeze")
    old_books = {book["slug"]: book for book in legacy["books"]}
    parent_books = {book["slug"]: book for book in parent_manifest["books"]}
    totals = Counter()
    books = []
    copies = []
    for book in current["books"]:
        previous = old_books.get(book["slug"])
        parent_book = parent_books.get(book["slug"])
        if (
            previous is None
            or previous["source_sha256"] != book["source_sha256"]
            or book["failed_pages"]
        ):
            raise ValueError("Source identity or extraction failure prevents a complete bundle")
        if parent_book is None or parent_book["source_sha256"] != book["source_sha256"]:
            raise ValueError("The V3 parent belongs to a different original source")
        source = (ROOT / book["source_path"]).resolve()
        catalog = (ROOT / book["catalog_path"]).resolve()
        old_catalog = (ROOT / previous["catalog_path"]).resolve()
        parent_catalog = (ROOT / parent_book["catalog_path"]).resolve()
        if (
            any(not path.is_relative_to(ROOT) for path in (source, catalog, old_catalog))
            or _sha256(source) != book["source_sha256"]
            or _sha256(catalog) != book["catalog_sha256"]
            or _sha256(old_catalog) != previous["catalog_sha256"]
        ):
            raise ValueError("Pinned source or catalog changed")
        if (
            not parent_catalog.is_relative_to(ROOT)
            or _sha256(parent_catalog) != parent_book["catalog_sha256"]
        ):
            raise ValueError("The immutable V3 parent catalog changed")
        with gzip.open(parent_catalog, "rt", encoding="utf-8") as parent_stream:
            parents = [json.loads(line) for line in parent_stream]
        with gzip.open(old_catalog, "rt", encoding="utf-8") as stream:
            old_ids = {json.loads(line)["region_id"] for line in stream}
        with gzip.open(catalog, "rt", encoding="utf-8") as stream:
            items = [json.loads(line) for line in stream]
        if (
            len({item["region_id"] for item in items}) != len(items)
            or {item["details"]["previous_region_id"] for item in items} != old_ids
            or len(items) != len(old_ids)
        ):
            raise ValueError("Every V2 lineage must occur exactly once in the new version")
        for item in items:
            if (
                item["region_id"] != _identity(item)
                or item["extractor_revision"] != current["extractor_revision"]
                or item["source_sha256"] != book["source_sha256"]
                or not item["status"].startswith("needs_")
                or item["details"].get("answer_evidence_eligible", False) is not False
            ):
                raise ValueError("Candidate identity or unapproved state is invalid")
            validate_reference_record(item, physical_pages=book["physical_pages"])
            totals[item["kind"]] += 1
            if item["kind"] == "table_candidate":
                totals["rectangular"] += int(rectangular_table_body(item))
                totals["unresolved"] += int(
                    not rectangular_table_body(item) and not is_inline_reference(item)
                )
                totals["references"] += int(is_inline_reference(item))
                totals["linked"] += int(
                    is_inline_reference(item)
                    and item["details"].get("reference_resolution_state") == "linked_candidate"
                )
                totals["glyphs"] += sum(
                    len(cell["native_glyphs"])
                    for cell in item["details"].get("cells_with_native_layout", [])
                )
        validate_reference_targets(items)
        validate_v3_parent_lineage(items, parents)
        copies.append((catalog, catalog.name))
        parent_name = f"{book['slug']}-parent-v3.jsonl.gz"
        copies.append((parent_catalog, parent_name))
        books.append(
            {
                "book": book["title"],
                "slug": book["slug"],
                "source_sha256": book["source_sha256"],
                "source_size_bytes": book["source_size_bytes"],
                "physical_pages": book["physical_pages"],
                "catalog_file": catalog.name,
                "catalog_sha256": book["catalog_sha256"],
                "previous_catalog_sha256": previous["catalog_sha256"],
                "all_old_region_lineages_preserved": len(items),
                "parent_candidate_catalog_file": parent_name,
                "parent_candidate_catalog_sha256": parent_book["catalog_sha256"],
            }
        )
    manifest = {
        "schema": "official_native_table_review_sources_v2",
        "candidate_revision": current["extractor_revision"],
        "recovery_revision": TABLE_RECOVERY_REVISION,
        "pymupdf_version": current["pymupdf_version"],
        "frozen_configuration": RECOVERY_CONFIGURATION,
        "freeze_sha256": _sha256(source_freeze),
        "frozen_source_files": [
            {"path": path, "sha256": sha} for path, sha in frozen["before"].items()
        ],
        "books": books,
        "region_count": sum(
            totals[k] for k in ("figure_image", "table_candidate", "formula_candidate")
        ),
        "table_count": totals["table_candidate"],
        "candidate_rectangular_grids": totals["rectangular"],
        "retained_unresolved_tables": totals["unresolved"],
        "inline_table_reference_count": totals["references"],
        "linked_table_reference_count": totals["linked"],
        "native_glyph_records_in_table_candidates": totals["glyphs"],
        "human_ratings": 0,
        "semantic_approvals": 0,
        "answer_evidence_eligible_candidates": 0,
        "published_candidates": 0,
    }
    output.mkdir(parents=True, exist_ok=False)
    for catalog, filename in copies:
        shutil.copyfile(catalog, output / filename)
    (output / "SOURCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--legacy-catalog-dir", type=Path, required=True)
    parser.add_argument("--parent-v3-catalog-dir", type=Path, required=True)
    parser.add_argument("--source-freeze", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    if output == ROOT or not output.is_relative_to(ROOT):
        parser.error("Use a dedicated new directory inside the project")
    result = prepare_bundle(
        args.catalog_dir.resolve(),
        args.legacy_catalog_dir.resolve(),
        args.parent_v3_catalog_dir.resolve(),
        args.source_freeze.resolve(),
        output,
    )
    print(
        json.dumps(
            {
                "bundle_manifest_sha256": _sha256(output / "SOURCE_MANIFEST.json"),
                "region_count": result["region_count"],
                "human_ratings": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
