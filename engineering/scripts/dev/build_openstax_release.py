"""Queue a genuine four-book release only after every current source run is ready."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.db.session import init_engine
from app.modules.identity.repository import get_user_by_email
from app.modules.knowledge.models import ActiveCorpus, ProcessingRun, CorpusRelease
from app.modules.knowledge.service import queue_release, processing_quality
from app.modules.answering.models import Job

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/openstax"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=EVIDENCE)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--name", default="cs30_openstax_v0.2 · official PDFs 2026-09-08 · E5 real")
    args = parser.parse_args()
    evidence_dir = args.evidence_dir
    settings = Settings()
    engine = init_engine(settings.database_url)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Formal corpus release requires PostgreSQL/pgvector")
    registry = json.loads(
        (args.registry or evidence_dir / "processing-registry.json").read_text(encoding="utf-8")
    )
    runs = [book["processing_id"] for book in registry["books"]]
    if len(set(runs)) != 4:
        raise RuntimeError("Exactly four distinct current book-processing runs are required")
    output = evidence_dir / "release-build.json"
    with sessionmaker(bind=engine, expire_on_commit=False)() as db:
        if output.exists():
            previous = json.loads(output.read_text())
            release = db.get(CorpusRelease, previous["release_id"])
            if release and release.manifest["processing_run_ids"] == runs:
                job = db.get(Job, previous["job_id"])
                print(
                    json.dumps(
                        {
                            "release_id": release.id,
                            "state": release.state,
                            "job_state": job.state,
                            "error": release.error,
                        }
                    )
                )
                return
            raise RuntimeError(
                "Existing release build evidence refers to a different source set; preserve it and select a new explicit build record"
            )
        for run_id in runs:
            report = processing_quality(db, run_id)
            if report["state"] != "ready" or report["counts"]["blocked_units"]:
                raise RuntimeError("A full-book run is not yet ready: " + run_id)
        admin = get_user_by_email(db, "admin@example.com")
        pointer = db.get(ActiveCorpus, 1)
        previous_active = pointer.release_id if pointer else None
        release, job = queue_release(
            db,
            admin.id,
            runs,
            registry["configuration_id"],
            args.name,
        )
        db.commit()
        result = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "release_id": release.id,
            "job_id": job.id,
            "configuration_id": registry["configuration_id"],
            "configuration": release.configuration,
            "processing_run_ids": runs,
            "previous_active_release_id": previous_active,
            "state_at_registration": release.state,
            "activation": "Not yet activated; full integrity and retrieval validation required",
            "answer_model_mode": settings.model_mode,
        }
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
