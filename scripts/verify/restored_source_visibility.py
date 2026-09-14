"""Verify unavailable historical evidence on an explicitly matched restored copy."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "backend"))


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore-proof", type=Path, required=True)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--apply-revoke", action="store_true")
    args = parser.parse_args()
    proof_path = args.restore_proof.resolve()
    proof_path.relative_to(ROOT / "evidence/recovery")
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    database = proof["target_database"]
    storage = Path(proof["target_storage"]).resolve()
    if (
        proof["status"] != "passed"
        or not re.fullmatch(r"cs30_restore_[a-z0-9_]+", database)
        or not storage.is_relative_to(ROOT / "artifacts")
        or not storage.name.startswith("restore-")
        or not storage.is_dir()
        or not args.apply_revoke
    ):
        raise SystemExit("An actual matched disposable restore and --apply-revoke are required.")
    stamp = datetime.now(timezone.utc)
    output = (
        ROOT / "evidence/operations/restored-source-visibility" / stamp.strftime("%Y%m%dT%H%M%SZ")
    )
    output.mkdir(parents=True, exist_ok=False)
    backup_manifest = proof_path.parent / "manifest.json"
    original_manifest_hash = hashlib.sha256(backup_manifest.read_bytes()).hexdigest()
    report = {
        "status": "running",
        "started_at": stamp.isoformat(),
        "database": database,
        "storage": str(storage),
        "restore_proof": str(proof_path.relative_to(ROOT)),
        "restore_proof_sha256": hashlib.sha256(proof_path.read_bytes()).hexdigest(),
        "original_backup_manifest_sha256": original_manifest_hash,
        "document_id": args.document_id,
        "mutation_scope": "One non-active-release authored document is revoked only in the named restored database. No original backup, main database, worker, model or physical source file is modified.",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }

    def save(name, value):
        (output / name).write_text(
            json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8"
        )

    server = make_url(
        os.environ.get(
            "TEST_DATABASE_SERVER",
            "postgresql+psycopg://learning:local-dev-database-only@127.0.0.1:55432",
        )
    )
    assert server.get_backend_name() == "postgresql"
    url = server.set(database=database).render_as_string(hide_password=False)
    engine = create_engine(url)
    app = client = None
    try:
        from fastapi.testclient import TestClient
        from app.core.config import Settings
        from app.main import create_app

        def snapshot():
            with engine.connect() as db:
                assert db.scalar(text("SELECT current_database()")) == database
                documents = [
                    dict(row._mapping)
                    for row in db.execute(text("SELECT * FROM documents ORDER BY id"))
                ]
                active = [
                    dict(row._mapping)
                    for row in db.execute(text("SELECT * FROM active_corpus ORDER BY id"))
                ]
                assert len(active) == 1
                release_id = active[0]["release_id"]
                release = dict(
                    db.execute(
                        text("SELECT * FROM corpus_releases WHERE id=:id"), {"id": release_id}
                    )
                    .one()
                    ._mapping
                )
                active_sources = [
                    dict(row._mapping)
                    for row in db.execute(
                        text(
                            "SELECT c.document_id,count(*) AS chunks FROM release_chunks rc JOIN chunks c ON c.id=rc.chunk_id WHERE rc.release_id=:id GROUP BY c.document_id ORDER BY c.document_id"
                        ),
                        {"id": release_id},
                    )
                ]
                preserved = {}
                for table in (
                    "messages",
                    "answers",
                    "answer_requests",
                    "evidence_snapshots",
                    "snapshots",
                    "citations",
                    "jobs",
                    "attempts",
                ):
                    values = [
                        dict(row._mapping)
                        for row in db.execute(text(f"SELECT * FROM {table} ORDER BY id"))
                    ]
                    preserved[table] = {"rows": len(values), "sha256": digest(values)}
                return {
                    "documents": documents,
                    "active_pointer": active,
                    "active_release": release,
                    "active_sources": active_sources,
                    "historical_records": preserved,
                }

        before = snapshot()
        document = next(row for row in before["documents"] if row["id"] == args.document_id)
        assert document["active"] is True and document["revoked"] is False
        assert document["title"] == "Authored biology integration notes"
        assert args.document_id not in {row["document_id"] for row in before["active_sources"]}
        assert len(before["active_sources"]) == 4
        with engine.connect() as db:
            selected = dict(
                db.execute(
                    text(
                        "SELECT e.answer_id,e.evidence_id,e.document_id,ar.owner_id,u.email FROM evidence_snapshots e JOIN answers a ON a.id=e.answer_id JOIN answer_requests ar ON ar.id=a.request_id JOIN users u ON u.id=ar.owner_id WHERE e.document_id=:id AND u.status='active' ORDER BY e.id LIMIT 1"
                    ),
                    {"id": args.document_id},
                )
                .one()
                ._mapping
            )
            originals = [
                dict(row._mapping)
                for row in db.execute(
                    text(
                        "SELECT storage_path,raw_hash FROM document_versions WHERE document_id=:id"
                    ),
                    {"id": args.document_id},
                )
            ]
        source_hashes = {}
        for original in originals:
            path = (storage / original["storage_path"]).resolve()
            assert path.is_relative_to(storage)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            assert actual == original["raw_hash"]
            source_hashes[str(path.relative_to(storage))] = actual
        save("before.json", before)
        settings = Settings(
            env="test",
            database_url=url,
            storage_root=str(storage),
            jwt_secret="restored-visibility-test-secret-at-least-thirty-two-characters",
            model_mode="mock",
            llm_provider="mock",
            mock_delay_seconds=0,
        )
        app = create_app(settings)
        client = TestClient(app)

        def login(email):
            response = client.post(
                "/api/v1/auth/login", json={"email": email, "password": "Passw0rd!"}
            )
            assert response.status_code == 200, ("fixture login", response.status_code)
            return {"Authorization": "Bearer " + response.json()["data"]["access_token"]}

        owner_headers = login(selected["email"])
        admin_headers = login("admin@example.com")
        evidence_path = (
            f"/api/v1/answers/{selected['answer_id']}/evidence/{selected['evidence_id']}"
        )
        answer_path = f"/api/v1/answers/{selected['answer_id']}"
        source_before = client.get(evidence_path, headers=owner_headers)
        answer_before = client.get(answer_path, headers=owner_headers)
        ready_before = client.get("/ready")
        capability_before = client.get("/api/v1/capabilities", headers=owner_headers)
        assert (
            source_before.status_code
            == answer_before.status_code
            == ready_before.status_code
            == capability_before.status_code
            == 200
        )
        assert capability_before.json()["data"]["chat_ready"] is True
        assert any(
            e["evidence_id"] == selected["evidence_id"]
            for e in answer_before.json()["data"]["evidence"]
        )
        revoked = client.post(f"/api/v1/documents/{args.document_id}/revoke", headers=admin_headers)
        assert revoked.status_code == 200
        source_after = client.get(evidence_path, headers=owner_headers)
        answer_after = client.get(answer_path, headers=owner_headers)
        ready_after = client.get("/ready")
        capability_after = client.get("/api/v1/capabilities", headers=owner_headers)
        assert source_after.status_code == 410
        assert source_after.json()["error"]["code"] == "EVIDENCE_UNAVAILABLE"
        assert (
            answer_after.status_code
            == ready_after.status_code
            == capability_after.status_code
            == 200
        )
        assert capability_after.json()["data"]["chat_ready"] is True
        before_answer = answer_before.json()["data"]
        after_answer = answer_after.json()["data"]
        assert before_answer["response"] == after_answer["response"]
        assert before_answer["conversation_snapshot"] == after_answer["conversation_snapshot"]
        assert not after_answer["evidence"]
        after = snapshot()
        for key in ("active_pointer", "active_release", "active_sources", "historical_records"):
            assert before[key] == after[key], key
        other_before = [row for row in before["documents"] if row["id"] != args.document_id]
        other_after = [row for row in after["documents"] if row["id"] != args.document_id]
        assert other_before == other_after
        changed_document = next(row for row in after["documents"] if row["id"] == args.document_id)
        assert changed_document["active"] is False and changed_document["revoked"] is True
        assert changed_document["version"] == document["version"] + 1
        for relative, expected in source_hashes.items():
            assert hashlib.sha256((storage / relative).read_bytes()).hexdigest() == expected
        assert hashlib.sha256(backup_manifest.read_bytes()).hexdigest() == original_manifest_hash
        save("after.json", after)
        save(
            "api-observations.json",
            {
                "selected": selected,
                "source_before": {
                    "status": source_before.status_code,
                    "payload_sha256": digest(source_before.json()),
                },
                "source_after": {"status": source_after.status_code, "body": source_after.json()},
                "answer_before": before_answer,
                "answer_after": after_answer,
                "ready_before": ready_before.json(),
                "ready_after": ready_after.json(),
                "capabilities_before": capability_before.json(),
                "capabilities_after": capability_after.json(),
            },
        )
        report.update(
            status="passed",
            evidence_id=selected["evidence_id"],
            answer_id=selected["answer_id"],
            assertions={
                "matched_existing_portable_restore": True,
                "only_non_active_authored_document_revoked": True,
                "evidence_200_then_410_unavailable": True,
                "historical_answer_content_and_stored_evidence_unchanged": True,
                "active_pointer_release_and_four_sources_unchanged": True,
                "database_and_chat_readiness_remain_true": True,
                "physical_original_hashes_and_backup_manifest_unchanged": True,
            },
            source_hashes=source_hashes,
            limits="No cross-backup erasure is performed or claimed. This disposable restored copy now retains an explicitly revoked authored source; the prior restore proof remains a historical pre-drill snapshot. Current official corpus and main application remain untouched.",
        )
    except BaseException as exc:
        report.update(status="failed", failure_type=type(exc).__name__, failure_detail=str(exc))
        raise
    finally:
        if client is not None:
            client.close()
        if app is not None:
            app.state.engine.dispose()
        engine.dispose()
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        save("verification.json", report)
        print(json.dumps({"status": report["status"], "evidence": str(output)}), flush=True)


if __name__ == "__main__":
    main()
