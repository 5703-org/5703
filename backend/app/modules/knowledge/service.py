"""Source administration, immutable processing and transactional release activation."""

from pathlib import Path
import hashlib
import json
import math
import struct
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.core.exceptions import AppError
from app.db.base import new_uuid, utcnow
from app.modules.knowledge.models import *
from app.modules.answering.models import Job
from pipelines.parse import CURRENT_PARSER_REVISION, parse
from pipelines.chunk import chunks
from pipelines.reports import quality_rows, compare_processing
from pipelines.supplements import apply_publisher_supplements
from retrieval.embedding import make_embedding, validate_vector
from retrieval.ranking import bm25, rrf, CrossEncoderReranker

DEFAULT_CONFIG = {
    "strategy": "structure",
    "target": 320,
    "cap": 448,
    "overlap": 48,
    "embedding_provider": "mock",
    "embedding_revision": "mock-hash-v1",
    "dimension": 384,
    "retriever": "R0",
    "top_k": 5,
    "parser_revision": CURRENT_PARSER_REVISION,
    "cleaner_revision": "nfc_conservative_v2",
    "chunker_revision": "token_spans_v2",
    "embedding_preprocessing_revision": "prefix_v1",
    "tokenizer_revision": "mock-lexical-v1",
}


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def _secret_free(value):
    if isinstance(value, dict):
        for name, item in value.items():
            lowered = name.casefold()
            if any(part in lowered for part in ("secret", "password", "authorization")) or (
                "key" in lowered and not lowered.endswith("_key_env")
            ):
                raise AppError(
                    "VALIDATION_FAILED",
                    detail="Credentials must be supplied through environment references, never stored configuration values.",
                )
            _secret_free(item)
    elif isinstance(value, list):
        for item in value:
            _secret_free(item)


def corpus_config(values=None):
    values = dict(values or {})
    _secret_free(values)
    cfg = {**DEFAULT_CONFIG, **values}
    if (
        any(
            type(cfg[name]) is not int
            for name in ("target", "cap", "overlap", "dimension", "top_k")
        )
        or not 0 <= cfg["overlap"] < cfg["target"] <= cfg["cap"] <= 448
    ):
        raise AppError(
            "VALIDATION_FAILED",
            detail="Chunk settings require integer 0 <= overlap < target <= cap <= 448.",
        )
    if (
        not 1 <= cfg["dimension"] <= 4096
        or not 1 <= cfg["top_k"] <= 50
        or cfg["strategy"] not in ("structure", "fixed")
        or cfg["retriever"] not in ("R0", "R1", "R2", "R3")
    ):
        raise AppError(
            "VALIDATION_FAILED",
            detail="Invalid corpus dimension, retrieval depth, strategy or variant.",
        )
    if cfg["embedding_provider"] not in ("mock", "e5"):
        raise AppError("VALIDATION_FAILED", detail="Unsupported embedding provider.")
    revision = cfg.get("embedding_revision")
    if not isinstance(revision, str) or not revision.strip() or revision in ("main", "latest"):
        raise AppError("VALIDATION_FAILED", detail="An immutable embedding revision is required.")
    if cfg["embedding_provider"] == "e5":
        if revision.startswith("mock"):
            raise AppError("VALIDATION_FAILED", detail="E5 needs its own pinned model revision.")
        cfg["tokenizer_revision"] = values.get("tokenizer_revision") or revision
    digest(cfg)
    return cfg


def embedding_signature(cfg):
    values = {
        name: cfg.get(name)
        for name in (
            "embedding_provider",
            "embedding_model",
            "embedding_revision",
            "dimension",
            "embedding_preprocessing_revision",
            "tokenizer_revision",
        )
    }
    if cfg.get("embedding_device") is not None:
        values["embedding_device"] = cfg["embedding_device"]
    return digest(values)


def config_create(db, kind, name, values):
    _secret_free(values)
    if kind in ("retrieval", "corpus", "embedding", "chunking"):
        values = corpus_config(values)
    h = digest({"kind": kind, "values": values})
    old = db.scalar(select(Configuration).where(Configuration.content_hash == h))
    if old:
        return old
    record = Configuration(
        kind=kind, name=name, values=json.loads(json.dumps(values)), content_hash=h
    )
    db.add(record)
    db.flush()
    return record


