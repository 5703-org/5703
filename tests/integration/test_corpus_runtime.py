"""Actual PostgreSQL corpus lifecycle, exact vectors and immutable provenance."""

from uuid import uuid4
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import hashlib
import random
import struct
import pytest
from sqlalchemy import select, func, event
from app.core.exceptions import AppError
from app.modules.knowledge.models import (
    Document,
    DocumentVersion,
    ProcessingRun,
    SourceUnit,
    Chunk,
    CorpusRelease,
    ReleaseChunk,
    ActiveCorpus,
)
from app.modules.knowledge import service
from app.modules.answering.models import Job
from app.worker import recover_stale
from retrieval.embedding import make_embedding
from .test_chat_runtime import call, corpus, session, submit, finish


def upload(rt, raw, filename=None):
    response = rt.client.post(
        "/api/v1/documents",
        headers=rt.headers("admin@example.com"),
        data={"title": "Authored corpus " + uuid4().hex[:8]},
        files={"file": (filename or uuid4().hex + ".txt", raw, "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def process(rt, document_id, configuration=None, exclusions=None):
    admin = rt.headers("admin@example.com")
    result = call(
        rt,
        "POST",
        f"/documents/{document_id}/process",
        {"configuration": configuration or {}, "exclusions": exclusions or {}},
        admin,
        202,
    )
    assert rt.work()
    return result, call(rt, "GET", "/jobs/" + result["job_id"], headers=admin)


def build(rt, processing_id, configuration_id=None):
    admin = rt.headers("admin@example.com")
    result = call(
        rt,
        "POST",
        "/corpus/releases",
        {"processing_run_ids": [processing_id], "configuration_id": configuration_id},
        admin,
        202,
    )
    assert rt.work()
    return result, call(rt, "GET", "/jobs/" + result["job_id"], headers=admin)


def test_upload_type_path_limits_recursive_secrets_and_raw_dedup(runtime):
    rt = runtime
    admin = rt.headers("admin@example.com")
    for filename, raw, status in [
        ("../escape.txt", b"Authored content", 422),
        ("fake.pdf", b"This is not a PDF", 415),
        ("binary.txt", b"Bad\x00content", 415),
        ("source.exe", b"MZnot executable", 415),
    ]:
        result = rt.client.post(
            "/api/v1/documents",
            headers=admin,
            data={"title": "Rejected fixture"},
            files={"file": (filename, raw, "text/plain")},
        )
        assert result.status_code == status, result.text
    old = rt.settings.max_upload_bytes
    rt.settings.max_upload_bytes = 64
    result = rt.client.post(
        "/api/v1/documents",
        headers=admin,
        data={"title": "Too large"},
        files={"file": ("large.txt", b"a" * 65, "text/plain")},
    )
    assert result.status_code == 413
    rt.settings.max_upload_bytes = old
    call(
        rt,
        "POST",
        "/configurations",
        {
            "kind": "retrieval",
            "name": "Unsafe",
            "values": {"nested": {"api_key": "test-only-placeholder"}},
        },
        admin,
        422,
    )
    raw = ("A unique authored source. " + uuid4().hex).encode()
    first = upload(rt, raw)
    second = upload(rt, raw)
    assert second["duplicate"] is True and first["version"]["id"] == second["version"]["id"]
    assert first["document"]["id"] == second["document"]["id"]
    with rt.db() as db:
        version = db.get(DocumentVersion, first["version"]["id"])
        assert Path(rt.settings.storage_root, version.storage_path).read_bytes() == raw
        assert version.raw_hash == hashlib.sha256(raw).hexdigest()
        assert (
            db.scalar(
                select(func.count())
                .select_from(DocumentVersion)
                .where(DocumentVersion.raw_hash == version.raw_hash)
            )
            == 1
        )


def test_quarantine_inspectable_exclusion_and_processing_lineage(runtime):
    rt = runtime
    admin = rt.headers("admin@example.com")
    _, active = corpus(rt)
    raw = (
        "# Sound text\nCells contain membranes and genetic material. "
        + uuid4().hex
        + "\n# Damaged extraction\nThis source contains a replacement \ufffd character."
    ).encode()
    imported = upload(rt, raw)
    first, job = process(rt, imported["document"]["id"])
    assert job["state"] == "succeeded"
    with rt.db() as db:
        run = db.get(ProcessingRun, first["processing_id"])
        assert run.state == "quarantined" and run.counts["blocked_units"] == 1
        bad = db.scalar(
            select(SourceUnit).where(
                SourceUnit.processing_id == run.id, SourceUnit.quality == "blocked"
            )
        )
        assert "\ufffd" in bad.raw_text and bad.issues
        sequence = str(bad.sequence)
        assert db.get(ActiveCorpus, 1).release_id == active["release_id"]
    call(
        rt, "POST", "/corpus/releases", {"processing_run_ids": [first["processing_id"]]}, admin, 409
    )
    second, job = process(
        rt,
        imported["document"]["id"],
        exclusions={sequence: "Authored damaged fragment excluded after source inspection."},
    )
    assert second["processing_id"] != first["processing_id"] and job["state"] == "succeeded"
    with rt.db() as db:
        new = db.get(ProcessingRun, second["processing_id"])
        old = db.get(ProcessingRun, first["processing_id"])
        assert new.state == "ready" and new.document_version_id == old.document_version_id
        assert new.counts["excluded_units"] == 1
        chunks = list(db.scalars(select(Chunk).where(Chunk.processing_id == new.id)))
        assert chunks and all("\ufffd" not in chunk.text for chunk in chunks)
    bad, job = process(rt, imported["document"]["id"], exclusions={"999": "Invalid unit reference"})
    assert job["state"] == "failed"
    with rt.db() as db:
        assert db.get(ProcessingRun, bad["processing_id"]).state == "failed"
        assert db.get(ActiveCorpus, 1).release_id == active["release_id"]


def test_reprocessing_creates_new_chunks_while_old_evidence_survives(runtime):
    rt = runtime
    doc, release = corpus(rt)
    s = session(rt)
    answer = finish(rt, submit(rt, s))
    old_evidence = call(
        rt, "GET", f"/answers/{answer['id']}/evidence/{answer['response']['citations'][0]}"
    )
    second, job = process(rt, doc["id"], configuration={"target": 160, "overlap": 20})
    assert job["state"] == "succeeded"
    with rt.db() as db:
        new_chunks = list(
            db.scalars(select(Chunk).where(Chunk.processing_id == second["processing_id"]))
        )
        assert new_chunks and all(c.id != old_evidence["chunk_id"] for c in new_chunks)
        run = db.get(ProcessingRun, second["processing_id"])
        old_run = db.get(ProcessingRun, old_evidence["processing_id"])
        assert (
            run.document_version_id == old_run.document_version_id
            and run.config_hash != old_run.config_hash
        )
    same = call(
        rt,
        "POST",
        f"/documents/{doc['id']}/process",
        {"configuration": {"target": 160, "overlap": 20}},
        rt.headers("admin@example.com"),
        202,
    )
    assert same["processing_id"] == second["processing_id"] and same["job_id"] == second["job_id"]
    current = call(
        rt, "GET", f"/answers/{answer['id']}/evidence/{answer['response']['citations'][0]}"
    )
    assert current == old_evidence


def test_quality_hash_export_and_semantic_processing_diff_ignore_new_ids(runtime):
    rt = runtime
    admin = rt.headers("admin@example.com")
    raw = (
        "# Energy\n\ufeffPhotosynthesis\u00ad\n captures  light energy. "
        + uuid4().hex
        + "\n# Cells\nCell membranes regulate transport."
    ).encode()
    imported = upload(rt, raw)
    first, _ = process(rt, imported["document"]["id"])
    quality = call(rt, "GET", f"/processing-runs/{first['processing_id']}/quality", headers=admin)
    assert quality["persisted_hash_status"] == "verified" and quality["counts"]["total_units"] == 2
    assert quality["counts"]["changed_text_units"] >= 1
    for unit in quality["units"]:
        assert unit["raw_hash"] == hashlib.sha256(unit["raw_text"].encode()).hexdigest()
        assert unit["cleaned_hash"] == hashlib.sha256(unit["cleaned_text"].encode()).hexdigest()
    same_content, _ = process(rt, imported["document"]["id"], {"target": 160, "overlap": 20})
    comparison = call(
        rt,
        "GET",
        f"/processing-runs/{first['processing_id']}/diff/{same_content['processing_id']}",
        headers=admin,
    )
    assert comparison["raw_asset_reused"] and comparison["configuration_changes"]["target"] == {
        "before": 320,
        "after": 160,
    }
    assert comparison["counts"]["chunks"] == {
        "unchanged": 2,
        "changed": 0,
        "added": 0,
        "removed": 0,
    }
    assert all(
        pair["before"]["id"] != pair["after"]["id"] for pair in comparison["chunks"]["unchanged"]
    )
    excluded, _ = process(
        rt,
        imported["document"]["id"],
        exclusions={"2": "Authored operator exclusion for comparison verification."},
    )
    comparison = call(
        rt,
        "GET",
        f"/processing-runs/{first['processing_id']}/diff/{excluded['processing_id']}",
        headers=admin,
    )
    assert (
        comparison["counts"]["source_units"]["changed"] == 1
        and comparison["counts"]["chunks"]["removed"] == 1
    )
    call(rt, "GET", f"/processing-runs/{first['processing_id']}/quality", status=403)
    with rt.db() as db:
        unit = db.scalar(
            select(SourceUnit).where(SourceUnit.processing_id == first["processing_id"])
        )
        original = unit.raw_text
        unit.raw_text = "An unauthorized changed raw extraction"
        db.commit()
    try:
        call(
            rt,
            "GET",
            f"/processing-runs/{first['processing_id']}/quality",
            headers=admin,
            status=503,
        )
    finally:
        with rt.db() as db:
            db.get(SourceUnit, unit.id).raw_text = original
            db.commit()


def test_processing_diff_reports_split_groups_by_overlapping_source_spans(runtime):
    rt = runtime
    admin = rt.headers("admin@example.com")
    raw = (
        "# Long authored source\n" + " ".join(f"term{i}" for i in range(140)) + " " + uuid4().hex
    ).encode()
    imported = upload(rt, raw)
    first, _ = process(rt, imported["document"]["id"], {"target": 80, "overlap": 10})
    second, _ = process(rt, imported["document"]["id"], {"target": 40, "overlap": 5})
    comparison = call(
        rt,
        "GET",
        f"/processing-runs/{first['processing_id']}/diff/{second['processing_id']}",
        headers=admin,
    )
    assert comparison["counts"]["chunks"]["changed"] >= 1
    assert comparison["counts"]["chunks"]["added"] == comparison["counts"]["chunks"]["removed"] == 0
    group = comparison["chunks"]["changed"][0]
    assert group["before"] and group["after"] and group["requires_qrel_review"]
    assert group["before"][0]["spans"][0]["raw_hash"] == group["after"][0]["spans"][0]["raw_hash"]


def test_failed_index_preserves_pointer_cache_and_a_b_a_rollback(runtime):
    rt = runtime
    admin = rt.headers("admin@example.com")
    doc, a = corpus(rt)
    detail = call(rt, "GET", "/documents/" + doc["id"], headers=admin)
    processing_id = detail["processing_runs"][0]["id"]
    config = call(
        rt,
        "POST",
        "/configurations",
        {
            "kind": "retrieval",
            "name": "Broken authored embedder",
            "values": {"embedding_revision": "broken-fixture-v1"},
        },
        admin,
        201,
    )
    fake = SimpleNamespace(
        revision="broken-fixture-v1", encode=lambda texts, **kwargs: [[1.0, 0.0] for _ in texts]
    )
    with patch("app.modules.knowledge.service.make_embedding", return_value=fake):
        failed, job = build(rt, processing_id, config["id"])
    assert job["state"] == "failed"
    with rt.db() as db:
        assert db.get(CorpusRelease, failed["release_id"]).state == "failed"
        assert db.get(ActiveCorpus, 1).release_id == a["release_id"]
    call(rt, "POST", "/corpus/releases/" + failed["release_id"] + "/activate", {}, admin, 409)
    adapter = make_embedding(service.DEFAULT_CONFIG)
    with (
        patch.object(adapter, "encode", wraps=adapter.encode) as encode,
        patch("app.modules.knowledge.service.make_embedding", return_value=adapter),
    ):
        b, job = build(rt, processing_id)
    assert job["state"] == "succeeded" and encode.call_count == 0
    with rt.db() as db:
        release = db.get(CorpusRelease, b["release_id"])
        assert release.manifest["cache_hits"] == release.manifest["chunk_count"]
        assert release.manifest["embedding_hash"]
    call(rt, "POST", "/corpus/releases/" + b["release_id"] + "/activate", {}, admin)
    call(rt, "POST", "/corpus/releases/" + a["release_id"] + "/rollback", {}, admin)
    with rt.db() as db:
        assert db.get(ActiveCorpus, 1).release_id == a["release_id"]
        assert db.get(CorpusRelease, a["release_id"]).state == "active"
        assert db.get(CorpusRelease, b["release_id"]).state == "retired"


def test_actual_pgvector_rankings_bm25_independence_and_invalid_mixed_vectors(runtime):
    rt = runtime
    admin = rt.headers("admin@example.com")
    raw = (
        "# Alpha\nAlpha particles are used in this authored test.\n# Beta\nBeta particles are used in this authored test.\n# Gamma\nGamma particles are used in this authored test. "
        + uuid4().hex
    ).encode()
    imported = upload(rt, raw)
    processed, job = process(rt, imported["document"]["id"])
    config = call(
        rt,
        "POST",
        "/configurations",
        {
            "kind": "retrieval",
            "name": "Known 2D vectors",
            "values": {"dimension": 2, "embedding_revision": "known-vector-fixture-v1"},
        },
        admin,
        201,
    )
    release, job = build(rt, processed["processing_id"], config["id"])
    assert job["state"] == "succeeded"
    with rt.db() as db:
        rows = list(
            db.execute(
                select(ReleaseChunk, Chunk)
                .join(Chunk, Chunk.id == ReleaseChunk.chunk_id)
                .where(ReleaseChunk.release_id == release["release_id"])
            )
        )
        for vector, chunk in rows:
            vector.embedding = {"Alpha": [1.0, 0.0], "Beta": [0.6, 0.8], "Gamma": [0.0, 1.0]}[
                chunk.section
            ]
        frozen = db.get(CorpusRelease, release["release_id"])
        frozen.manifest = {
            **frozen.manifest,
            "embedding_hash": service._embedding_hash([v for v, _ in rows]),
        }
        db.commit()
    call(rt, "POST", "/corpus/releases/" + release["release_id"] + "/activate", {}, admin)
    fake = SimpleNamespace(encode=lambda texts, **kwargs: [[1.0, 0.0]])
    statements = []

    def capture_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(rt.engine, "before_cursor_execute", capture_sql)
    try:
        with (
            rt.db() as db,
            patch("app.modules.knowledge.service.make_embedding", return_value=fake),
        ):
            ranked = service.retrieve(db, "Alpha", release["release_id"], top_k=3)
            assert [r["section"] for r in ranked] == ["Alpha", "Beta", "Gamma"]
            assert [r["score"] for r in ranked] == pytest.approx([1, 0.6, 0])
        assert any(
            "ORDER BY release_chunks.embedding <=>" in sql and "LIMIT" in sql for sql in statements
        )
    finally:
        event.remove(rt.engine, "before_cursor_execute", capture_sql)
    with (
        rt.db() as db,
        patch(
            "app.modules.knowledge.service.make_embedding",
            side_effect=AssertionError("BM25 must not invoke dense embedding"),
        ),
    ):
        assert (
            service.retrieve(db, "Beta", release["release_id"], variant="R1")[0]["section"]
            == "Beta"
        )
    with rt.db() as db:
        row = db.scalar(
            select(ReleaseChunk).where(ReleaseChunk.release_id == release["release_id"])
        )
        original = list(row.embedding)
        row.embedding = [1.0, 0.0, 0.0]
        db.commit()
    with rt.db() as db:
        with pytest.raises(AppError) as error:
            service.retrieve(db, "Alpha", release["release_id"])
        assert error.value.code == "SOURCE_UNAVAILABLE"
    call(rt, "POST", "/corpus/releases/" + release["release_id"] + "/activate", {}, admin, 409)
    with rt.db() as db:
        row = db.scalar(
            select(ReleaseChunk).where(
                ReleaseChunk.release_id == release["release_id"],
                ReleaseChunk.chunk_id == row.chunk_id,
            )
        )
        row.embedding = original
        db.commit()


def test_source_deactivation_filters_current_retrieval_and_restore_recovers(runtime):
    rt = runtime
    doc, release = corpus(rt)
    admin = rt.headers("admin@example.com")
    with rt.db() as db:
        assert service.retrieve(db, "Photosynthesis", release["release_id"])
    call(rt, "POST", "/documents/" + doc["id"] + "/deactivate", {}, admin)
    with rt.db() as db:
        assert service.retrieve(db, "Photosynthesis", release["release_id"]) == []
    call(rt, "POST", "/corpus/releases/" + release["release_id"] + "/activate", {}, admin, 409)
    call(rt, "POST", "/documents/" + doc["id"] + "/restore", {}, admin)
    with rt.db() as db:
        assert service.retrieve(db, "Photosynthesis", release["release_id"])


def test_large_multisource_retrieval_bulk_reads_preserve_integrity_checks(runtime):
    rt = runtime
    admin = rt.headers("admin@example.com")
    processing_ids = []
    for book in range(3):
        raw = "\n".join(
            f"# Book {book} topic {number}\nPhotosynthesis stores solar energy in sugar. "
            f"This authored source section explains chloroplast reactions {uuid4().hex}."
            for number in range(20)
        ).encode()
        imported = upload(rt, raw)
        processed, job = process(rt, imported["document"]["id"])
        assert job["state"] == "succeeded"
        processing_ids.append(processed["processing_id"])
    release = call(
        rt, "POST", "/corpus/releases", {"processing_run_ids": processing_ids}, admin, 202
    )
    assert rt.work()
    assert call(rt, "GET", "/jobs/" + release["job_id"], headers=admin)["state"] == "succeeded"
    statements = []

    def capture_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(rt.engine, "before_cursor_execute", capture_sql)
    try:
        with rt.db() as db:
            hits = service.retrieve(db, "photosynthesis solar energy", release["release_id"])
            assert len(hits) == 5
        # All 60 chunks are validated, but each lineage/source table is fetched
        # once, rather than issuing a lookup for every interleaved source chunk.
        assert len(statements) <= 8
        assert sum("FROM document_versions" in sql for sql in statements) == 1
        assert sum("FROM source_units" in sql for sql in statements) == 1
        assert any("ORDER BY release_chunks.embedding <=>" in sql for sql in statements)
    finally:
        event.remove(rt.engine, "before_cursor_execute", capture_sql)
    with rt.db() as db:
        unit = db.scalar(select(SourceUnit).where(SourceUnit.processing_id == processing_ids[0]))
        original = unit.raw_text
        unit_id = unit.id
        unit.raw_text += " A corrupted raw source change."
        db.commit()
    try:
        with rt.db() as db, pytest.raises(AppError) as error:
            service.retrieve(db, "photosynthesis", release["release_id"])
        assert error.value.code == "SOURCE_UNAVAILABLE"
    finally:
        with rt.db() as db:
            db.get(SourceUnit, unit_id).raw_text = original
            db.commit()


def test_cache_rejects_finite_but_corrupted_prior_vectors_and_reencodes(runtime):
    rt = runtime
    admin = rt.headers("admin@example.com")
    doc, a = corpus(rt)
    detail = call(rt, "GET", "/documents/" + doc["id"], headers=admin)
    processing_id = detail["processing_runs"][0]["id"]
    with rt.db() as db:
        prior = db.scalar(select(ReleaseChunk).where(ReleaseChunk.release_id == a["release_id"]))
        chunk_id = prior.chunk_id
        original = list(prior.embedding)
        prior.embedding = [-float(value) for value in original]
        db.commit()
    try:
        adapter = make_embedding(service.DEFAULT_CONFIG)
        with (
            patch.object(adapter, "encode", wraps=adapter.encode) as encode,
            patch("app.modules.knowledge.service.make_embedding", return_value=adapter),
        ):
            b, job = build(rt, processing_id)
        assert job["state"] == "succeeded" and encode.call_count >= 1
        with rt.db() as db:
            repaired = db.get(CorpusRelease, b["release_id"])
            assert repaired.manifest["rejected_cache_releases"] >= 1
            assert list(
                db.get(ReleaseChunk, (b["release_id"], chunk_id)).embedding
            ) == pytest.approx(original)
            assert db.get(ActiveCorpus, 1).release_id == a["release_id"]
        call(rt, "POST", "/corpus/releases/" + a["release_id"] + "/activate", {}, admin, 409)
    finally:
        with rt.db() as db:
            db.get(ReleaseChunk, (a["release_id"], chunk_id)).embedding = original
            db.commit()


def test_reusing_valid_float32_vectors_preserves_exact_bits_and_manifest(runtime):
    from retrieval.embedding import validate_vector

    rt = runtime
    imported = upload(
        rt,
        ("# Exact cache\nAuthored source for immutable vector identity. " + uuid4().hex).encode(),
    )
    processed, job = process(rt, imported["document"]["id"])
    assert job["state"] == "succeeded"
    rng = random.Random(35)
    vector = validate_vector([rng.uniform(-1, 1) for _ in range(2)] + [0.0] * 382, 384)
    # This fixture specifically exposes the second-normalization rounding bug.
    stored = [struct.unpack("!f", struct.pack("!f", value))[0] for value in vector]
    assert any(
        struct.pack("!f", a) != struct.pack("!f", b)
        for a, b in zip(stored, validate_vector(stored, 384))
    )
    config = call(
        rt,
        "POST",
        "/configurations",
        {
            "kind": "retrieval",
            "name": "Exact float32 fixture",
            "values": {"embedding_revision": "float32-cache-fixture-v1"},
        },
        rt.headers("admin@example.com"),
        201,
    )
    adapter = SimpleNamespace(
        revision="float32-cache-fixture-v1", encode=lambda texts, **kwargs: [vector for _ in texts]
    )
    with patch("app.modules.knowledge.service.make_embedding", return_value=adapter):
        first, job = build(rt, processed["processing_id"], config["id"])
    assert job["state"] == "succeeded"
    adapter.encode = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("Exact compatible vectors must be reused")
    )
    with patch("app.modules.knowledge.service.make_embedding", return_value=adapter):
        second, job = build(rt, processed["processing_id"], config["id"])
    assert job["state"] == "succeeded"
    with rt.db() as db:
        a, b = (db.get(CorpusRelease, item["release_id"]) for item in (first, second))
        assert a.manifest["embedding_hash"] == b.manifest["embedding_hash"]
        assert b.manifest["cache_hits"] == b.manifest["vector_count"]
        before = {
            row.chunk_id: [struct.pack("!f", float(v)) for v in row.embedding]
            for row in db.scalars(select(ReleaseChunk).where(ReleaseChunk.release_id == a.id))
        }
        after = {
            row.chunk_id: [struct.pack("!f", float(v)) for v in row.embedding]
            for row in db.scalars(select(ReleaseChunk).where(ReleaseChunk.release_id == b.id))
        }
        assert before == after


def test_legacy_release_without_saved_hashes_requires_explicit_new_build(runtime):
    rt = runtime
    admin = rt.headers("admin@example.com")
    doc, current = corpus(rt)
    detail = call(rt, "GET", "/documents/" + doc["id"], headers=admin)
    processing_id = detail["processing_runs"][0]["id"]
    old, _ = build(rt, processing_id)
    with rt.db() as db:
        legacy = db.get(CorpusRelease, old["release_id"])
        legacy.manifest = {
            key: value
            for key, value in legacy.manifest.items()
            if key not in ("configuration_hash", "embedding_signature", "embedding_hash")
        }
        original = dict(legacy.manifest)
        db.commit()
    response = rt.client.post(
        "/api/v1/corpus/releases/" + old["release_id"] + "/activate", json={}, headers=admin
    )
    assert (
        response.status_code == 409
        and "legacy release" in response.text
        and "Reprocess" in response.text
    )
    with rt.db() as db:
        assert db.get(CorpusRelease, old["release_id"]).manifest == original
        assert db.get(ActiveCorpus, 1).release_id == current["release_id"]
        with pytest.raises(AppError, match="legacy release"):
            service.retrieve(db, "photosynthesis", old["release_id"])
    rebuilt, job = build(rt, processing_id)
    assert job["state"] == "succeeded"
    call(rt, "POST", "/corpus/releases/" + rebuilt["release_id"] + "/activate", {}, admin)
    with rt.db() as db:
        assert db.get(CorpusRelease, old["release_id"]).manifest == original
        assert db.get(ActiveCorpus, 1).release_id == rebuilt["release_id"]


@pytest.mark.parametrize("interruption", ["cancel", "recover"])
def test_process_stop_and_stale_recovery_fence_late_publication_and_allow_rerun(
    runtime, interruption
):
    rt = runtime
    admin = rt.headers("admin@example.com")
    imported = upload(
        rt, ("Membranes regulate transport in this authored fixture. " + uuid4().hex).encode()
    )
    queued = call(rt, "POST", f"/documents/{imported['document']['id']}/process", {}, admin, 202)
    entered = Event()
    resume = Event()
    original = service.parse

    def blocked_parse(*args, **kwargs):
        entered.set()
        assert resume.wait(10), "Test failed to release its authored parser"
        return original(*args, **kwargs)

    with (
        patch("app.modules.knowledge.service.parse", side_effect=blocked_parse),
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        work = pool.submit(rt.work)
        try:
            assert entered.wait(5), "Worker did not enter parsing"
            if interruption == "cancel":
                stop = pool.submit(
                    call, rt, "POST", "/jobs/" + queued["job_id"] + "/cancel", {}, admin
                )
                assert stop.result(timeout=3)["state"] == "cancelled"
            else:
                stop = pool.submit(recover_stale, rt.engine, 0)
                assert stop.result(timeout=3) == 1
            # Cancellation/recovery updates the artifact immediately, even while
            # the old worker remains inside its parser and has not returned.
            with rt.db() as db:
                run = db.get(ProcessingRun, queued["processing_id"])
                assert run.state == "failed" and run.error["code"] in (
                    "CANCELLED",
                    "WORKER_INTERRUPTED",
                )
                assert (
                    db.scalar(
                        select(func.count()).select_from(Chunk).where(Chunk.processing_id == run.id)
                    )
                    == 0
                )
            rerun = call(
                rt, "POST", f"/documents/{imported['document']['id']}/process", {}, admin, 202
            )
            assert (
                rerun["processing_id"] == queued["processing_id"]
                and rerun["job_id"] != queued["job_id"]
            )
        finally:
            resume.set()
        assert work.result(timeout=5)
    with rt.db() as db:
        assert db.get(ProcessingRun, queued["processing_id"]).state == "registered"
        assert db.get(Job, rerun["job_id"]).state == "queued"
        assert (
            db.scalar(
                select(func.count())
                .select_from(Chunk)
                .where(Chunk.processing_id == queued["processing_id"])
            )
            == 0
        )
    assert rt.work()
    with rt.db() as db:
        assert db.get(ProcessingRun, queued["processing_id"]).state == "ready"
        assert db.get(Job, rerun["job_id"]).state == "succeeded"
        assert db.get(Job, queued["job_id"]).state == (
            "cancelled" if interruption == "cancel" else "failed"
        )


@pytest.mark.parametrize("interruption", ["cancel", "recover"])
def test_release_stop_and_recovery_do_not_lock_provider_or_publish_late_vectors(
    runtime, interruption
):
    rt = runtime
    admin = rt.headers("admin@example.com")
    doc, active = corpus(rt)
    detail = call(rt, "GET", "/documents/" + doc["id"], headers=admin)
    processing_id = detail["processing_runs"][0]["id"]
    config = call(
        rt,
        "POST",
        "/configurations",
        {
            "kind": "retrieval",
            "name": "Independent interruption fixture",
            "values": {"embedding_revision": "interruption-fixture-" + uuid4().hex},
        },
        admin,
        201,
    )
    queued = call(
        rt,
        "POST",
        "/corpus/releases",
        {"processing_run_ids": [processing_id], "configuration_id": config["id"]},
        admin,
        202,
    )
    entered = Event()
    resume = Event()
    adapter = make_embedding(service.corpus_config(config["values"]))
    original = adapter.encode

    def blocked_encode(*args, **kwargs):
        entered.set()
        assert resume.wait(10), "Test failed to release its authored embedding provider"
        return original(*args, **kwargs)

    with (
        patch.object(adapter, "encode", side_effect=blocked_encode),
        patch("app.modules.knowledge.service.make_embedding", return_value=adapter),
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        work = pool.submit(rt.work)
        try:
            assert entered.wait(5), "Worker did not enter embedding"
            if interruption == "cancel":
                stop = pool.submit(
                    call, rt, "POST", "/jobs/" + queued["job_id"] + "/cancel", {}, admin
                )
                assert stop.result(timeout=3)["state"] == "cancelled"
            else:
                stop = pool.submit(recover_stale, rt.engine, 0)
                assert stop.result(timeout=3) == 1
            with rt.db() as db:
                release = db.get(CorpusRelease, queued["release_id"])
                assert release.state == "failed" and release.error["details"]["safe_next_action"]
                assert db.get(ActiveCorpus, 1).release_id == active["release_id"]
        finally:
            resume.set()
        assert work.result(timeout=5)
    with rt.db() as db:
        assert db.get(CorpusRelease, queued["release_id"]).state == "failed"
        assert (
            db.scalar(
                select(func.count())
                .select_from(ReleaseChunk)
                .where(ReleaseChunk.release_id == queued["release_id"])
            )
            == 0
        )
        assert db.get(ActiveCorpus, 1).release_id == active["release_id"]
    call(rt, "POST", "/corpus/releases/" + queued["release_id"] + "/activate", {}, admin, 409)
    rebuilt, job = build(rt, processing_id, config["id"])
    assert rebuilt["release_id"] != queued["release_id"] and job["state"] == "succeeded"
    with rt.db() as db:
        assert db.get(CorpusRelease, rebuilt["release_id"]).state == "validated"
        assert db.get(ActiveCorpus, 1).release_id == active["release_id"]
