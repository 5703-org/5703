"""Build a separate R3 comparison release without changing the active pointer."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.db.session import init_engine
from app.modules.identity.models import User
from app.modules.answering.models import Job
from app.modules.knowledge.models import ActiveCorpus, CorpusRelease
from app.modules.knowledge.service import _release_rows, config_create, queue_release
from app.worker import run_once

BASELINE = "39483e7f-efbe-42e7-855e-469fd924383e"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="evidence/retrieval/comparison-release-v2.json")
    args = parser.parse_args()
    output = Path(args.output)
    settings = Settings()
    engine = init_engine(settings.database_url)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    if output.exists():
        prior = json.loads(output.read_text(encoding="utf-8"))
        if prior["status"] != "validated_unactivated":
            raise RuntimeError(
                "Saved comparison needs reconciliation; no duplicate job will be queued"
            )
        with factory() as db:
            current = db.get(CorpusRelease, prior["release_id"])
            _release_rows(db, current)
            assert db.get(ActiveCorpus, 1).release_id == prior["active_pointer_before"]
        print(json.dumps(prior, indent=2))
        return
    with factory() as db:
        source = db.get(CorpusRelease, BASELINE)
        assert source is not None and source.state == "active"
        _release_rows(db, source)
        pointer = db.get(ActiveCorpus, 1).release_id
        original_manifest = json.loads(json.dumps(source.manifest))
        original_configuration = json.loads(json.dumps(source.configuration))
        changes = json.loads(Path("configs/corpus/r3_minilm_cuda.json").read_text())
        config = config_create(
            db,
            "retrieval",
            "Frozen MiniLM R3 comparison",
            {**source.configuration, **changes, "retriever": "R3"},
        )
        owner = db.scalar(select(User).where(User.email == "admin@example.com"))
        release, job = queue_release(
            db,
            owner.id,
            source.manifest["processing_run_ids"],
            configuration_id=config.id,
            name="Four-book MiniLM R3 comparison (unactivated)",
        )
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "baseline_release_id": BASELINE,
            "release_id": release.id,
            "job_id": job.id,
            "configuration_id": config.id,
            "active_pointer_before": pointer,
            "status": "queued",
            "configuration": config.values,
            "processing_run_ids": source.manifest["processing_run_ids"],
        }
        db.commit()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    # The normal running worker may claim this job first. Token fencing in the
    # shared worker prevents duplicate publication; never call execute_release
    # directly on a concurrently claimed job.
    run_once(engine, settings)
    deadline = time.monotonic() + 180
    while True:
        with factory() as db:
            state = db.get(Job, record["job_id"])
            if state.state in ("succeeded", "failed", "cancelled"):
                current = db.get(CorpusRelease, record["release_id"])
                source = db.get(CorpusRelease, BASELINE)
                if state.state != "succeeded":
                    record.update(status=state.state, error=state.error)
                    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
                    raise RuntimeError("Comparison build did not complete; failure retained")
                _release_rows(db, current)
                assert current.state == "validated"
                assert db.get(ActiveCorpus, 1).release_id == pointer
                assert (
                    source.manifest == original_manifest
                    and source.configuration == original_configuration
                )
                assert current.manifest["chunk_ids"] == original_manifest["chunk_ids"]
                assert current.manifest["content_hash"] == original_manifest["content_hash"]
                assert current.manifest["embedding_hash"] == original_manifest["embedding_hash"]
                record.update(
                    status="validated_unactivated",
                    manifest=current.manifest,
                    active_pointer_after=pointer,
                    baseline_unchanged=True,
                    exact_chunks_and_vectors_reused=True,
                )
                output.write_text(json.dumps(record, indent=2), encoding="utf-8")
                print(
                    json.dumps(
                        {
                            k: record[k]
                            for k in (
                                "status",
                                "release_id",
                                "active_pointer_after",
                                "exact_chunks_and_vectors_reused",
                            )
                        },
                        indent=2,
                    )
                )
                return
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "Comparison build still pending; reconcile its saved job instead of queuing another"
            )
        time.sleep(0.5)


if __name__ == "__main__":
    main()