def ingest(
    db,
    settings,
    owner_id,
    filename,
    data,
    title,
    edition="",
    source_url="",
    license="Not specified",
):
    if (
        not filename
        or len(filename) > 250
        or any(c in filename for c in ("/", "\\", ":", "\x00"))
        or any(ord(c) < 32 for c in filename)
        or filename in (".", "..")
    ):
        raise AppError("VALIDATION_FAILED", detail="Use a plain filename without a path.")
    if not title.strip() or len(title.strip()) > 500:
        raise AppError("VALIDATION_FAILED", detail="A nonblank source title is required.")
    if len(data) > settings.max_upload_bytes:
        raise AppError("UPLOAD_TOO_LARGE")
    suffix = Path(filename).suffix.casefold()
    if suffix == ".pdf" and data.startswith(b"%PDF-"):
        mime = "application/pdf"
    elif suffix == ".txt" and not data.startswith((b"%PDF-", b"MZ", b"PK\x03\x04")):
        try:
            decoded = data.decode("utf-8-sig")
            if "\x00" in decoded:
                raise ValueError("Binary data")
        except (UnicodeDecodeError, ValueError):
            raise AppError("UNSUPPORTED_MEDIA")
        mime = "text/plain"
    else:
        raise AppError("UNSUPPORTED_MEDIA")
    h = hashlib.sha256(data).hexdigest()
    old = db.scalar(select(DocumentVersion).where(DocumentVersion.raw_hash == h))
    if old:
        return db.get(Document, old.document_id), old, True
    if db.bind.dialect.name == "postgresql":
        # Orphan cleanup uses this transaction lock too: it must not remove an
        # old hash-named file between this existence check and version insertion.
        db.execute(text("SELECT pg_advisory_xact_lock(5703002)"))
        old = db.scalar(select(DocumentVersion).where(DocumentVersion.raw_hash == h))
        if old:
            return db.get(Document, old.document_id), old, True
    storage = Path(settings.storage_root).resolve() / "originals"
    storage.mkdir(parents=True, exist_ok=True)
    target = storage / (h + suffix)
    # User filenames never select an output path.
    if not target.exists():
        with target.open("xb") as stream:
            stream.write(data)
    elif hashlib.sha256(target.read_bytes()).hexdigest() != h:
        raise AppError(
            "SOURCE_UNAVAILABLE", detail="An existing immutable original has a mismatched hash."
        )
    document = Document(
        title=title.strip(),
        edition=edition,
        source_url=source_url,
        license=license,
        owner_id=owner_id,
    )
    db.add(document)
    db.flush()
    version = DocumentVersion(
        document_id=document.id,
        raw_hash=h,
        media_type=mime,
        size_bytes=len(data),
        storage_path=str(Path("originals") / (h + suffix)),
        original_filename=filename,
    )
    db.add(version)
    db.flush()
    return document, version, False


def queue_process(db, document_id, actor_id, configuration=None, exclusions=None):
    doc = db.scalar(select(Document).where(Document.id == document_id).with_for_update())
    if not doc or doc.revoked or not doc.active:
        raise AppError("NOT_FOUND")
    version = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.created_at.desc())
    )
    configuration = {**corpus_config(configuration), "exclusions": exclusions or {}}
    h = digest(configuration)
    existing = db.scalar(
        select(ProcessingRun).where(
            ProcessingRun.document_version_id == version.id, ProcessingRun.config_hash == h
        )
    )
    if existing:
        job = db.scalar(
            select(Job)
            .where(Job.kind == "process", Job.payload["processing_id"].as_string() == existing.id)
            .order_by(Job.created_at.desc())
        )
        if existing.state == "failed" and (
            not job or job.state in ("failed", "cancelled", "succeeded")
        ):
            job = Job(owner_id=actor_id, kind="process", payload={"processing_id": existing.id})
            existing.state = "registered"
            existing.error = None
            db.add(job)
            db.flush()
        return existing, job
    run = ProcessingRun(document_version_id=version.id, config_hash=h, configuration=configuration)
    db.add(run)
    db.flush()
    job = Job(owner_id=actor_id, kind="process", payload={"processing_id": run.id})
    db.add(job)
    db.flush()
    return run, job


class CorpusExecutionCancelled(Exception):
    """The durable job no longer authorizes this worker to mutate its artifact."""


class LegacyReleaseUnverified(ValueError):
    """Historical manifests without integrity baselines require a new release."""


