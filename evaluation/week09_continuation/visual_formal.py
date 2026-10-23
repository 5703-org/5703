"""Frozen, source-bound visual-region mechanical evaluation.

This study checks original-PDF provenance, locators, native text, table shape,
database identity and administrator source viewing. It does not infer figure
meaning, certify formula notation or score downstream question answering.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random

import httpx
import pymupdf
from dotenv import dotenv_values
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "evidence/week09-continuation/20260930"
REVIEW = SOURCE / "visual-review-v2/review-sheet.csv"
CURRENT = SOURCE / "visual-full-attempt2/manifest.json"
PREVIOUS = SOURCE / "visual-full-attempt1/manifest.json"
KINDS = ("figure_image", "table_candidate", "formula_candidate")
SCHEMA = "week09_visual_mechanical_paired_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _catalog(book: dict) -> list[dict]:
    path = ROOT / book["catalog_path"]
    if sha256(path) != book["catalog_sha256"]:
        raise ValueError(f"Visual catalog changed: {book['slug']}")
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def _pair_key(region: dict) -> tuple:
    details = region["details"]
    return (
        region["physical_pdf_page"],
        region["kind"],
        region["native_text"],
        details.get("image_md5") if region["kind"] == "figure_image" else details.get("label"),
    )


def _closest(region: dict, predecessors: list[dict]) -> dict:
    matches = [row for row in predecessors if _pair_key(row) == _pair_key(region)]
    if not matches:
        raise ValueError(f"No old-region counterpart: {region['region_id']}")
    return min(
        matches,
        key=lambda row: sum(abs(x - y) for x, y in zip(row["bbox_points"], region["bbox_points"])),
    )


def freeze(output: Path) -> dict:
    """Freeze the earlier unlabeled 120-region selection before new checks."""
    if output.exists():
        raise FileExistsError(f"Frozen visual study already exists: {output}")
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    previous = json.loads(PREVIOUS.read_text(encoding="utf-8"))
    if current["scope"] != "full_originals" or previous["scope"] != "full_originals":
        raise ValueError("Both four-book full-source catalogs are required")
    if len(current["books"]) != 4 or len(previous["books"]) != 4:
        raise ValueError("The full four-book corpus is required")
    with REVIEW.open(newline="", encoding="utf-8-sig") as stream:
        selected = list(csv.DictReader(stream))
    if len(selected) != 120 or any(
        row[field]
        for row in selected
        for field in (
            "reviewer_id",
            "original_page_match",
            "structure_correct",
            "caption_or_symbol_correct",
            "notes",
        )
    ):
        raise ValueError("The prior 120-region review must remain entirely unlabeled")
    by_id: dict[str, tuple[dict, dict, dict]] = {}
    for new_book, old_book in zip(current["books"], previous["books"]):
        if (new_book["slug"], new_book["source_sha256"]) != (
            old_book["slug"],
            old_book["source_sha256"],
        ):
            raise ValueError("The paired scans do not use the same original PDF")
        original = ROOT / new_book["source_path"]
        if sha256(original) != new_book["source_sha256"]:
            raise ValueError(f"Original PDF changed: {new_book['slug']}")
        old_regions = _catalog(old_book)
        for region in _catalog(new_book):
            by_id[region["region_id"]] = (new_book, region, _closest(region, old_regions))
    selected_ids = {row["region_id"] for row in selected}
    if len(selected_ids) != 120 or not selected_ids <= set(by_id):
        raise ValueError("The earlier review selection does not match the catalog")
    source_groups = sorted(
        {(by_id[row["region_id"]][0]["slug"], int(row["physical_pdf_page"])) for row in selected}
    )
    random.Random(20260930).shuffle(source_groups)
    splits = {
        group: "development" if i < 24 else "pilot" if i < 48 else "reserved"
        for i, group in enumerate(source_groups)
    }
    cases = []
    for row in selected:
        book, region, old = by_id[row["region_id"]]
        if (
            row["book"] != book["title"]
            or row["source_sha256"] != book["source_sha256"]
            or int(row["physical_pdf_page"]) != region["physical_pdf_page"]
            or row["kind"] != region["kind"]
            or row["native_text"] != region["native_text"]
            or json.loads(row["bbox_points"]) != region["bbox_points"]
        ):
            raise ValueError(f"Review sheet changed from the source catalog: {row['region_id']}")
        group = (book["slug"], region["physical_pdf_page"])
        cases.append(
            {
                "id": f"VIS-{len(cases) + 1:03d}",
                "region_id": region["region_id"],
                "prior_region_id": old["region_id"],
                "book": book["title"],
                "slug": book["slug"],
                "source_url": book["official_pdf_url"],
                "source_sha256": book["source_sha256"],
                "catalog_sha256": book["catalog_sha256"],
                "prior_catalog_sha256": next(
                    b["catalog_sha256"] for b in previous["books"] if b["slug"] == book["slug"]
                ),
                "page": region["physical_pdf_page"],
                "kind": region["kind"],
                "bbox": region["bbox_points"],
                "prior_bbox": old["bbox_points"],
                "native_text": region["native_text"],
                "details": region["details"],
                "candidate_status": region["status"],
                "split": splits[group],
                "split_group": f"{book['slug']}:physical-pdf-page-{region['physical_pdf_page']}",
                "label_provenance": "unlabelled",
            }
        )
    summary = {
        "schema": SCHEMA + "_freeze",
        "source_manifest_sha256": sha256(CURRENT),
        "prior_manifest_sha256": sha256(PREVIOUS),
        "review_selection_sha256": sha256(REVIEW),
        "evaluator_sha256": sha256(Path(__file__)),
        "split_policy": "Book plus physical PDF page; 24/24/remaining page groups, seeded shuffle 20260930",
        "split_warning": "Pages are disjoint; chapter/concept and cross-book topics are not independently labelled.",
        "cases": cases,
        "human_labels": 0,
        "semantic_answer_labels": 0,
    }
    output.mkdir(parents=True)
    (output / "freeze.json").write_bytes(canonical(summary))
    (output / "freeze.sha256").write_text(
        sha256(output / "freeze.json") + "  freeze.json\n", encoding="utf-8"
    )
    return {
        "cases": len(cases),
        "page_groups": len(source_groups),
        "splits": dict(Counter(c["split"] for c in cases)),
        "freeze_sha256": sha256(output / "freeze.json"),
    }


def _line_found(page: pymupdf.Page, value: str) -> bool:
    if not value:
        return True
    flags = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    for block in page.get_text("dict", flags=flags)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text_value = "".join(span["text"] for span in line.get("spans", [])).strip()
            if text_value == value:
                return True
    return False


def _geometry(page: pymupdf.Page, case: dict) -> dict:
    box = pymupdf.Rect(case["bbox"])
    old = pymupdf.Rect(case["prior_bbox"])
    visible = box.is_valid and page.rect.contains(box)
    prior_visible = old.is_valid and page.rect.contains(old)
    image_identity = None
    if case["kind"] == "figure_image":
        digest = case["details"]["image_md5"]
        raw_bbox = pymupdf.Rect(case["details"]["raw_bbox_points"])
        image_identity = any(
            image["digest"].hex() == digest
            and pymupdf.Rect(image["bbox"]).is_valid
            and max(abs(x - y) for x, y in zip(image["bbox"], raw_bbox)) <= 0.002
            for image in page.get_image_info(hashes=True)
        )
    return {
        "candidate_inside_visible_page": bool(visible),
        "previous_inside_visible_page": bool(prior_visible),
        "native_text_exact_line_recovered": _line_found(page, case["native_text"]),
        "image_bytes_and_raw_rectangle_recovered": image_identity,
    }


def _table_shape(case: dict) -> dict | None:
    if case["kind"] != "table_candidate":
        return None
    details = case["details"]
    cells = details.get("cells")
    if cells is None:
        return {"reconstructed": False, "shape_consistent": None, "nonempty_cells": None}
    rows, columns = details.get("rows"), details.get("columns")
    shape = (
        isinstance(cells, list)
        and isinstance(rows, int)
        and isinstance(columns, int)
        and rows > 0
        and columns > 0
        and len(cells) == rows
        and all(isinstance(row, list) and len(row) == columns for row in cells)
    )
    return {
        "reconstructed": True,
        "shape_consistent": shape,
        "nonempty_cells": sum(
            bool(str(cell).strip()) for row in cells for cell in row if cell is not None
        ),
    }


def _database_rows(cases: list[dict], stage_root: Path) -> tuple[dict[str, dict], dict]:
    env = dotenv_values(stage_root / ".env")
    database_url = env.get("DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql+"):
        raise ValueError("The isolated PostgreSQL connection is unavailable")
    engine = create_engine(database_url, hide_parameters=True, connect_args={"connect_timeout": 10})
    try:
        with engine.connect() as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            if db.scalar(text("SHOW transaction_read_only")) != "on":
                raise ValueError("Visual evaluation database transaction is not read-only")
            release = db.scalar(text("SELECT release_id FROM active_corpus WHERE id=1"))
            if not release:
                raise ValueError("No active release exists in the isolated database")
            total = db.scalar(text("SELECT count(*) FROM visual_regions"))
            published = db.scalar(text("SELECT count(*) FROM visual_region_reviews"))
            rows = {}
            for case in cases:
                row = (
                    db.execute(
                        text("""
                    SELECT vr.id, vr.physical_page, vr.kind, vr.bbox, vr.native_text,
                           vr.details, vr.candidate_status, vr.catalog_sha256,
                           dv.raw_hash, d.title,
                           (SELECT count(*) FROM visual_region_reviews rr WHERE rr.region_id=vr.id) AS reviews
                    FROM visual_regions vr
                    JOIN document_versions dv ON dv.id=vr.document_version_id
                    JOIN documents d ON d.id=dv.document_id
                    WHERE vr.id=:region_id
                """),
                        {"region_id": case["region_id"]},
                    )
                    .mappings()
                    .one_or_none()
                )
                rows[case["id"]] = dict(row) if row else {}
            return rows, {
                "active_release_id": release,
                "database_read_only": True,
                "visual_candidate_count": total,
                "visual_review_count": published,
            }
    finally:
        engine.dispose()


def _api_check(cases: list[dict], stage_root: Path, api_port: int) -> dict:
    password = (
        (stage_root / ".secrets/initial-admin-password.txt").read_text(encoding="utf-8").strip()
    )
    samples = [
        next(case for case in cases if case["book"] == book and case["kind"] == kind)
        for book in sorted({case["book"] for case in cases})
        for kind in KINDS
    ]
    with httpx.Client(base_url=f"http://127.0.0.1:{api_port}", timeout=30) as client:
        login = client.post(
            "/api/v1/auth/login", json={"email": "admin@example.com", "password": password}
        )
        login.raise_for_status()
        headers = {"Authorization": "Bearer " + login.json()["data"]["access_token"]}
        outcomes = []
        for case in samples:
            detail = client.get(
                f"/api/v1/admin/source-quality/visual-regions/{case['region_id']}", headers=headers
            )
            page = client.get(
                f"/api/v1/admin/source-quality/visual-regions/{case['region_id']}/original-page",
                headers=headers,
            )
            payload = detail.json().get("data", {}) if detail.status_code == 200 else {}
            outcomes.append(
                {
                    "id": case["id"],
                    "kind": case["kind"],
                    "detail_http": detail.status_code,
                    "detail_exact_region": payload.get("id") == case["region_id"],
                    "detail_answer_eligible": payload.get("answer_evidence_eligible"),
                    "original_page_http": page.status_code,
                    "original_page_png": page.content[:8] == b"\x89PNG\r\n\x1a\n",
                }
            )
        return {"sample_count": len(samples), "outcomes": outcomes}


def run(frozen_dir: Path, output: Path, stage_root: Path, api_port: int) -> dict:
    if output.exists():
        raise FileExistsError(f"Visual outcome already exists: {output}")
    frozen = json.loads((frozen_dir / "freeze.json").read_text(encoding="utf-8"))
    if frozen.get("schema") != SCHEMA + "_freeze":
        raise ValueError("Unknown frozen visual experiment")
    if sha256(Path(__file__)) != frozen["evaluator_sha256"]:
        raise ValueError("Visual evaluator changed since freeze")
    if (
        sha256(CURRENT) != frozen["source_manifest_sha256"]
        or sha256(PREVIOUS) != frozen["prior_manifest_sha256"]
        or sha256(REVIEW) != frozen["review_selection_sha256"]
    ):
        raise ValueError("Frozen source or selected IDs changed")
    books = {
        book["slug"]: book for book in json.loads(CURRENT.read_text(encoding="utf-8"))["books"]
    }
    for book in books.values():
        if (
            sha256(ROOT / book["source_path"]) != book["source_sha256"]
            or sha256(ROOT / book["catalog_path"]) != book["catalog_sha256"]
        ):
            raise ValueError("Official PDF or derived catalog changed")
    db_rows, database = _database_rows(frozen["cases"], stage_root)
    opened = {slug: pymupdf.open(ROOT / book["source_path"]) for slug, book in books.items()}
    observations = []
    try:
        for case in frozen["cases"]:
            page = opened[case["slug"]][case["page"] - 1]
            location = _geometry(page, case)
            row = db_rows[case["id"]]
            db_match = bool(row) and all(
                (
                    row["id"] == case["region_id"],
                    row["physical_page"] == case["page"],
                    row["kind"] == case["kind"],
                    row["bbox"] == case["bbox"],
                    row["native_text"] == case["native_text"],
                    row["details"] == case["details"],
                    row["candidate_status"] == case["candidate_status"],
                    row["catalog_sha256"] == case["catalog_sha256"],
                    row["raw_hash"] == case["source_sha256"],
                    row["title"] == case["book"],
                    row["reviews"] == 0,
                )
            )
            observations.append(
                {
                    "id": case["id"],
                    "split": case["split"],
                    "book": case["book"],
                    "kind": case["kind"],
                    "region_id": case["region_id"],
                    "page": case["page"],
                    **location,
                    "table": _table_shape(case),
                    "database_identity_exact_and_unreviewed": db_match,
                }
            )
    finally:
        for pdf in opened.values():
            pdf.close()
    api = _api_check(frozen["cases"], stage_root, api_port)
    counts = Counter((row["split"], row["kind"]) for row in observations)
    result = {
        "schema": SCHEMA + "_outcomes",
        "freeze_sha256": sha256(frozen_dir / "freeze.json"),
        "evaluator_sha256": sha256(Path(__file__)),
        "paired_cases": len(observations),
        "split_kind_counts": {
            f"{split}/{kind}": count for (split, kind), count in sorted(counts.items())
        },
        "candidate_inside_visible_page": sum(
            row["candidate_inside_visible_page"] for row in observations
        ),
        "previous_inside_visible_page": sum(
            row["previous_inside_visible_page"] for row in observations
        ),
        "native_text_exact_line_recovered": sum(
            row["native_text_exact_line_recovered"] for row in observations
        ),
        "image_identity_recovered": sum(
            row["image_bytes_and_raw_rectangle_recovered"] is True for row in observations
        ),
        "tables_reconstructed": sum(
            row["table"] is not None and row["table"]["reconstructed"] for row in observations
        ),
        "tables_unresolved": sum(
            row["table"] is not None and not row["table"]["reconstructed"] for row in observations
        ),
        "table_shapes_consistent": sum(
            row["table"] is not None and row["table"]["shape_consistent"] is True
            for row in observations
        ),
        "database_exact_and_unreviewed": sum(
            row["database_identity_exact_and_unreviewed"] for row in observations
        ),
        "database": database,
        "api": api,
        "human_semantic_labels": 0,
        "answer_question_outcomes": 0,
        "semantic_accuracy": None,
        "conclusion_scope": "Mechanical provenance, locator and structural checks only; no figure semantics, notation, reading-order or downstream QA correctness conclusion.",
        "observations": observations,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical(result))
    return {k: value for k, value in result.items() if k not in {"observations", "api"}}


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("--out", type=Path, required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--freeze", type=Path, required=True)
    run_parser.add_argument("--out", type=Path, required=True)
    run_parser.add_argument("--stage-root", type=Path, required=True)
    run_parser.add_argument("--api-port", type=int, default=18847)
    args = parser.parse_args()
    outcome = (
        freeze(args.out.resolve())
        if args.action == "freeze"
        else run(
            args.freeze.resolve(), args.out.resolve(), args.stage_root.resolve(), args.api_port
        )
    )
    print(json.dumps(outcome, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
