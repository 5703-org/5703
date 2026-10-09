"""Compare the untouched project DB with an isolated migrated/restored clone."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT / "backend", ROOT):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from app.core.config import Settings  # noqa: E402


QUERIES = {
    "migration_head": "SELECT version_num FROM alembic_version",
    "active_release": "SELECT release_id FROM active_corpus WHERE id=1",
    "active_vectors": "SELECT count(*) FROM release_chunks WHERE release_id=(SELECT release_id FROM active_corpus WHERE id=1)",
    "vector_dimension_min": "SELECT min(dimension) FROM release_chunks WHERE release_id=(SELECT release_id FROM active_corpus WHERE id=1)",
    "vector_dimension_max": "SELECT max(dimension) FROM release_chunks WHERE release_id=(SELECT release_id FROM active_corpus WHERE id=1)",
    "all_release_memberships": "SELECT count(*) FROM release_chunks",
    "answers": "SELECT count(*) FROM answers",
    "citations": "SELECT count(*) FROM citations",
    "answer_requests": "SELECT count(*) FROM answer_requests",
    "source_hashes": "SELECT string_agg(raw_hash, ',' ORDER BY raw_hash) FROM document_versions",
}


def snapshot(url: str, *, visual: bool) -> dict:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            result = {key: connection.scalar(text(query)) for key, query in QUERIES.items()}
            if visual:
                result["visual_regions"] = connection.scalar(
                    text("SELECT count(*) FROM visual_regions")
                )
                result["visual_reviews"] = connection.scalar(
                    text("SELECT count(*) FROM visual_region_reviews")
                )
            return result
    finally:
        engine.dispose()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    isolated_url = os.getenv("WEEK09_ISOLATED_DATABASE_URL")
    if not isolated_url:
        parser.error("WEEK09_ISOLATED_DATABASE_URL is required")
    main_db = snapshot(Settings(_env_file=ROOT / ".env").database_url, visual=False)
    clone_db = snapshot(isolated_url, visual=True)
    preserved = all(main_db[key] == clone_db[key] for key in QUERIES if key != "migration_head")
    passed = (
        preserved
        and clone_db["migration_head"] == "f4a18bc67d20"
        and clone_db["active_vectors"] == 10594
        and clone_db["vector_dimension_min"] == clone_db["vector_dimension_max"] == 384
        and clone_db["visual_regions"] == 5543
        and clone_db["visual_reviews"] == 0
    )
    evidence = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed",
        "scope": "read-only main database versus disposable restored and migrated clone",
        "backup": {
            "path": str(args.backup.resolve()),
            "bytes": args.backup.stat().st_size,
            "sha256": sha256(args.backup),
            "included_in_delivery": False,
        },
        "main": main_db,
        "isolated_clone": clone_db,
        "preserved_except_migration_head": preserved,
        "limitations": "Counts and source identities do not prove every historical row byte is identical; the source backup and original database remain intact.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "evidence": str(args.out)}))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
