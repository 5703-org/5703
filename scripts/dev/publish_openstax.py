"""Activate the verified real corpus while proving historical answers are unchanged."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text
from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/openstax"


def historical_fingerprint(connection):
    result = {}
    for table in ("answers", "evidence_snapshots", "document_versions"):
        rows = [
            dict(row)
            for row in connection.execute(text(f"SELECT * FROM {table} ORDER BY id")).mappings()
        ]
        result[table] = {
            "count": len(rows),
            "sha256": hashlib.sha256(
                json.dumps(rows, sort_keys=True, default=str).encode()
            ).hexdigest(),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    evidence_dir = args.evidence_dir
    target = evidence_dir / "publication.json"
    if target.exists():
        raise RuntimeError(
            "Publication record already exists; use a separate record for a later activation"
        )
    checks = {}
    for filename, status in (
        ("formal-source-validation-summary.json", "passed"),
        ("retrieval-verification.json", "passed_source_and_vector_checks"),
    ):
        path = evidence_dir / filename
        data = json.loads(path.read_text("utf-8"))
        if data.get("status") != status:
            raise RuntimeError("Required current check has not passed: " + filename)
        checks[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    build = json.loads((evidence_dir / "release-build.json").read_text("utf-8"))
    release_id = build["release_id"]
    formal_path = evidence_dir / "formal-source-validation.json"
    formal = json.loads(formal_path.read_text("utf-8"))
    summary = json.loads(
        (evidence_dir / "formal-source-validation-summary.json").read_text("utf-8")
    )
    if (
        formal.get("status") != "passed"
        or hashlib.sha256(formal_path.read_bytes()).hexdigest() != summary["report_sha256"]
        or {book["processing_id"] for book in formal["books"]} != set(build["processing_run_ids"])
    ):
        raise RuntimeError("Formal source proof does not match this exact release source set")
    retrieval = json.loads((evidence_dir / "retrieval-verification.json").read_text("utf-8"))
    if retrieval["release_id"] != release_id or len(retrieval["questions"]) != 15:
        raise RuntimeError("Retrieval proof does not cover this release and all scheduled queries")
    engine = create_engine(Settings().database_url)
    with engine.connect() as db:
        previous = db.scalar(text("SELECT release_id FROM active_corpus WHERE id=1"))
        before = historical_fingerprint(db)
    with httpx.Client(base_url="http://127.0.0.1:8000/api/v1", timeout=120) as client:
        login = client.post(
            "/auth/login", json={"email": "admin@example.com", "password": "Passw0rd!"}
        )
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["data"]["access_token"]
        response = client.post(f"/corpus/releases/{release_id}/activate")
        response.raise_for_status()
        release = response.json()["data"]
    with engine.connect() as db:
        active = db.scalar(text("SELECT release_id FROM active_corpus WHERE id=1"))
        active_count = db.scalar(text("SELECT count(*) FROM corpus_releases WHERE state='active'"))
        after = historical_fingerprint(db)
        dimensions = [
            dict(row)
            for row in db.execute(
                text(
                    "SELECT c.document_id, count(*) AS vectors, min(vector_dims(r.embedding)) AS minimum_dimension, max(vector_dims(r.embedding)) AS maximum_dimension FROM release_chunks r JOIN chunks c ON c.id=r.chunk_id WHERE r.release_id=:id GROUP BY c.document_id"
                ),
                {"id": release_id},
            ).mappings()
        ]
    assert active == release_id and active_count == 1
    assert before == after, "Historical answer/evidence/original records changed during activation"
    result = {
        "status": "passed",
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "release_id": release_id,
        "previous_active_release_id": previous,
        "release": release,
        "active_release_count": active_count,
        "historical_before": before,
        "historical_after": after,
        "history_preserved": True,
        "per_document_vectors": dimensions,
        "checks_sha256": checks,
        "answer_model_mode": "mock",
        "publication_scope": "Local atomic corpus activation; real OpenStax, E5 and pgvector; no live answering or human semantic certification.",
    }
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", "utf-8")
    print(
        json.dumps(
            {
                "status": "passed",
                "release_id": active,
                "vectors": sum(x["vectors"] for x in dimensions),
                "history_preserved": True,
            }
        )
    )


if __name__ == "__main__":
    main()
