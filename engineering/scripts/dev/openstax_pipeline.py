"""Operate and export evidence for the acquired, complete official corpus."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.db.session import init_engine
from app.modules.identity.repository import get_user_by_email
from app.modules.knowledge import service
from app.modules.knowledge.models import ProcessingRun, Configuration
from app.modules.answering.models import Job

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/openstax"


def write(path, value):
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["register", "reprocess-reviewed", "status"])
    args = parser.parse_args()
    settings = Settings()
    engine = init_engine(settings.database_url)
    if engine.dialect.name != "postgresql":
        raise SystemExit("Official corpus operations require PostgreSQL/pgvector.")
    registry_path = EVIDENCE / "processing-registry.json"
    registry = (
        json.loads(registry_path.read_text(encoding="utf-8"))
        if registry_path.exists()
        else {"books": []}
    )
    with sessionmaker(bind=engine, expire_on_commit=False)() as db:
        if args.action in ("register", "reprocess-reviewed"):
            if args.action == "reprocess-reviewed":
                initial = EVIDENCE / "initial-v3"
                initial.mkdir(exist_ok=True)
                if not (initial / "processing-registry.json").exists():
                    write(initial / "processing-registry.json", registry)
                    for book in registry["books"]:
                        write(
                            initial / f"{book['slug']}-quality.json",
                            service.processing_quality(db, book["processing_id"]),
                        )
                registry.setdefault("processing_history", []).append(
                    {
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                        "books": registry["books"],
                    }
                )
            spec = json.loads((ROOT / "configs/corpus/e5_cuda.json").read_text())
            config = service.config_create(db, spec["kind"], spec["name"], spec["values"])
            admin = get_user_by_email(db, "admin@example.com")
            if not admin or admin.status != "active" or admin.role.name != "admin":
                raise RuntimeError("An active local administrator is required.")
            registry["configuration_id"] = config.id
            registry["configuration"] = config.values
            registry["database"] = str(engine.url.set(password=None))
            registry["answer_model_mode"] = settings.model_mode
            db.commit()
            acquisitions = sorted(EVIDENCE.glob("*-acquisition.json"))
            if len(acquisitions) != 4:
                raise RuntimeError("All four official acquisition records are required.")
            for file in acquisitions:
                asset = json.loads(file.read_text())
                raw_path = ROOT / asset["raw_path"]
                raw = raw_path.read_bytes()
                if (
                    len(raw) != asset["size_bytes"]
                    or hashlib.sha256(raw).hexdigest() != asset["sha256"]
                ):
                    raise RuntimeError(f"Original verification failed: {asset['slug']}")
                document, version, duplicate = service.ingest(
                    db,
                    settings,
                    admin.id,
                    raw_path.name,
                    raw,
                    asset["title"],
                    f"Official PDF acquired {asset['acquired_at'][:10]}; digital ISBN {asset['digital_isbn_13']}",
                    asset["final_url"],
                    f"Catalog: {asset['license_name']} {asset['license_version']}; {asset['license_url']}. Embedded PDF terms are separately recorded in source inspection evidence.",
                )
                run_config = dict(config.values)
                exclusions = None
                if args.action == "reprocess-reviewed":
                    decisions = json.loads(
                        (EVIDENCE / "pdf-low-text-decisions.json").read_text(encoding="utf-8")
                    )
                    review_book = next(
                        book for book in decisions["books"] if book["slug"] == asset["slug"]
                    )
                    if review_book["pdf_sha256"] != asset["sha256"]:
                        raise RuntimeError("Page review belongs to different original bytes")
                    run_config["page_reviews"] = []
                    for page in review_book["pages"]:
                        if page["category"] == "substantive_visual_unextracted":
                            continue
                        if not (ROOT / page["review_evidence"]).is_file():
                            raise RuntimeError("Required page-review evidence is missing")
                        run_config["page_reviews"].append(
                            {
                                "physical_page": page["physical_pdf_page"],
                                "pdf_sha256": asset["sha256"],
                                "normalized_native_text_sha256": hashlib.sha256(
                                    " ".join(page["text"].split()).encode()
                                ).hexdigest(),
                                "category": page["category"],
                                "reason": page["reason"],
                                "review_evidence": page["review_evidence"],
                                "review_method": page["review_method"],
                                "printed_page": page["printed_page"],
                            }
                        )
                    image_manifest = EVIDENCE / "image-transcription-manifest.json"
                    if image_manifest.is_file():
                        transcriptions = json.loads(image_manifest.read_text(encoding="utf-8"))
                        run_config["source_supplements"] = [
                            item
                            for item in transcriptions["entries"]
                            if item["pdf_sha256"] == asset["sha256"]
                        ]
                        run_config["image_transcription_revision"] = "ocr_review_line_paragraphs_v1"
                    elif asset["slug"] == "chemistry-2e":
                        supplement = json.loads(
                            (EVIDENCE / "chemistry-publisher-supplement.json").read_text(
                                encoding="utf-8"
                            )
                        )
                        run_config["source_supplements"] = supplement["entries"]
                run, job = service.queue_process(db, document.id, admin.id, run_config, exclusions)
                db.commit()
                result = {
                    "slug": asset["slug"],
                    "title": asset["title"],
                    "sha256": asset["sha256"],
                    "document_id": document.id,
                    "document_version_id": version.id,
                    "processing_id": run.id,
                    "job_id": job.id,
                    "config_hash": run.config_hash,
                    "raw_path": asset["raw_path"],
                    "database_storage_path": version.storage_path,
                    "storage_root": str(Path(settings.storage_root).resolve()),
                    "acquisition_evidence": file.relative_to(ROOT).as_posix(),
                    "duplicate_original": duplicate,
                }
                registry["books"] = [
                    row for row in registry["books"] if row["slug"] != asset["slug"]
                ] + [result]
                registry["updated_at"] = datetime.now(timezone.utc).isoformat()
                write(registry_path, registry)
                print(json.dumps(result), flush=True)
                del raw
        else:
            result = {"observed_at": datetime.now(timezone.utc).isoformat(), "books": []}
            for item in registry["books"]:
                run, job = db.get(ProcessingRun, item["processing_id"]), db.get(Job, item["job_id"])
                counts = {
                    name: value
                    for name, value in run.counts.items()
                    if name != "source_unit_hashes"
                }
                row = {
                    **item,
                    "processing_state": run.state,
                    "job_state": job.state,
                    "stage": job.stage,
                    "counts": counts,
                    "processing_error": run.error,
                    "job_error": job.error,
                }
                result["books"].append(row)
                if run.state in ("ready", "quarantined"):
                    quality = service.processing_quality(db, run.id)
                    write(EVIDENCE / f"{item['slug']}-quality.json", quality)
                    (EVIDENCE / "runs").mkdir(exist_ok=True)
                    saved_quality = EVIDENCE / f"runs/{run.id}-quality.json"
                    if not saved_quality.exists():
                        write(saved_quality, quality)
                print(
                    json.dumps(
                        {
                            "book": item["slug"],
                            "state": run.state,
                            "job": job.state,
                            "stage": job.stage,
                            "counts": counts,
                            "error": run.error or job.error,
                        }
                    ),
                    flush=True,
                )
            write(EVIDENCE / "processing-status.json", result)


if __name__ == "__main__":
    main()
