"""Prepare a separate unapproved V5 bundle with exact V4 and V3 parent sidecars."""

from __future__ import annotations

import argparse
import copy
from collections import Counter
import gzip
import json
from pathlib import Path
import shutil

import pymupdf

from app.modules.learning_product.visual_catalog_versions import load_bundle
from pipelines.native_formula_context_v1 import (
    CONTEXT_CONFIGURATION,
    validate_formula_context,
    validate_formula_context_against_page,
)
from pipelines.native_tables_v2 import RECOVERY_CONFIGURATION as TABLE_CONFIGURATION
from pipelines.visual_candidate_boundaries import (
    is_inline_reference,
    rectangular_table_body,
    validate_reference_record,
    validate_reference_targets,
    validate_v3_parent_lineage,
    validate_v4_parent_lineage,
)
from pipelines.visual_regions import _identity
from scripts.verify.build_visual_region_catalog import BOOKS, ROOT, _sha256

SCHEMA = "official_native_visual_review_sources_v3"
CANDIDATE_REVISION = "pymupdf_visual_regions_v5"
RECOVERY_REVISION = "native_visual_context_v5"
FROZEN_CONFIGURATION = {
    "table_recovery": TABLE_CONFIGURATION,
    "formula_context": CONTEXT_CONFIGURATION,
}
REQUIRED_SOURCE_PATHS = {
    "pipelines/visual_regions.py",
    "pipelines/visual_regions_v3.py",
    "pipelines/visual_regions_v4.py",
    "pipelines/visual_regions_v5.py",
    "pipelines/native_formula_context_v1.py",
    "pipelines/native_tables_v1.py",
    "pipelines/native_tables_v2.py",
    "pipelines/visual_candidate_boundaries.py",
    "scripts/verify/build_visual_region_catalog.py",
    "scripts/verify/prepare_visual_catalog_v5_bundle.py",
    "backend/app/modules/learning_product/visual_catalog_versions.py",
}


def _confined(path: Path) -> Path:
    root = ROOT.resolve()
    resolved = path.resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError("V5 preparation paths must stay inside a dedicated project directory")
    if any(part.is_symlink() for part in (path, *path.parents) if part != root):
        raise ValueError("V5 preparation does not follow symlink paths")
    return resolved


def _basename(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).name != value
        or "/" in value
        or "\\" in value
        or ":" in value
        or value in {".", ".."}
    ):
        raise ValueError("V5 catalog filenames must be confined basenames")
    return value


def _relative(value: str) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
        or "\\" in value
        or ":" in value
    ):
        raise ValueError("V5 source and catalog locations must use confined relative paths")
    return _confined(ROOT / value)


