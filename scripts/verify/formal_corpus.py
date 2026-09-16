"""Read-only, complete source/chunk accounting plus a deterministic 50-item sample."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from pypdf import PdfReader
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.db.session import init_engine
from app.modules.knowledge.models import Document, DocumentVersion, ProcessingRun, SourceUnit, Chunk
from app.modules.answering.models import Job
from app.modules.knowledge.service import digest, processing_quality, _validate_chunk
from retrieval.embedding import make_embedding

SEED = "cs30-four-book-source-sample-v1-2026-09-08"
EXPECTED = {
    "anatomy-and-physiology-2e": 1347,
    "biology-2e": 1475,
    "chemistry-2e": 1203,
    "concepts-biology": 613,
}
SUPPLEMENT_CODES = {"PDF_IMAGE_TRANSCRIPTION", "PUBLISHER_ALTERNATIVE_TEXT"}


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default="evidence/openstax/processing-registry.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    registry_path = Path(args.registry)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if {b["slug"] for b in registry["books"]} != set(EXPECTED) or len(registry["books"]) != 4:
        raise ValueError("The registry must contain exactly the four source-approved books.")
    settings = Settings()
    engine = init_engine(settings.database_url)
    if engine.dialect.name != "postgresql":
        raise ValueError("Formal corpus verification requires PostgreSQL.")
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "registry": args.registry,
        "registry_sha256": file_sha(registry_path),
        "expected_physical_pages": sum(EXPECTED.values()),
        "status": "pending",
        "books": [],
        "errors": [],
        "sample": [],
        "sample_protocol": {
            "seed": SEED,
            "method": "SHA-256 ordering over seed, original PDF hash, processing ID and chunk ID; balanced quotas 13/13/12/12 in slug order. Include one deterministically selected chunk from every recovery page and one internal furniture-exclusion boundary per book before filling by hash order.",
            "scientific_quality_claim": False,
            "source_checks": "Every chunk is checked; sample additionally re-extracts original physical PDF pages and compares their native text to retained source units.",
        },
    }
    book_data = []
    with sessionmaker(bind=engine)() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        pending = []
        for item in sorted(registry["books"], key=lambda b: b["slug"]):
            run = db.get(ProcessingRun, item["processing_id"])
            job = db.get(Job, item["job_id"])
            status = {
                "slug": item["slug"],
                "processing_id": item["processing_id"],
                "processing_state": run.state if run else None,
                "job_state": job.state if job else None,
                "error": run.error if run else "missing run",
            }
            if (
                not run
                or run.state not in ("ready", "quarantined", "failed")
                or not job
                or job.state in ("queued", "running")
            ):
                pending.append(status)
            output["books"].append(status)
        if pending:
            output["pending"] = pending
        else:
            configurations = {
                digest(db.get(ProcessingRun, b["processing_id"]).configuration): db.get(
                    ProcessingRun, b["processing_id"]
                ).configuration
                for b in registry["books"]
            }
            # Load the actual pinned model once. All book configs must use the
            # same fixed model/tokenizer identity, but keep their review settings.
            first = next(iter(configurations.values()))
            identity = lambda c: tuple(
                c.get(k)
                for k in (
                    "embedding_provider",
                    "embedding_model",
                    "embedding_revision",
                    "tokenizer_revision",
                    "dimension",
                )
            )
            if first["embedding_provider"] != "e5" or any(
                identity(c) != identity(first) for c in configurations.values()
            ):
                raise ValueError(
                    "Formal sources require a consistent, real pinned E5/tokenizer identity."
                )
            embedder = make_embedding(first)
            output["tokenizer"] = {
                "model": first["embedding_model"],
                "revision": first["tokenizer_revision"],
                "window": embedder.model.max_seq_length,
                "device": str(embedder.model.device),
                "dimension": embedder.dimension,
            }
            for item, status in zip(
                sorted(registry["books"], key=lambda b: b["slug"]), output["books"]
            ):
                run = db.get(ProcessingRun, item["processing_id"])
                version = db.get(DocumentVersion, run.document_version_id)
                document = db.get(Document, version.document_id)
                path = (Path(settings.storage_root) / version.storage_path).resolve()
                if not path.is_relative_to(Path(settings.storage_root).resolve()):
                    raise ValueError("Source path escaped storage.")
                if file_sha(path) != item["sha256"] or version.raw_hash != item["sha256"]:
                    raise ValueError("Original PDF identity changed.")
                if document.id != item["document_id"] or version.id != item["document_version_id"]:
                    raise ValueError("Registry lineage differs from database.")
                if not document.active or document.revoked:
                    raise ValueError("A formal source is currently unavailable.")
                if (
                    run.config_hash != digest(run.configuration)
                    or run.config_hash != item["config_hash"]
                ):
                    raise ValueError("Processing configuration identity changed.")
                pdf = PdfReader(path, strict=True)
                page_count = len(pdf.pages)
                if page_count != EXPECTED[item["slug"]]:
                    raise ValueError("Actual PDF page count differs from source inspection.")
                report = processing_quality(db, run.id)
                units = list(
                    db.scalars(
                        select(SourceUnit)
                        .where(SourceUnit.processing_id == run.id)
                        .order_by(SourceUnit.sequence)
                    )
                )
                lookup = {u.id: u for u in units}
                by_page = defaultdict(list)
                for unit in units:
                    by_page[unit.page].append(unit)
                missing = sorted(set(range(1, page_count + 1)) - set(by_page))
                extra = sorted(set(by_page) - set(range(1, page_count + 1)))
                if missing or extra:
                    output["errors"].append(
                        {"slug": item["slug"], "missing_pages": missing, "extra_pages": extra}
                    )
                chunks = list(
                    db.scalars(
                        select(Chunk).where(Chunk.processing_id == run.id).order_by(Chunk.id)
                    )
                )
                errors = []
                max_body = max_input = 0
                used_units = set()
                for chunk in chunks:
                    try:
                        if chunk.document_id != document.id:
                            raise ValueError("Wrong source document")
                        _validate_chunk(chunk, lookup)
                        body = embedder.count_input(chunk.text)
                        total = embedder.count_input(
                            "passage: " + chunk.section + "\n" + chunk.text
                        )
                        if (
                            body != chunk.tokens
                            or body > run.configuration["cap"]
                            or total > embedder.model.max_seq_length
                        ):
                            raise ValueError(
                                f"Token limits/count mismatch: body {body}, stored {chunk.tokens}, input {total}"
                            )
                        max_body = max(max_body, body)
                        max_input = max(max_input, total)
                        used_units.update(s["unit_id"] for s in chunk.spans)
                    except Exception as exc:
                        errors.append({"chunk_id": chunk.id, "error": str(exc)})
                pages = []
                for number in range(1, page_count + 1):
                    current = by_page[number]
                    native = [
                        u
                        for u in current
                        if not any(i["code"] in SUPPLEMENT_CODES for i in u.issues)
                    ]
                    if not native:
                        errors.append({"page": number, "error": "No retained native source unit"})
                    pages.append(
                        {
                            "physical_page": number,
                            "native_units": len(native),
                            "supplement_units": len(current) - len(native),
                            "quality_counts": dict(Counter(u.quality for u in current)),
                            "issue_codes": sorted({i["code"] for u in current for i in u.issues}),
                            "chunked_unit_count": sum(u.id in used_units for u in current),
                        }
                    )
                unused = [
                    u.id
                    for u in units
                    if u.quality == "ready" and u.cleaned_text.strip() and u.id not in used_units
                ]
                if run.state == "ready" and unused:
                    errors.append({"error": "Usable source units lack chunks", "unit_ids": unused})
                if len(chunks) != run.counts.get("chunks"):
                    errors.append({"error": "Chunk count differs from processing record"})
                if run.state != "ready":
                    errors.append(
                        {
                            "error": "Processing is not ready",
                            "state": run.state,
                            "blocked_units": report["counts"]["blocked_units"],
                        }
                    )
                status.update(
                    {
                        "source_title": document.title,
                        "pdf_sha256": version.raw_hash,
                        "physical_page_count": page_count,
                        "accounted_physical_pages": len(by_page),
                        "counts": report["counts"],
                        "chunk_count": len(chunks),
                        "all_chunk_text_spans_hashes_checked": bool(chunks) and not errors,
                        "maximum_body_tokens": max_body,
                        "maximum_input_tokens": max_input,
                        "quality_hash_status": report["persisted_hash_status"],
                        "errors": errors,
                        "pages": pages,
                    }
                )
                output["errors"].extend({"slug": item["slug"], **error} for error in errors)
                book_data.append((item, run, units, by_page, chunks, pdf))
                print(
                    json.dumps(
                        {
                            "slug": item["slug"],
                            "state": run.state,
                            "pages": page_count,
                            "units": len(units),
                            "chunks_checked": len(chunks),
                            "errors": len(errors),
                        }
                    ),
                    flush=True,
                )
            if not output["errors"]:
                for index, (item, run, units, by_page, chunks, pdf) in enumerate(book_data):
                    quota = 13 if index < 2 else 12
                    rank = lambda c: sha(f"{SEED}:{item['sha256']}:{run.id}:{c.id}")
                    ordered = sorted(chunks, key=rank)
                    selected = {}
                    recovery_pages = sorted(
                        {
                            u.page
                            for u in units
                            if any(i["code"] in SUPPLEMENT_CODES for i in u.issues)
                        }
                    )
                    recovery_ids = {
                        u.id for u in units if any(i["code"] in SUPPLEMENT_CODES for i in u.issues)
                    }
                    for page in recovery_pages:
                        candidates = [
                            c
                            for c in ordered
                            if page in c.pages
                            and any(s["unit_id"] in recovery_ids for s in c.spans)
                        ]
                        if not candidates:
                            raise ValueError(f"No recovery chunk for {item['slug']}:{page}")
                        selected.setdefault(candidates[0].id, (candidates[0], []))[1].append(
                            f"recovery_page_{page}"
                        )
                    furniture_pages = sorted(
                        {
                            u.page
                            for u in units
                            if any(i.get("category") == "furniture_only" for i in u.issues)
                        }
                    )
                    boundary_candidates = [
                        c
                        for c in ordered
                        if any(p + 1 in c.pages or p - 1 in c.pages for p in furniture_pages)
                    ]
                    if boundary_candidates:
                        chosen = boundary_candidates[0]
                        selected.setdefault(chosen.id, (chosen, []))[1].append(
                            "adjacent_to_reviewed_furniture_only_page"
                        )
                    for chunk in ordered:
                        if len(selected) >= quota:
                            break
                        if chunk.id not in selected:
                            selected[chunk.id] = (chunk, ["deterministic_hash_sample"])
                    if len(selected) != quota:
                        raise ValueError("Cannot satisfy the fixed balanced sample quota.")
                    native_checks = {}
                    for chunk, reasons in selected.values():
                        for page in chunk.pages:
                            if page not in native_checks:
                                native = "".join(
                                    u.raw_text
                                    for u in by_page[page]
                                    if not any(i["code"] in SUPPLEMENT_CODES for i in u.issues)
                                )
                                actual = pdf.pages[page - 1].extract_text() or ""
                                native_checks[page] = {
                                    "physical_page": page,
                                    "matches_retained_native_text": actual == native,
                                    "original_extracted_hash": sha(actual),
                                    "retained_native_hash": sha(native),
                                }
                                if actual != native:
                                    output["errors"].append(
                                        {
                                            "slug": item["slug"],
                                            "page": page,
                                            "error": "Sample original native extraction does not reconstruct retained units",
                                        }
                                    )
                        output["sample"].append(
                            {
                                "slug": item["slug"],
                                "processing_id": run.id,
                                "pdf_sha256": item["sha256"],
                                "chunk_id": chunk.id,
                                "selection_reason": reasons,
                                "section": chunk.section,
                                "physical_pages": chunk.pages,
                                "text": chunk.text,
                                "text_hash": chunk.text_hash,
                                "body_tokens": chunk.tokens,
                                "actual_input_tokens": embedder.count_input(
                                    "passage: " + chunk.section + "\n" + chunk.text
                                ),
                                "spans": chunk.spans,
                                "original_pdf_checks": [native_checks[p] for p in chunk.pages],
                            }
                        )
                if len(output["sample"]) != 50:
                    raise ValueError("Formal source sample must contain exactly 50 chunks.")
            output["status"] = "passed" if not output["errors"] else "failed"
        db.rollback()
    output["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": output["status"],
                "output": str(destination),
                "sample_count": len(output["sample"]),
                "errors": len(output["errors"]),
                "elapsed_seconds": output["elapsed_seconds"],
            }
        )
    )
    return 0 if output["status"] == "passed" else 2 if output["status"] == "pending" else 1


if __name__ == "__main__":
    raise SystemExit(main())
