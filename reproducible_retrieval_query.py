"""Run one source-traceable retrieval query against an immutable corpus release.

This script belongs in the shared repository at
``scripts/verify/reproducible_retrieval_query.py``.  It deliberately calls the
same ``knowledge.service.retrieve`` interface used by the application, rather
than reimplementing retrieval in a separate experiment-only path.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _validate_hits(hits: list[dict]) -> None:
    required = {"chunk_id", "text", "score", "text_hash"}
    for rank, hit in enumerate(hits, start=1):
        missing = required - set(hit)
        if missing:
            raise ValueError(f"Hit {rank} is missing required fields: {sorted(missing)}")
        actual_hash = hashlib.sha256(hit["text"].encode("utf-8")).hexdigest()
        if actual_hash != hit["text_hash"]:
            raise ValueError(f"Hit {rank} has a source-text hash mismatch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-id", required=True, type=int)
    parser.add_argument("--question-id", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--variant", choices=("R0", "R1", "R2", "R3"), default="R0")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.top_k not in (3, 5, 10):
        raise ValueError("Week 7 experiments use Top-K values 3, 5, or 10")

    # The shared project keeps these packages under backend/.  Resolving from
    # this file makes the command independent of the current shell directory.
    repository_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repository_root / "backend"))

    from sqlalchemy import text  # pylint: disable=import-outside-toplevel
    from sqlalchemy.orm import sessionmaker  # pylint: disable=import-outside-toplevel
    from app.core.config import Settings  # pylint: disable=import-outside-toplevel
    from app.db.session import init_engine  # pylint: disable=import-outside-toplevel
    from app.modules.knowledge import service  # pylint: disable=import-outside-toplevel
    from app.modules.knowledge.models import CorpusRelease  # pylint: disable=import-outside-toplevel

    engine = init_engine(Settings().database_url)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("A PostgreSQL/pgvector database is required for this query")

    factory = sessionmaker(bind=engine, expire_on_commit=False)
    started = time.perf_counter()
    with factory() as database:
        database.execute(text("SET TRANSACTION READ ONLY"))
        release = database.get(CorpusRelease, args.release_id)
        if release is None:
            raise ValueError(f"Corpus release {args.release_id} was not found")

        configuration = dict(release.configuration)
        if configuration.get("embedding_model") != "intfloat/e5-small-v2":
            raise ValueError("Expected the pinned E5-small-v2 corpus-v5 embedding configuration")
        if configuration.get("dimension") != 384:
            raise ValueError("Expected 384-dimensional corpus-v5 embeddings")

        hits = service.retrieve(
            database,
            args.question,
            release.id,
            variant=args.variant,
            top_k=args.top_k,
        )

    _validate_hits(hits)
    for rank, hit in enumerate(hits, start=1):
        hit["rank"] = rank

    result = {
        "status": "succeeded",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "question_id": args.question_id,
        "question": args.question,
        "release_id": args.release_id,
        "variant": args.variant,
        "top_k": args.top_k,
        "configuration": configuration,
        "manifest_hashes": {
            key: release.manifest.get(key)
            for key in ("content_hash", "embedding_hash", "configuration_hash")
        },
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "hits": hits,
        "source_hashes_verified": True,
    }
    _write_json(Path(args.output), result)
    print(json.dumps({"status": "succeeded", "hits": len(hits), "output": args.output}))


if __name__ == "__main__":
    main()
