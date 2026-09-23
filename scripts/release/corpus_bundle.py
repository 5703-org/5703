"""Export/import official corpus rows and assets without deployment or learner data."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil

from sqlalchemy import DateTime, create_engine, func, insert, select, text
from sqlalchemy.orm import Session

from app.cli import seed
from app.core.config import Settings
from app.modules.identity.models import User
from app.modules.knowledge.models import (
    ActiveCorpus,
    Chunk,
    Configuration,
    CorpusRelease,
    Document,
    DocumentVersion,
    ProcessingRun,
    ReleaseChunk,
    SourceUnit,
)
from scripts.release.common import file_hash
from app.modules.knowledge.service import _release_rows

BOOKS = {"Biology 2e", "Chemistry 2e", "Anatomy and Physiology 2e", "Concepts of Biology"}
TABLES = [
    Document,
    DocumentVersion,
    Configuration,
    ProcessingRun,
    SourceUnit,
    Chunk,
    CorpusRelease,
    ReleaseChunk,
    ActiveCorpus,
]


def safe_path(root, value):
    path = (root / str(value).replace("\\", "/")).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("A corpus resource path escapes its designated root")
    return path


def json_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(type(value).__name__)


def export_bundle(destination, settings):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Choose a new corpus-bundle destination")
    destination.mkdir(parents=True)
    engine = create_engine(settings.database_url)
    storage = Path(settings.storage_root).resolve()
    files = {}
    counts = {}

    def copy_asset(relative, expected=None):
        source = safe_path(storage, relative)
        relative = source.relative_to(storage).as_posix()
        digest = file_hash(source)
        if expected and digest != expected:
            raise ValueError("Source hash differs: " + relative)
        if relative not in files:
            target = safe_path(destination / "storage", relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            files[relative] = {
                "path": "storage/" + relative,
                "sha256": digest,
                "bytes": source.stat().st_size,
            }
        return source

    try:
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as db:
            documents = list(
                db.execute(select(Document.__table__).where(Document.title.in_(BOOKS))).mappings()
            )
            if {d["title"] for d in documents} != BOOKS or len(documents) != 4:
                raise ValueError("Expected exactly the four required official OpenStax documents")
            if any(
                not d["source_url"].startswith("https://assets.openstax.org/") for d in documents
            ):
                raise ValueError("Official source URL verification failed")
            document_ids = [d["id"] for d in documents]
            versions = list(
                db.execute(
                    select(DocumentVersion.__table__).where(
                        DocumentVersion.document_id.in_(document_ids)
                    )
                ).mappings()
            )
            version_ids = [v["id"] for v in versions]
            runs = list(
                db.execute(
                    select(ProcessingRun.__table__).where(
                        ProcessingRun.document_version_id.in_(version_ids)
                    )
                ).mappings()
            )
            run_ids = [v["id"] for v in runs]
            releases = [
                dict(r)
                for r in db.execute(select(CorpusRelease.__table__)).mappings()
                if r["configuration"].get("embedding_provider") == "e5"
            ]
            release_ids = [r["id"] for r in releases]
            if any(
                not set(r["manifest"].get("processing_run_ids", [])) <= set(run_ids)
                for r in releases
            ):
                raise ValueError(
                    "An E5 release references sources outside the four-book export scope"
                )
            exported_document_ids = set(
                db.execute(
                    select(Chunk.document_id)
                    .join(ReleaseChunk, ReleaseChunk.chunk_id == Chunk.id)
                    .where(ReleaseChunk.release_id.in_(release_ids))
                    .distinct()
                ).scalars()
            )
            if not exported_document_ids <= set(document_ids):
                raise ValueError("An E5 release includes chunks outside the four required books")
            active = db.scalar(select(ActiveCorpus.release_id).where(ActiveCorpus.id == 1))
            if active not in release_ids:
                raise ValueError("Active corpus is not a real E5 release")
            for version in versions:
                copy_asset(version["storage_path"], version["raw_hash"])
            for run in runs:
                for item in run["configuration"].get("source_supplements", []):
                    path = copy_asset(
                        item["storage_path"], item.get("html_sha256") or item["artifact_sha256"]
                    )
                    if item["kind"] == "pdf_image_transcription":
                        artifact = json.loads(path.read_text("utf-8"))
                        copy_asset(artifact["render_storage_path"], artifact["render_sha256"])
                        copy_asset(artifact["ocr_storage_path"], artifact["ocr_sha256"])
            queries = {
                Document.__tablename__: documents,
                DocumentVersion.__tablename__: versions,
                Configuration.__tablename__: [
                    r
                    for r in db.execute(select(Configuration.__table__)).mappings()
                    if r["kind"] in ("retrieval", "corpus", "embedding", "chunking")
                    and r["values"].get("embedding_provider") == "e5"
                ],
                ProcessingRun.__tablename__: runs,
                SourceUnit.__tablename__: db.execute(
                    select(SourceUnit.__table__).where(SourceUnit.processing_id.in_(run_ids))
                ).mappings(),
                Chunk.__tablename__: db.execute(
                    select(Chunk.__table__).where(Chunk.processing_id.in_(run_ids))
                ).mappings(),
                CorpusRelease.__tablename__: releases,
                ReleaseChunk.__tablename__: db.execute(
                    select(ReleaseChunk.__table__).where(ReleaseChunk.release_id.in_(release_ids))
                ).mappings(),
                ActiveCorpus.__tablename__: [{"id": 1, "release_id": active}],
            }
            data_file = destination / "corpus.jsonl.gz"
            with gzip.open(data_file, "wt", encoding="utf-8", compresslevel=6) as stream:
                for model in TABLES:
                    table = model.__tablename__
                    counts[table] = 0
                    for source in queries[table]:
                        row = dict(source)
                        if table == "documents":
                            # Operator ownership is rebound on a new installation.
                            row.pop("owner_id")
                        if table == "document_versions":
                            row["storage_path"] = str(row["storage_path"]).replace("\\", "/")
                        stream.write(
                            json.dumps(
                                {"table": table, "row": row}, ensure_ascii=False, default=json_value
                            )
                            + "\n"
                        )
                        counts[table] += 1
            active_count = db.scalar(
                select(func.count())
                .select_from(ReleaseChunk)
                .where(ReleaseChunk.release_id == active)
            )
        manifest = {
            "schema": "official-corpus-bundle-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Four official books, all their preserved processing units/chunks, real E5 releases and source recovery artifacts. No users, answers, sessions, model credentials or private evaluation labels.",
            "active_release_id": active,
            "active_vector_count": active_count,
            "dimension": 384,
            "books": [
                {k: d[k] for k in ("id", "title", "edition", "source_url", "license")}
                for d in documents
            ],
            "counts": counts,
            "data": {
                "path": data_file.name,
                "sha256": file_hash(data_file),
                "bytes": data_file.stat().st_size,
            },
            "files": list(files.values()),
            "ownership": "Document operator IDs are rebound to the new installation administrator; scientific row IDs, text, source hashes and vectors are retained.",
        }
        (destination / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        return manifest
    finally:
        engine.dispose()


def import_bundle(source, settings):
    source = Path(source).resolve()
    manifest = json.loads((source / "MANIFEST.json").read_text("utf-8"))
    if manifest.get("schema") != "official-corpus-bundle-v1":
        raise ValueError("Unsupported corpus bundle")
    for entry in [manifest["data"], *manifest["files"]]:
        if file_hash(safe_path(source, entry["path"])) != entry["sha256"]:
            raise ValueError("Bundled resource hash mismatch")
    storage = Path(settings.storage_root).resolve()
    engine = create_engine(settings.database_url)
    try:
        with Session(engine) as db:
            if db.scalar(select(func.count()).select_from(Document)):
                raise ValueError(
                    "Import requires an empty corpus; existing sources are never overwritten"
                )
            seed(db)
            admin = db.scalar(select(User).where(User.email == "admin@example.com"))
            if not admin:
                raise ValueError("Create the local administrator before corpus import")
            owner = admin.id
        models = {model.__tablename__: model for model in TABLES}
        actual = {name: 0 for name in models}
        with Session(engine) as db, db.begin():
            if engine.dialect.name == "postgresql":
                db.execute(text("SELECT pg_advisory_xact_lock(5703002)"))
            if db.scalar(select(func.count()).select_from(Document)):
                raise ValueError(
                    "A concurrent operator installed a corpus; no existing rows were overwritten"
                )
            # Share the storage lifecycle lock with ingestion/cleanup through
            # file verification, copying and committed source registration.
            for entry in manifest["files"]:
                target = safe_path(storage, entry["path"].removeprefix("storage/"))
                if target.exists() and file_hash(target) != entry["sha256"]:
                    raise ValueError("An existing source differs; choose a new storage directory")
            for entry in manifest["files"]:
                target = safe_path(storage, entry["path"].removeprefix("storage/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copyfile(safe_path(source, entry["path"]), target)
            pending = []
            pending_table = None

            def flush():
                if pending:
                    db.execute(insert(pending_table), pending)
                    pending.clear()

            with gzip.open(
                safe_path(source, manifest["data"]["path"]), "rt", encoding="utf-8"
            ) as stream:
                for line in stream:
                    value = json.loads(line)
                    table = models[value["table"]].__table__
                    row = value["row"]
                    if pending_table is not table:
                        flush()
                        pending_table = table
                    if table.name == "documents":
                        row["owner_id"] = owner
                    for column in table.columns:
                        if isinstance(column.type, DateTime) and isinstance(
                            row.get(column.name), str
                        ):
                            row[column.name] = datetime.fromisoformat(row[column.name])
                    if (
                        table.name == "chunks"
                        and hashlib.sha256(row["text"].encode()).hexdigest() != row["text_hash"]
                    ):
                        raise ValueError("Bundled chunk text hash differs")
                    if table.name == "release_chunks" and (
                        len(row["embedding"]) != row["dimension"]
                        or any(not math.isfinite(v) for v in row["embedding"])
                    ):
                        raise ValueError("Bundled embedding has invalid dimension or values")
                    if table.name == "active_corpus":
                        db.execute(
                            table.update()
                            .where(table.c.id == 1)
                            .values(release_id=row["release_id"])
                        )
                    else:
                        pending.append(row)
                        if len(pending) >= 250:
                            flush()
                    actual[table.name] += 1
                flush()
            if actual != manifest["counts"]:
                raise ValueError("Corpus row counts differ from the package manifest")
            count = db.scalar(
                select(func.count())
                .select_from(ReleaseChunk)
                .where(ReleaseChunk.release_id == manifest["active_release_id"])
            )
            if count != manifest["active_vector_count"]:
                raise ValueError("Active real vector count mismatch")
            validated = _release_rows(
                db, db.get(CorpusRelease, manifest["active_release_id"]), require_active=True
            )
            if len(validated) != count:
                raise ValueError("Publication integrity verification failed")
        return {
            "status": "passed",
            "active_release_id": manifest["active_release_id"],
            "active_vectors": count,
            "counts": actual,
            "verified_source_files": len(manifest["files"]),
            "publication_integrity": "Full active membership, content/vector/configuration hashes, source spans, processing quality and model identity verified within the import transaction",
        }
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "import"])
    parser.add_argument("--path", type=Path, required=True)
    args = parser.parse_args()
    result = (
        export_bundle(args.path, Settings())
        if args.action == "export"
        else import_bundle(args.path, Settings())
    )
    print(json.dumps({k: v for k, v in result.items() if k not in ("books", "files")}, indent=2))


if __name__ == "__main__":
    main()
