"""Validated PostgreSQL release snapshots with transactional database invalidation.

Only immutable primitive projections are cached. Every relevant DML statement
changes a UUID token in the same transaction, so rollback cannot cause token reuse.
SQLite and frozen legacy retrieval keep the complete-validation path.
"""

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
import time

from sqlalchemy import text

from retrieval.lexical import LexicalIndex

VERSION = "validated_release_cache_v1"
TABLES = {
    "documents",
    "document_versions",
    "processing_runs",
    "source_units",
    "chunks",
    "corpus_releases",
    "release_chunks",
    "active_corpus",
    "configurations",
}
_LOCK = RLock()
_CACHE = OrderedDict()


def epoch(db):
    """Fail closed if invalidation infrastructure is missing or disabled."""
    db.flush()
    if db.scalar(text("SHOW session_replication_role")) != "origin":
        raise ValueError("Retrieval requires active origin invalidation triggers")
    triggers = (
        db.execute(
            text("""
        SELECT c.relname FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE t.tgname='cs30_retrieval_epoch' AND t.tgenabled IN ('O','A')
          AND n.nspname=current_schema()
    """)
        )
        .scalars()
        .all()
    )
    if set(triggers) != TABLES:
        raise ValueError("Retrieval invalidation triggers are missing or disabled")
    value = db.scalar(text("SELECT token FROM retrieval_epochs WHERE id=1"))
    if not value:
        raise ValueError("Retrieval invalidation identity is unavailable")
    return value


@dataclass(frozen=True)
class ReleaseIndex:
    token: str
    rows: dict
    vector_hashes: dict
    lexical: LexicalIndex
    provenance: dict


def load(db, release, project_row, validator, vector_hash, digest):
    started = time.perf_counter()
    current = epoch(db)
    identity = digest({"configuration": release.configuration, "manifest": release.manifest})
    key = (db.get_bind(), release.id, current, identity)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached:
            _CACHE.move_to_end(key)
            return cached, {
                "version": VERSION,
                "hit": True,
                "epoch": current,
                "validation_ms": (time.perf_counter() - started) * 1000,
            }
        # A session can retain ORM identities while another connection changes
        # a source. epoch() already flushed local writes; refresh every loaded
        # source before constructing the new validated snapshot.
        db.expire_all()
        provenance = {}
        raw_rows = validator(db, release, provenance=provenance)
        visible = [r for r in raw_rows if r[2].active and not r[2].revoked]
        rows = {r[1].id: project_row(r, provenance) for r in visible}
        result = ReleaseIndex(
            current,
            rows,
            {r[1].id: vector_hash([r[0]]) for r in visible},
            LexicalIndex(list(rows.values())),
            provenance,
        )
        if epoch(db) != current:
            raise ValueError("Sources changed during release validation; retry with current data")
        _CACHE[key] = result
        _CACHE.move_to_end(key)
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
        return result, {
            "version": VERSION,
            "hit": False,
            "epoch": current,
            "validation_ms": (time.perf_counter() - started) * 1000,
        }


def validate_hits(db, release_id, index, hits, project_row, vector_hash):
    """Recheck actual hit text, source identity, visibility and vector bytes."""
    for value in hits:
        vector, chunk, doc = value
        expected = index.rows.get(chunk.id)
        if (
            not expected
            or not doc.active
            or doc.revoked
            or vector.release_id != release_id
            or project_row(value, index.provenance) != expected
            or vector_hash([vector]) != index.vector_hashes[chunk.id]
        ):
            raise ValueError("A retrieved source differs from its validated release")
    if epoch(db) != index.token:
        raise ValueError("Sources changed during retrieval; retry with current data")


def clear():
    with _LOCK:
        _CACHE.clear()


def publication_fence(db):
    """Hold through answer commit; source DML's epoch update must serialize after it."""
    token = db.scalar(text("SELECT token FROM retrieval_epochs WHERE id=1 FOR SHARE"))
    if not token or epoch(db) != token:
        raise ValueError("Current source publication fence is unavailable")
    return token
