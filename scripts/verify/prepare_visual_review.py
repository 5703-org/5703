"""Audit real visual catalogs and prepare a source-bound, unlabeled 120-region review."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipelines.visual_regions import _identity  # noqa: E402

KINDS = ("figure_image", "table_candidate", "formula_candidate")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_book(book: dict) -> tuple[dict, dict[str, list[dict]]]:
    catalog = ROOT / book["catalog_path"]
    original = ROOT / book["source_path"]
    if sha256(catalog) != book["catalog_sha256"]:
        raise ValueError(f"Catalog hash differs: {book['slug']}")
    candidate_groups = defaultdict(list)
    counts = Counter()
    seen = set()
    failures = []
    clipped_images = 0
    offpage_images = 0
    with pymupdf.open(original) as source:
        if len(source) != book["physical_pages"]:
            raise ValueError(f"Original PDF page count differs: {book['slug']}")
        with gzip.open(catalog, "rt", encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                try:
                    item = json.loads(line)
                    if item["source_sha256"] != book["source_sha256"]:
                        raise ValueError("wrong source hash")
                    if item["region_id"] != _identity(item):
                        raise ValueError("region content changed")
                    if item["region_id"] in seen:
                        raise ValueError("duplicate region identity")
                    seen.add(item["region_id"])
                    page_number = item["physical_pdf_page"]
                    if not 1 <= page_number <= book["physical_pages"]:
                        raise ValueError("physical page out of range")
                    bbox = item["bbox_points"]
                    if len(bbox) != 4 or not all(math.isfinite(value) for value in bbox):
                        raise ValueError("invalid geometry")
                    page = source[page_number - 1]
                    rect = pymupdf.Rect(bbox)
                    if not rect.is_valid:
                        raise ValueError("invalid region rectangle")
                    if not page.rect.intersects(rect):
                        if (
                            item["kind"] == "figure_image"
                            and item["status"] == "needs_geometry_review"
                        ):
                            offpage_images += 1
                        else:
                            raise ValueError("region outside source page without isolation")
                    elif not page.rect.contains(rect):
                        raise ValueError("visible region was not clipped to the source page")
                    if item["kind"] == "figure_image" and item["details"].get("clipped_to_page"):
                        clipped_images += 1
                    if item["kind"] not in KINDS or not item["status"].startswith("needs_"):
                        raise ValueError("candidate was silently treated as verified")
                    counts[item["kind"]] += 1
                    candidate_groups[item["kind"]].append(item)
                except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
                    failures.append(
                        {"line": number, "error_type": type(exc).__name__, "reason": str(exc)}
                    )
    expected = Counter({key: value for key, value in book["counts"].items() if key in KINDS})
    if counts != expected:
        raise ValueError(
            f"Catalog counts differ from manifest: {book['slug']}: "
            f"actual={dict(counts)} expected={dict(expected)} sample_failures={failures[:5]}"
        )
    return {
        "slug": book["slug"],
        "count": sum(counts.values()),
        "by_kind": dict(counts),
        "unique_ids": len(seen),
        "clipped_images": clipped_images,
        "offpage_images": offpage_images,
        "failures": failures,
    }, candidate_groups


def spread_sample(items: list[dict], count: int) -> list[dict]:
    first_per_page = {}
    for item in sorted(items, key=lambda row: (row["physical_pdf_page"], row["region_id"])):
        first_per_page.setdefault(item["physical_pdf_page"], item)
    pages = list(first_per_page.values())
    if len(pages) < count:
        raise ValueError(f"Only {len(pages)} distinct source pages for {count} requested reviews")
    return [pages[round((index + 0.5) * len(pages) / count - 0.5)] for index in range(count)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    catalog_dir, output = args.catalog_dir.resolve(), args.out.resolve()
    if not catalog_dir.is_relative_to(ROOT) or not output.is_relative_to(ROOT):
        parser.error("Both locations must be inside the project")
    if (output / "manifest.json").exists():
        raise FileExistsError("Review manifest is immutable; use a new output directory")
    catalog_manifest = json.loads((catalog_dir / "manifest.json").read_text(encoding="utf-8"))
    if catalog_manifest["scope"] != "full_originals" or len(catalog_manifest["books"]) != 4:
        raise ValueError("A four-book full-source catalog is required")
    audit = []
    selected = []
    for book in catalog_manifest["books"]:
        result, groups = audit_book(book)
        audit.append(result)
        if result["failures"] or book["failed_pages"]:
            raise ValueError(f"Unresolved extraction or catalog audit failures: {book['slug']}")
        for kind in KINDS:
            selected.extend(spread_sample(groups[kind], 10))
    output.mkdir(parents=True, exist_ok=True)
    review_path = output / "review-sheet.csv"
    columns = [
        "region_id",
        "book",
        "source_sha256",
        "physical_pdf_page",
        "kind",
        "bbox_points",
        "native_text",
        "reviewer_id",
        "original_page_match",
        "structure_correct",
        "caption_or_symbol_correct",
        "notes",
    ]
    with review_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for item in selected:
            writer.writerow(
                {
                    "region_id": item["region_id"],
                    "book": item["book"],
                    "source_sha256": item["source_sha256"],
                    "physical_pdf_page": item["physical_pdf_page"],
                    "kind": item["kind"],
                    "bbox_points": json.dumps(item["bbox_points"]),
                    "native_text": item["native_text"],
                }
            )
    summary = {
        "source_manifest_path": catalog_dir.relative_to(ROOT).as_posix() + "/manifest.json",
        "source_manifest_sha256": sha256(catalog_dir / "manifest.json"),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "audit": audit,
        "selection": {
            "total": len(selected),
            "per_book_kind": 10,
            "method": "Deterministic spread across distinct physical pages, first region ID per page",
            "selection_ids": [item["region_id"] for item in selected],
            "label_status": "empty; no human or independent semantic review recorded",
        },
        "review_sheet": review_path.relative_to(ROOT).as_posix(),
        "review_sheet_sha256": sha256(review_path),
    }
    (output / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"audit": audit, "review_rows": len(selected)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
