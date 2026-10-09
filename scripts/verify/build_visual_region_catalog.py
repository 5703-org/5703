"""Build an additive visual-region audit from the four original OpenStax PDFs.

The output is a candidate catalog. It does not publish new corpus text or vectors.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipelines.visual_regions import EXTRACTOR_REVISION, extract_page_regions


BOOKS = (
    "anatomy-and-physiology-2e",
    "biology-2e",
    "chemistry-2e",
    "concepts-biology",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scan_book(
    slug: str,
    output: Path,
    max_pages: int | None = None,
    extractor_revision: str = EXTRACTOR_REVISION,
) -> dict:
    if extractor_revision == EXTRACTOR_REVISION:
        extract = extract_page_regions
    elif extractor_revision == "pymupdf_visual_regions_v3":
        from pipelines.visual_regions_v3 import extract_page_regions as extract
    elif extractor_revision == "pymupdf_visual_regions_v4":
        from pipelines.visual_regions_v4 import extract_page_regions as extract
    elif extractor_revision == "pymupdf_visual_regions_v5":
        from pipelines.visual_regions_v5 import extract_page_regions as extract
    else:
        raise ValueError("Unsupported visual extractor revision")
    acquisition_path = ROOT / "evidence/openstax" / f"{slug}-acquisition.json"
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    source_path = (ROOT / acquisition["raw_path"]).resolve()
    if not source_path.is_relative_to(ROOT) or not source_path.is_file():
        raise ValueError(f"Original source is missing or outside the project: {slug}")
    actual_sha256 = _sha256(source_path)
    if actual_sha256 != acquisition["sha256"]:
        raise ValueError(f"Original OpenStax source hash mismatch: {slug}")
    document = pymupdf.open(source_path)
    total_pages = len(document)
    output.mkdir(parents=True, exist_ok=True)
    catalog = output / f"{slug}-regions.jsonl.gz"
    if catalog.exists():
        raise FileExistsError(f"Existing catalog is immutable: {catalog}")
    count = Counter()
    failures = []
    inspected_pages = min(total_pages, max_pages) if max_pages is not None else total_pages
    try:
        with gzip.open(catalog, "wt", encoding="utf-8", compresslevel=6) as stream:
            for index in range(inspected_pages):
                try:
                    regions = extract(
                        document[index],
                        source_sha256=actual_sha256,
                        book=acquisition["title"],
                        physical_page=index + 1,
                    )
                except Exception as exc:
                    failures.append(
                        {
                            "physical_pdf_page": index + 1,
                            "error_type": type(exc).__name__,
                            "message": str(exc)[:500],
                        }
                    )
                    continue
                for region in regions:
                    stream.write(json.dumps(region, ensure_ascii=False, sort_keys=True) + "\n")
                    count[region["kind"]] += 1
                    if region["kind"] == "table_candidate":
                        if region["details"].get("record_role") == "inline_table_reference":
                            count["inline_table_references"] += 1
                            count["linked_table_references"] += int(
                                region["details"].get("reference_resolution_state")
                                == "linked_candidate"
                            )
                        elif region["details"]["cells"] is None:
                            count["table_structure_unresolved"] += 1
    finally:
        document.close()
    return {
        "slug": slug,
        "title": acquisition["title"],
        "official_pdf_url": acquisition["pdf_url"],
        "license_url": acquisition["license_url"],
        "source_path": source_path.relative_to(ROOT).as_posix(),
        "source_sha256": actual_sha256,
        "source_size_bytes": source_path.stat().st_size,
        "source_acquired_at": acquisition["acquired_at"],
        "physical_pages": total_pages,
        "inspected_pages": inspected_pages,
        "counts": dict(count),
        "failed_pages": failures,
        "catalog_path": catalog.relative_to(ROOT).as_posix()
        if catalog.is_relative_to(ROOT)
        else str(catalog),
        "catalog_sha256": _sha256(catalog),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--slug", choices=BOOKS, action="append")
    parser.add_argument(
        "--extractor-revision",
        choices=(
            EXTRACTOR_REVISION,
            "pymupdf_visual_regions_v3",
            "pymupdf_visual_regions_v4",
            "pymupdf_visual_regions_v5",
        ),
        default=EXTRACTOR_REVISION,
        help="Explicit candidate-only successor; default retains frozen v2 catalogs",
    )
    parser.add_argument(
        "--max-pages", type=int, help="Development sample; omitting scans every page"
    )
    args = parser.parse_args()
    if args.max_pages is not None and args.max_pages < 1:
        parser.error("--max-pages must be positive")
    output = args.out.resolve()
    if output == ROOT or not output.is_relative_to(ROOT):
        parser.error("--out must be a dedicated directory inside the project")
    books = args.slug or BOOKS
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"Existing manifest is immutable: {manifest_path}")
    started_at = datetime.now(timezone.utc).isoformat()
    results = [scan_book(slug, output, args.max_pages, args.extractor_revision) for slug in books]
    manifest = {
        "extractor_revision": args.extractor_revision,
        "pymupdf_version": pymupdf.VersionBind,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "scope": "full_originals" if args.max_pages is None else "bounded_development_sample",
        "books": results,
        "interpretation": (
            "Source-bound native geometry and candidate structures only. Figures require image review; "
            "tables need cell/reading-order review; formulas need symbol/layout review. "
            "No new answer evidence, chunk, vector or corpus release is published."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