def _execution_fence(db, execution, kind, operation_id, stage=None, complete=False):
    if execution is None:
        return
    job_id, token = execution
    # Do not flush pending artifacts before checking the current database token.
    with db.no_autoflush:
        job = db.scalar(
            select(Job)
            .where(Job.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    key = "processing_id" if kind == "process" else "release_id"
    if (
        not job
        or job.state != "running"
        or job.execution_token != token
        or job.kind != kind
        or job.payload.get(key) != operation_id
    ):
        db.rollback()
        raise CorpusExecutionCancelled(
            "The operation was cancelled or its worker lease was replaced."
        )
    job.updated_at = utcnow()
    if stage:
        job.stage = stage
    if complete:
        job.state = "succeeded"
        job.stage = "complete"
        job.execution_token = None
        job.error = None


def mark_operation_interrupted(db, job, error):
    """Called with the Job locked; retain partial diagnostics, never a usable release.

    A replacement queued/running job owns its own progress. An old worker cannot
    change that attempt's artifact after its token has been revoked.
    """
    if job.kind not in ("process", "release"):
        return
    key, model, complete = (
        ("processing_id", ProcessingRun, ("ready", "quarantined"))
        if job.kind == "process"
        else ("release_id", CorpusRelease, ("validated", "active", "retired"))
    )
    operation_id = job.payload.get(key)
    if not operation_id:
        return
    replacement = db.scalar(
        select(Job.id).where(
            Job.id != job.id,
            Job.kind == job.kind,
            Job.payload[key].as_string() == operation_id,
            Job.state.in_(("queued", "running", "retry_wait")),
        )
    )
    if replacement:
        return
    record = db.scalar(
        select(model)
        .where(model.id == operation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if record and record.state not in complete:
        record.state = "failed"
        record.error = {
            "code": error["code"],
            "message": error["message"],
            "details": {
                **error.get("details", {}),
                "safe_next_action": "Reprocess this source with the same configuration."
                if job.kind == "process"
                else "Build a new release from the same ready processing runs.",
            },
        }


def _processing_stage(db, execution, processing_id, stage):
    _execution_fence(db, execution, "process", processing_id, stage)
    run = db.get(ProcessingRun, processing_id)
    run.state = stage
    run.error = None
    db.commit()


def execute_processing(db, settings, processing_id, execution=None):
    try:
        _execution_fence(db, execution, "process", processing_id)
        run = db.get(ProcessingRun, processing_id)
        if not run:
            raise ValueError("Processing run is unavailable")
        if run.state in ("ready", "quarantined"):
            _execution_fence(db, execution, "process", processing_id, complete=True)
            db.commit()
            return
        version = db.get(DocumentVersion, run.document_version_id)
        _processing_stage(db, execution, processing_id, "validating")
        root = Path(settings.storage_root).resolve()
        path = (root / version.storage_path).resolve()
        if (
            not path.is_relative_to(root)
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != version.raw_hash
        ):
            raise AppError(
                "SOURCE_UNAVAILABLE", detail="Original source is missing or its hash differs."
            )
        _processing_stage(db, execution, processing_id, "parsing")
        # Parsing, model loading and tokenization execute without a Job row lock.
        units = parse(
            path, version.media_type, parser_revision=run.configuration["parser_revision"]
        )
        from pipelines.supplements import apply_page_reviews

        units = apply_page_reviews(
            units, run.configuration.get("page_reviews", []), version.raw_hash
        )
        supplements = run.configuration.get("source_supplements", [])
        if any(
            item.get("kind") not in ("official_html_image_alt", "pdf_image_transcription")
            for item in supplements
        ):
            raise ValueError("Unsupported source supplement kind")
        units = apply_publisher_supplements(
            units,
            [item for item in supplements if item["kind"] == "official_html_image_alt"],
            settings.storage_root,
            version.raw_hash,
        )
        from pipelines.image_transcriptions import apply_image_transcriptions

        units = apply_image_transcriptions(
            units,
            [item for item in supplements if item["kind"] == "pdf_image_transcription"],
            settings.storage_root,
            version.raw_hash,
        )
        if not units:
            raise ValueError("No source units found")
        _processing_stage(db, execution, processing_id, "cleaning")
        exclusions = run.configuration.get("exclusions", {})
        if any(
            not str(sequence).isdigit()
            or int(sequence) not in {u["sequence"] for u in units}
            or not str(reason).strip()
            for sequence, reason in exclusions.items()
        ):
            raise ValueError(
                "Each exclusion must name an existing source unit and contain a documented reason"
            )
        saved = []
        for unit in units:
            id = hashlib.sha256(f"{run.id}:{unit['sequence']}".encode()).hexdigest()[:36]
            if str(unit["sequence"]) in exclusions:
                if not str(exclusions[str(unit["sequence"])]).strip():
                    raise ValueError("Each exclusion needs a documented reason")
                unit["quality"] = "excluded"
                unit["issues"].append(
                    {
                        "code": "DOCUMENTED_EXCLUSION",
                        "severity": "excluded",
                        "message": exclusions[str(unit["sequence"])],
                    }
                )
            saved.append({"id": id, **unit})
        blocked = sum(u["quality"] == "blocked" for u in saved)
        counts = {
            "total_units": len(saved),
            "blocked_units": blocked,
            "excluded_units": sum(u["quality"] == "excluded" for u in saved),
            "ready_units": sum(u["quality"] == "ready" for u in saved),
            "supplemented_units": sum(u["quality"] == "supplemented" for u in saved),
        }
        values = []
        if not blocked:
            _processing_stage(db, execution, processing_id, "chunking")
            cfg = run.configuration
            tokenizer_args = {}
            if cfg["embedding_provider"] == "e5":
                embedder = make_embedding(cfg)
                tokenizer_args = {
                    "tokenizer": embedder.count_input,
                    "model_window": embedder.model.max_seq_length,
                }
            values = chunks(
                saved,
                run.id,
                target=cfg["target"],
                cap=cfg["cap"],
                overlap=cfg["overlap"],
                strategy=cfg["strategy"],
                **tokenizer_args,
            )
            if not values:
                raise ValueError("No usable chunks remain after exclusions")
        _execution_fence(db, execution, "process", processing_id, complete=True)
        for unit in saved:
            if not db.get(SourceUnit, unit["id"]):
                db.add(SourceUnit(processing_id=run.id, **unit))
        for item in values:
            if not db.get(Chunk, item["id"]):
                db.add(Chunk(processing_id=run.id, document_id=version.document_id, **item))
        quality = quality_rows(saved)
        run.counts = {
            **counts,
            "chunks": len(values),
            "quality_report_hash": digest(quality),
            "source_unit_hashes": {
                u["id"]: {"raw_hash": u["raw_hash"], "cleaned_hash": u["cleaned_hash"]}
                for u in quality
            },
        }
        run.state = "quarantined" if blocked else "ready"
        run.error = None
        db.commit()
    except CorpusExecutionCancelled:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        _execution_fence(db, execution, "process", processing_id)
        run = db.get(ProcessingRun, processing_id)
        if run:
            run.state = "failed"
            run.error = {
                "code": getattr(exc, "code", "PROCESSING_FAILED"),
                "message": str(exc)[:300],
            }
        db.commit()
        raise


def processing_quality(db, processing_id, *, _loaded=None):
    # Release validation supplies the same current transaction's bulk-loaded
    # records. Keep all report/hash checks identical to the standalone export.
    if _loaded is None:
        run = db.get(ProcessingRun, processing_id)
        if not run:
            raise AppError("NOT_FOUND")
        version = db.get(DocumentVersion, run.document_version_id)
        units = list(
            db.scalars(
                select(SourceUnit)
                .where(SourceUnit.processing_id == run.id)
                .order_by(SourceUnit.sequence)
            )
        )
    else:
        run, version, units = _loaded
    rows = quality_rows(
        [
            {
                name: getattr(unit, name)
                for name in (
                    "id",
                    "sequence",
                    "page",
                    "section",
                    "raw_text",
                    "cleaned_text",
                    "quality",
                    "issues",
                )
            }
            for unit in units
        ]
    )
    expected = run.counts.get("quality_report_hash")
    if expected and (
        expected != digest(rows)
        or run.counts.get("source_unit_hashes")
        != {u["id"]: {"raw_hash": u["raw_hash"], "cleaned_hash": u["cleaned_hash"]} for u in rows}
    ):
        raise AppError("SOURCE_UNAVAILABLE", detail="Persisted source-unit quality hashes changed.")
    counts = {
        "total_units": len(rows),
        "ready_units": sum(u["quality"] == "ready" for u in rows),
        "blocked_units": sum(u["quality"] == "blocked" for u in rows),
        "excluded_units": sum(u["quality"] == "excluded" for u in rows),
        "warning_units": sum(
            any(issue["severity"] == "warning" for issue in u["issues"]) for u in rows
        ),
        "supplemented_units": sum(u["quality"] == "supplemented" for u in rows),
        "changed_text_units": sum(u["text_changed"] for u in rows),
    }
    if expected and any(
        run.counts.get(key) != value
        for key, value in counts.items()
        if key in ("total_units", "ready_units", "blocked_units", "excluded_units")
    ):
        raise AppError(
            "SOURCE_UNAVAILABLE",
            detail="Persisted quality counts do not reconcile to source units.",
        )
    if expected and run.counts.get("supplemented_units", 0) != counts["supplemented_units"]:
        raise AppError(
            "SOURCE_UNAVAILABLE", detail="Persisted supplemented-unit count does not reconcile."
        )
    return {
        "report_version": "source_quality_v1",
        "processing_id": run.id,
        "document_version_id": version.id,
        "document_id": version.document_id,
        "raw_asset_hash": version.raw_hash,
        "configuration_hash": run.config_hash,
        "configuration": run.configuration,
        "state": run.state,
        "error": run.error,
        "counts": counts,
        "units": rows,
        "quality_report_hash": digest(rows),
        "persisted_hash_status": "verified" if expected else "unrecorded_legacy_or_incomplete",
    }


def processing_diff(db, before_id, after_id):
    before, after = processing_quality(db, before_id), processing_quality(db, after_id)
    if before["document_id"] != after["document_id"]:
        raise AppError("CONFLICT", detail="Compare processing runs of the same document.")
    if any(value["state"] not in ("ready", "quarantined") for value in (before, after)):
        raise AppError(
            "CONFLICT", detail="Processing comparisons require completed ready or quarantined runs."
        )

    def values(processing_id):
        return [
            {
                name: getattr(chunk, name)
                for name in ("id", "text_hash", "section", "pages", "spans")
            }
            for chunk in db.scalars(select(Chunk).where(Chunk.processing_id == processing_id))
        ]

    comparison = compare_processing(
        before["units"], after["units"], values(before_id), values(after_id)
    )
    changes = {
        name: {
            "before": before["configuration"].get(name),
            "after": after["configuration"].get(name),
        }
        for name in sorted(set(before["configuration"]) | set(after["configuration"]))
        if before["configuration"].get(name) != after["configuration"].get(name)
    }
    return {
        "report_version": "processing_diff_v1",
        "before_processing_id": before_id,
        "after_processing_id": after_id,
        "before_document_version_id": before["document_version_id"],
        "after_document_version_id": after["document_version_id"],
        "raw_asset_reused": before["raw_asset_hash"] == after["raw_asset_hash"],
        "configuration_changes": changes,
        **comparison,
    }


def queue_release(db, owner_id, processing_run_ids, configuration_id=None, name="Corpus release"):
    if not processing_run_ids or len(set(processing_run_ids)) != len(processing_run_ids):
        raise AppError("VALIDATION_FAILED", detail="Select distinct ready processing runs.")
    runs = [db.get(ProcessingRun, id) for id in processing_run_ids]
    if any(not r or r.state != "ready" for r in runs):
        raise AppError("CONFLICT", detail="Only ready processing runs can enter a release.")
    config = db.get(Configuration, configuration_id) if configuration_id else None
    if configuration_id and not config:
        raise AppError("NOT_FOUND")
    cfg = corpus_config(config.values if config else {})
    if any(
        not db.get(Document, db.get(DocumentVersion, r.document_version_id).document_id).active
        or db.get(Document, db.get(DocumentVersion, r.document_version_id).document_id).revoked
        for r in runs
    ):
        raise AppError(
            "CONFLICT", detail="Release sources must currently be active and authorized."
        )
    release = CorpusRelease(
        name=name,
        configuration=cfg,
        manifest={"processing_run_ids": processing_run_ids, "configuration_id": configuration_id},
    )
    db.add(release)
    db.flush()
    job = Job(owner_id=owner_id, kind="release", payload={"release_id": release.id})
    db.add(job)
    db.flush()
    return release, job


def execute_release(db, release_id, execution=None):
    try:
        _execution_fence(db, execution, "release", release_id, "embedding")
        release = db.get(CorpusRelease, release_id)
        if not release:
            raise ValueError("Release is unavailable")
        if release.state in ("validated", "active", "retired"):
            _release_rows(db, release)
            _execution_fence(db, execution, "release", release_id, complete=True)
            db.commit()
            return
        cfg = release.configuration
        release.state = "building"
        release.error = None
        db.commit()
        for processing_id in release.manifest["processing_run_ids"]:
            report = processing_quality(db, processing_id)
            if report["state"] != "ready":
                raise ValueError("Release processing run is not ready")
        embedder = make_embedding(cfg)
        values = list(
            db.scalars(
                select(Chunk)
                .where(Chunk.processing_id.in_(release.manifest["processing_run_ids"]))
                .order_by(Chunk.id)
            )
        )
        if not values:
            raise ValueError("Release has no chunks")
        source_units = {
            u.id: u
            for u in db.scalars(
                select(SourceUnit).where(
                    SourceUnit.processing_id.in_(release.manifest["processing_run_ids"])
                )
            )
        }
        for chunk in values:
            _validate_chunk(chunk, source_units)
            document = db.get(Document, chunk.document_id)
            if not document or not document.active or document.revoked:
                raise ValueError("A release source is currently unavailable")
        signature = embedding_signature(cfg)
        cached = {}
        rejected_cache_releases = 0
        prior_releases = list(
            db.scalars(
                select(CorpusRelease)
                .where(CorpusRelease.state.in_(("validated", "active", "retired")))
                .order_by(CorpusRelease.id)
            )
        )
        for prior in prior_releases:
            if embedding_signature(prior.configuration) != signature:
                continue
            try:
                # A finite vector can still have been altered. Verify its complete
                # immutable release before accepting any cache entry from it.
                prior_rows = _release_rows(db, prior)
            except (ValueError, KeyError, TypeError):
                rejected_cache_releases += 1
                continue
            for vector, chunk, _ in prior_rows:
                if vector.model_revision == embedder.revision:
                    cached[(chunk.section, chunk.text_hash)] = _stored_vector(
                        vector.embedding, cfg["dimension"]
                    )
        cache_hits = 0
        for start in range(0, len(values), 32):
            _execution_fence(db, execution, "release", release_id, "embedding")
            db.commit()
            batch = [
                c
                for c in values[start : start + 32]
                if not db.get(ReleaseChunk, (release.id, c.id))
            ]
            if not batch:
                continue
            missing = []
            for chunk in batch:
                cache_key = (chunk.section, chunk.text_hash)
                if cache_key not in cached and cache_key not in {
                    (c.section, c.text_hash) for c in missing
                }:
                    missing.append(chunk)
            vectors = (
                embedder.encode([c.section + "\n" + c.text for c in missing]) if missing else []
            )
            if len(vectors) != len(missing):
                raise ValueError("Embedding count differs from chunk count")
            new_keys = set()
            for chunk, vector in zip(missing, vectors):
                cache_key = (chunk.section, chunk.text_hash)
                cached[cache_key] = validate_vector(vector, cfg["dimension"])
                new_keys.add(cache_key)
            # Encoding never holds the Job row. Stop/recovery can revoke its
            # token while a provider is still busy; returned vectors then vanish.
            _execution_fence(db, execution, "release", release_id, "embedding")
            for chunk in batch:
                cache_key = (chunk.section, chunk.text_hash)
                vector = cached[cache_key]
                if cache_key not in new_keys:
                    cache_hits += 1
                new_keys.discard(cache_key)
                db.add(
                    ReleaseChunk(
                        release_id=release.id,
                        chunk_id=chunk.id,
                        embedding=vector,
                        dimension=cfg["dimension"],
                        model_revision=embedder.revision,
                    )
                )
            db.commit()
        actual = list(db.scalars(select(ReleaseChunk).where(ReleaseChunk.release_id == release.id)))
        if len(actual) != len(values) or any(r.dimension != cfg["dimension"] for r in actual):
            raise ValueError("Release integrity check failed")
        for row in actual:
            if row.model_revision != embedder.revision:
                raise ValueError("Mixed model revisions in release vectors")
            _stored_vector(row.embedding, cfg["dimension"])
        _execution_fence(db, execution, "release", release_id, complete=True)
        release.manifest = {
            **release.manifest,
            "chunk_ids": [c.id for c in values],
            "chunk_count": len(values),
            "vector_count": len(actual),
            "dimension": cfg["dimension"],
            "embedding_revision": embedder.revision,
            "embedding_signature": signature,
            "embedding_hash": _embedding_hash(actual),
            "configuration_hash": digest(cfg),
            "cache_hits": cache_hits,
            "rejected_cache_releases": rejected_cache_releases,
            "content_hash": digest([(c.id, c.text_hash) for c in values]),
        }
        release.state = "validated"
        release.error = None
        db.commit()
    except CorpusExecutionCancelled:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        _execution_fence(db, execution, "release", release_id)
        release = db.get(CorpusRelease, release_id)
        if release and release.state not in ("validated", "active", "retired"):
            release.state = "failed"
            release.error = {"code": "RELEASE_FAILED", "message": str(exc)[:300]}
        db.commit()
        raise


def _stored_vector(vector, dimension):
    normalized = validate_vector(vector, dimension)
    if any(abs(float(before) - after) > 1e-4 for before, after in zip(vector, normalized)):
        raise ValueError("A stored release vector is not normalized")
    # Validation must not re-normalize an immutable stored vector. A second
    # float64 normalization can change float32 least-significant bits when
    # pgvector stores a cache reuse, breaking exact release vector identity.
    return [float(value) for value in vector]


def _embedding_hash(rows):
    # pgvector stores float32; canonicalize before hashing so Python float64
    # inputs and reloaded PostgreSQL values have identical release identities.
    return digest(
        [
            (row.chunk_id, [struct.pack("!f", float(v)).hex() for v in row.embedding])
            for row in sorted(rows, key=lambda r: r.chunk_id)
        ]
    )


def _validate_chunk(chunk, units):
    if hashlib.sha256(chunk.text.encode()).hexdigest() != chunk.text_hash or not chunk.text.strip():
        raise ValueError("Chunk text/hash integrity mismatch")
    if not chunk.spans or chunk.pages != sorted({span["page"] for span in chunk.spans}):
        raise ValueError("Chunk physical locators are incomplete")
    previous_end = 0
    for span in chunk.spans:
        unit = units.get(span["unit_id"])
        if (
            not unit
            or unit.processing_id != chunk.processing_id
            or unit.quality != "ready"
            or unit.page != span["page"]
        ):
            raise ValueError("Chunk span refers to a foreign or unavailable source unit")
        start, end = span["start"], span["end"]
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(unit.cleaned_text)
        ):
            raise ValueError("Chunk source character span is invalid")
        passage = unit.cleaned_text[start:end]
        local_start = span.get("chunk_start", chunk.text.find(passage, previous_end))
        local_end = span.get("chunk_end", local_start + len(passage))
        if (
            local_start < previous_end
            or chunk.text[local_start:local_end] != passage
            or chunk.text[previous_end:local_start].strip()
        ):
            raise ValueError("Chunk text does not reconstruct from its source spans")
        previous_end = local_end
    if chunk.text[previous_end:].strip():
        raise ValueError("Chunk includes untraceable trailing text")


def _release_rows(db, release, require_active=False, *, provenance=None):
    rows = list(
        db.execute(
            select(ReleaseChunk, Chunk, Document)
            .join(Chunk, Chunk.id == ReleaseChunk.chunk_id)
            .join(Document, Document.id == Chunk.document_id)
            .where(ReleaseChunk.release_id == release.id)
            .order_by(Chunk.id)
        )
    )
    manifest = release.manifest
    if any(
        not manifest.get(key)
        for key in ("configuration_hash", "embedding_signature", "embedding_hash")
    ):
        raise LegacyReleaseUnverified(
            "This legacy release has no saved configuration/vector fingerprints. Reprocess its original sources and build a new validated release; historical evidence remains unchanged."
        )
    if (
        len(rows) != manifest.get("chunk_count")
        or len(rows) != manifest.get("vector_count")
        or {chunk.id for _, chunk, _ in rows} != set(manifest.get("chunk_ids", []))
    ):
        raise ValueError("Released chunk/vector membership differs from its manifest")
    if manifest.get("configuration_hash") != digest(release.configuration):
        raise ValueError("Immutable release configuration hash changed")
    if manifest.get("embedding_signature") != embedding_signature(release.configuration):
        raise ValueError("Embedding preprocessing/model signature changed")
    if manifest.get("embedding_hash") != _embedding_hash([vector for vector, _, _ in rows]):
        raise ValueError("Released embedding values differ from the immutable manifest")
    if manifest.get("dimension") != release.configuration.get("dimension") or manifest.get(
        "embedding_revision"
    ) != release.configuration.get("embedding_revision"):
        raise ValueError("Release vector metadata differs from its immutable configuration")
    if digest([(chunk.id, chunk.text_hash) for _, chunk, _ in rows]) != manifest.get(
        "content_hash"
    ):
        raise ValueError("Released content manifest hash differs")
    runs = {
        r.id: r
        for r in db.scalars(
            select(ProcessingRun).where(ProcessingRun.id.in_(manifest["processing_run_ids"]))
        )
    }
    # Strong references avoid SQLAlchemy's weak identity-map eviction causing
    # one DocumentVersion lookup for each interleaved chunk of a large corpus.
    versions = {
        v.id: v
        for v in db.scalars(
            select(DocumentVersion).where(
                DocumentVersion.id.in_([r.document_version_id for r in runs.values()])
            )
        )
    }
    units = {
        u.id: u
        for u in db.scalars(
            select(SourceUnit)
            .where(SourceUnit.processing_id.in_(manifest["processing_run_ids"]))
            .order_by(SourceUnit.sequence)
        )
    }
    units_by_run = {processing_id: [] for processing_id in runs}
    for unit in units.values():
        units_by_run[unit.processing_id].append(unit)
    for processing_id, processing in runs.items():
        version = versions.get(processing.document_version_id)
        if not version:
            raise ValueError("A released source asset is unavailable")
        try:
            processing_quality(
                db, processing_id, _loaded=(processing, version, units_by_run[processing_id])
            )
        except AppError as exc:
            raise ValueError("Released source-unit quality hashes changed") from exc
    for vector, chunk, document in rows:
        processing = runs.get(chunk.processing_id)
        if not processing or processing.state != "ready":
            raise ValueError("A released processing run is unavailable")
        version = versions.get(processing.document_version_id)
        if not version or version.document_id != document.id:
            raise ValueError("Chunk source asset differs from the processing lineage")
        _validate_chunk(chunk, units)
        if (
            vector.dimension != manifest["dimension"]
            or vector.model_revision != manifest["embedding_revision"]
        ):
            raise ValueError("Mixed embedding dimensions or model revisions in release")
        _stored_vector(vector.embedding, manifest["dimension"])
        if require_active and (not document.active or document.revoked):
            raise ValueError("A release source is currently unavailable")
    if provenance is not None:
        provenance["media_types"] = {
            r.id: versions[r.document_version_id].media_type for r in runs.values()
        }
        provenance["visual_pages"] = {
            (u.processing_id, u.page)
            for u in units.values()
            if any(issue["code"] == "UNEXTRACTED_VISUAL_CONTENT" for issue in u.issues)
        }
    return rows


def activate(db, release_id):
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(5703002)"))
    pointer = db.scalar(select(ActiveCorpus).where(ActiveCorpus.id == 1).with_for_update())
    if not pointer:
        pointer = ActiveCorpus(id=1)
        db.add(pointer)
        db.flush()
    release = db.get(CorpusRelease, release_id)
    if not release or release.state not in ("validated", "retired", "active"):
        raise AppError("CONFLICT", detail="Release is not validated and intact.")
    try:
        _release_rows(db, release, require_active=True)
    except (ValueError, KeyError, TypeError) as exc:
        raise AppError(
            "CONFLICT",
            detail="Release integrity or current source availability failed: " + str(exc),
        ) from exc
    if pointer.release_id and pointer.release_id != release_id:
        db.get(CorpusRelease, pointer.release_id).state = "retired"
    pointer.release_id = release_id
    release.state = "active"
    db.flush()
    return release


def retrieve(db, query, release_id, variant=None, top_k=None, *, runtime_device=None):
    release = db.get(CorpusRelease, release_id)
    if not release or release.state not in ("active", "retired", "validated"):
        raise AppError("SOURCE_UNAVAILABLE", detail="Pinned corpus is unavailable.")
    cfg = release.configuration
    k = cfg.get("top_k", 5) if top_k is None else top_k
    variant = variant or cfg.get("retriever", "R0")
    if type(k) is not int or not 1 <= k <= 50 or variant not in ("R0", "R1", "R2", "R3"):
        raise AppError("VALIDATION_FAILED", detail="Invalid retrieval depth or variant.")
    provenance = {}
    try:
        integrity_rows = _release_rows(db, release, provenance=provenance)
    except (ValueError, KeyError, TypeError) as exc:
        raise AppError(
            "SOURCE_UNAVAILABLE",
            detail=str(exc)
            if isinstance(exc, LegacyReleaseUnverified)
            else "Pinned release failed integrity validation.",
        ) from exc
    query_rows = (
        select(ReleaseChunk, Chunk, Document)
        .join(Chunk, Chunk.id == ReleaseChunk.chunk_id)
        .join(Document, Document.id == Chunk.document_id)
        .where(
            ReleaseChunk.release_id == release_id,
            Document.active.is_(True),
            Document.revoked.is_(False),
        )
    )
    media_types = provenance["media_types"]
    visual_pages = provenance["visual_pages"]

    def row(value):
        embedding, chunk, doc = value
        page_label = (
            "PDF physical pages"
            if media_types[chunk.processing_id] == "application/pdf"
            else "source pages"
        )
        visual = any((chunk.processing_id, page) in visual_pages for page in chunk.pages)
        warning = "Figures or formulas may require viewing the original PDF."
        locator = f"{chunk.section}; {page_label} " + ", ".join(map(str, chunk.pages))
        return {
            "chunk_id": chunk.id,
            "asset_id": doc.id,
            "processing_id": chunk.processing_id,
            "source_title": doc.title,
            "source_url": doc.source_url or None,
            "license": doc.license or None,
            "section": chunk.section,
            "pages": chunk.pages,
            "locator": locator + ("; " + warning if visual else ""),
            "text": chunk.text,
            "text_hash": chunk.text_hash,
            "quality_warnings": [{"code": "UNEXTRACTED_VISUAL_CONTENT", "message": warning}]
            if visual
            else [],
        }

    values = [value for value in integrity_rows if value[2].active and not value[2].revoked]
    if variant == "R1":
        return bm25(query, [row(v) for v in values], k)
    if not values:
        return []
    embedder = (
        make_embedding(cfg, runtime_device=runtime_device)
        if runtime_device is not None
        else make_embedding(cfg)
    )
    encoded = embedder.encode([query], kind="query")
    if len(encoded) != 1:
        raise AppError("SOURCE_UNAVAILABLE", detail="Query embedding count is invalid.")
    vector = validate_vector(encoded[0], cfg["dimension"])
    if db.bind.dialect.name == "postgresql":
        distance = ReleaseChunk.embedding.cosine_distance(vector)
        ranked = list(db.execute(query_rows.order_by(distance, Chunk.id).limit(50)))
        dense = [
            {
                **row(v),
                "score": sum(float(a) * b for a, b in zip(v[0].embedding, vector)),
                "score_type": "cosine",
            }
            for v in ranked
        ]
    else:
        dense = sorted(
            [
                {
                    **row(v),
                    "score": sum(float(a) * b for a, b in zip(v[0].embedding, vector)),
                    "score_type": "cosine",
                }
                for v in values
            ],
            key=lambda r: (-r["score"], r["chunk_id"]),
        )[:50]
    if variant == "R0":
        return dense[:k]
    lexical = bm25(query, [row(v) for v in values], 50)
    fused = rrf([dense, lexical], max(20, k))
    if variant == "R2":
        return fused[:k]
    if variant == "R3":
        return CrossEncoderReranker(
            cfg.get("reranker_model", "BAAI/bge-reranker-base"),
            cfg.get("reranker_revision"),
            device=runtime_device or cfg.get("reranker_device"),
            cache_folder=cfg.get("reranker_cache_folder"),
        ).rerank(query, fused, k)
    raise AppError("VALIDATION_FAILED", detail="Unsupported retrieval variant.")
