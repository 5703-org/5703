"""Verify and optionally import source-bound visual candidates, without publishing them."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import Settings  # noqa: E402
from app.modules.knowledge.models import DocumentVersion, VisualRegion  # noqa: E402
from pipelines.visual_regions import _identity  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def original_source(book: dict, root: Path = ROOT) -> Path:
    """Resolve the scanned PDF in either the workspace or a portable corpus install."""
    digest = book["source_sha256"]
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("Invalid original source hash")
    candidates = (
        root / book["source_path"],
        root / "artifacts" / "storage" / "originals" / f"{digest}.pdf",
        root / "resources" / "official-corpus" / "storage" / "originals" / f"{digest}.pdf",
    )
    for candidate in candidates:
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise ValueError("Original source path escaped the project")
        if resolved.is_file():
            if sha256(resolved) != digest:
                raise ValueError("Original source hash changed")
            return resolved
    raise ValueError("Original source PDF is unavailable")


def verified_catalog(path: Path) -> tuple[dict, list[tuple[dict, list[dict]]]]:
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["scope"] != "full_originals" or len(manifest["books"]) != 4:
        raise ValueError("Only the complete four-book source audit is importable")
    books = []
    for book in manifest["books"]:
        if book["failed_pages"] or book["inspected_pages"] != book["physical_pages"]:
            raise ValueError(f"Incomplete original source scan: {book['slug']}")
        original = original_source(book)
        catalog = (ROOT / book["catalog_path"]).resolve()
        if not catalog.is_relative_to(path):
            raise ValueError("Catalog path escaped the project source and audit roots")
        if sha256(original) != book["source_sha256"] or sha256(catalog) != book["catalog_sha256"]:
            raise ValueError(f"Original source or candidate catalog hash changed: {book['slug']}")
        items, ids = [], set()
        counts = Counter()
        with gzip.open(catalog, "rt", encoding="utf-8") as stream:
            for line in stream:
                item = json.loads(line)
                if (
                    item["source_sha256"] != book["source_sha256"]
                    or item["region_id"] != _identity(item)
                    or item["region_id"] in ids
                    or not item["status"].startswith("needs_")
                    or not 1 <= item["physical_pdf_page"] <= book["physical_pages"]
                ):
                    raise ValueError(f"Invalid source identity or candidate state: {book['slug']}")
                ids.add(item["region_id"])
                counts[item["kind"]] += 1
                items.append(item)
        for kind in ("figure_image", "table_candidate", "formula_candidate"):
            if counts[kind] != book["counts"].get(kind, 0):
                raise ValueError(f"Candidate kind count differs from source audit: {book['slug']}")
        books.append((book, items))
    return manifest, books


def import_catalog(db: Session, books: list[tuple[dict, list[dict]]]) -> list[dict]:
    result = []
    for book, items in books:
        version = db.scalar(
            select(DocumentVersion).where(DocumentVersion.raw_hash == book["source_sha256"])
        )
        if version is None:
            raise ValueError(f"Original source has no registered database version: {book['slug']}")
        existing = {
            row.id: row.catalog_sha256
            for row in db.scalars(
                select(VisualRegion).where(VisualRegion.document_version_id == version.id)
            )
        }
        if any(value != book["catalog_sha256"] for value in existing.values()):
            raise ValueError(f"A different immutable visual catalog already exists: {book['slug']}")
        added = 0
        for item in items:
            if item["region_id"] in existing:
                continue
            db.add(
                VisualRegion(
                    id=item["region_id"],
                    document_version_id=version.id,
                    physical_page=item["physical_pdf_page"],
                    kind=item["kind"],
                    bbox=item["bbox_points"],
                    native_text=item["native_text"],
                    candidate_status=item["status"],
                    details=item["details"],
                    extractor_revision=item["extractor_revision"],
                    catalog_sha256=book["catalog_sha256"],
                )
            )
            added += 1
        result.append({"book": book["slug"], "expected": len(items), "added": added})
    db.flush()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--import", dest="commit", action="store_true")
    args = parser.parse_args()
    directory = args.catalog_dir.resolve()
    if not directory.is_relative_to(ROOT):
        parser.error("Catalog must be inside the project")
    manifest, books = verified_catalog(directory)
    print(
        json.dumps(
            {
                "catalog_revision": manifest["extractor_revision"],
                "verified_candidates": sum(len(items) for _, items in books),
                "write_requested": args.commit,
            }
        )
    )
    if not args.commit:
        return
    engine = create_engine(Settings().database_url)
    try:
        with Session(engine) as db:
            with db.begin():
                result = import_catalog(db, books)
            print(json.dumps(result))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