def prepare_bundle(
    catalog_dir: Path,
    parent_v4_bundle: Path,
    source_freeze: Path,
    output: Path,
    *,
    expected_parent_manifest_sha256: str,
) -> dict:
    """Verify the new full catalog and parent chain before writing a new directory."""
    catalog_dir, parent_v4_bundle, source_freeze, output = [
        _confined(path) for path in (catalog_dir, parent_v4_bundle, source_freeze, output)
    ]
    current_path = _confined(catalog_dir / "manifest.json")
    _confined(parent_v4_bundle / "SOURCE_MANIFEST.json")
    current = json.loads(current_path.read_text(encoding="utf-8"))
    if (
        current.get("extractor_revision") != CANDIDATE_REVISION
        or current.get("scope") != "full_originals"
        or len(current.get("books", [])) != 4
    ):
        raise ValueError("A complete four-book explicit V5 catalog is required")
    parent_manifest, parent_books = load_bundle(
        parent_v4_bundle,
        expected_manifest_sha256=expected_parent_manifest_sha256,
    )
    if parent_manifest["candidate_revision"] != "pymupdf_visual_regions_v4":
        raise ValueError("The exact immutable V4 prepared bundle is required")
    frozen = json.loads(source_freeze.read_text(encoding="utf-8"))
    if not isinstance(frozen.get("before"), dict) or not REQUIRED_SOURCE_PATHS.issubset(
        frozen["before"]
    ):
        raise ValueError("The source freeze must pin the complete V5 producer and consumer")
    for relative, expected in frozen["before"].items():
        path = _relative(relative)
        if _sha256(path) != expected:
            raise ValueError("Current implementation differs from the supplied source freeze")
    parents_by_source = {book["source_sha256"]: (book, items) for book, items in parent_books}
    totals = Counter()
    books, copies, seen_sources, seen_slugs = [], [], set(), set()
    for book in current["books"]:
        if book.get("slug") not in BOOKS or book["slug"] in seen_slugs:
            raise ValueError(
                "V5 must use each of the four fixed official source slugs exactly once"
            )
        seen_slugs.add(book["slug"])
        pair = parents_by_source.get(book["source_sha256"])
        if pair is None or book["source_sha256"] in seen_sources:
            raise ValueError("V5 sources must occur once each in the exact V4 parent bundle")
        seen_sources.add(book["source_sha256"])
        parent_book, parents = pair
        if (
            book.get("failed_pages")
            or book["inspected_pages"] != book["physical_pages"]
            or book["physical_pages"] != parent_book["physical_pages"]
            or book["title"] != parent_book["book"]
            or book["slug"] != parent_book["slug"]
            or book["source_size_bytes"] != parent_book["source_size_bytes"]
        ):
            raise ValueError("Incomplete extraction or changed original source metadata")
        source = _relative(book["source_path"])
        catalog = _relative(book["catalog_path"])
        if (
            catalog.name != f"{book['slug']}-regions.jsonl.gz"
            or _sha256(source) != book["source_sha256"]
            or source.stat().st_size != book["source_size_bytes"]
            or _sha256(catalog) != book["catalog_sha256"]
        ):
            raise ValueError("Pinned original source or V5 catalog changed")
        with gzip.open(catalog, "rt", encoding="utf-8") as stream:
            items = [json.loads(line) for line in stream]
        if len({item["region_id"] for item in items}) != len(items):
            raise ValueError("Every V5 candidate identity must be unique")
        v3_path = _confined(
            parent_v4_bundle / _basename(parent_book["parent_candidate_catalog_file"])
        )
        with gzip.open(v3_path, "rt", encoding="utf-8") as stream:
            v3_parents = [json.loads(line) for line in stream]
        validate_v3_parent_lineage(items, v3_parents)
        validate_v4_parent_lineage(items, parents)
        for item in items:
            if (
                item["region_id"] != _identity(item)
                or item["extractor_revision"] != CANDIDATE_REVISION
                or item["source_sha256"] != book["source_sha256"]
                or item["details"].get("answer_evidence_eligible", False) is not False
            ):
                raise ValueError("Candidate identity or unapproved state is invalid")
            validate_reference_record(item, physical_pages=book["physical_pages"])
            validate_formula_context(item)
            totals[item["kind"]] += 1
            if item["kind"] == "formula_candidate":
                context = item["details"]["formula_context"]
                totals["formula_contexts"] += 1
                totals["unresolved_formula_contexts"] += int(
                    context["anchor_state"] == "unresolved_native_anchor"
                )
                totals["formula_glyphs"] += sum(
                    len(line["native_glyphs"]) for line in context["lines"]
                )
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
        with pymupdf.open(source) as pdf:
            if len(pdf) != book["physical_pages"]:
                raise ValueError("The physical page count differs from the pinned original")
            for item in items:
                page = pdf[item["physical_pdf_page"] - 1]
                if item["details"]["page_size_points"] != [page.rect.width, page.rect.height]:
                    raise ValueError("V5 source dimensions differ from the pinned original page")
                if item["kind"] == "formula_candidate":
                    validate_formula_context_against_page(item, page)
        v4_path = _confined(parent_v4_bundle / _basename(parent_book["catalog_file"]))
        v3_name = f"{book['slug']}-parent-v3.jsonl.gz"
        v4_name = f"{book['slug']}-parent-v4.jsonl.gz"
        copies.extend(((catalog, catalog.name), (v3_path, v3_name), (v4_path, v4_name)))
        books.append(
            {
                "book": book["title"],
                "slug": book["slug"],
                "source_sha256": book["source_sha256"],
                "source_size_bytes": book["source_size_bytes"],
                "physical_pages": book["physical_pages"],
                "catalog_file": catalog.name,
                "catalog_sha256": book["catalog_sha256"],
                "previous_catalog_sha256": parent_book["previous_catalog_sha256"],
                "all_old_region_lineages_preserved": len(items),
                "parent_candidate_catalog_file": v3_name,
                "parent_candidate_catalog_sha256": parent_book["parent_candidate_catalog_sha256"],
                "previous_version_catalog_file": v4_name,
                "previous_version_catalog_sha256": parent_book["catalog_sha256"],
            }
        )
    manifest = {
        "schema": SCHEMA,
        "candidate_revision": CANDIDATE_REVISION,
        "recovery_revision": RECOVERY_REVISION,
        "pymupdf_version": current["pymupdf_version"],
        "frozen_configuration": copy.deepcopy(FROZEN_CONFIGURATION),
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
        "formula_context_count": totals["formula_contexts"],
        "unresolved_formula_context_count": totals["unresolved_formula_contexts"],
        "native_glyph_records_in_formula_context_candidates": totals["formula_glyphs"],
        "human_ratings": 0,
        "semantic_approvals": 0,
        "answer_evidence_eligible_candidates": 0,
        "published_candidates": 0,
    }
    copy_names = [_basename(name) for _, name in copies]
    if len(set(copy_names)) != len(copy_names):
        raise ValueError("V5 copy destinations must be unique confined basenames")
    destinations = [_confined(output / name) for name in copy_names]
    output.mkdir(parents=True, exist_ok=False)
    for (path, _), destination in zip(copies, destinations, strict=True):
        shutil.copyfile(path, destination)
    (output / "SOURCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    # Exercise the actual consumer before describing this as a prepared bundle.
    load_bundle(output, expected_manifest_sha256=_sha256(output / "SOURCE_MANIFEST.json"))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--parent-v4-bundle-dir", type=Path, required=True)
    parser.add_argument("--expected-parent-manifest-sha256", required=True)
    parser.add_argument("--source-freeze", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    if output == ROOT or not output.is_relative_to(ROOT):
        parser.error("Use a dedicated new directory inside the project")
    result = prepare_bundle(
        args.catalog_dir,
        args.parent_v4_bundle_dir,
        args.source_freeze,
        args.out,
        expected_parent_manifest_sha256=args.expected_parent_manifest_sha256,
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
