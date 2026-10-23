"""Disposable authored fixtures for version coexistence; no real human approvals."""

from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pymupdf
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.exceptions import AppError
from app.modules.identity.models import User, Workspace
from app.modules.knowledge.models import Document, DocumentVersion, VisualRegion
from app.modules.learning_product import visual_catalog_versions as service
from pipelines.visual_regions import _identity


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _count(db, model, bundle):
    query = select(func.count()).select_from(model)
    if model is service.VisualCatalogCandidate:
        query = query.join(
            service.VisualCatalogVersion, service.VisualCatalogVersion.id == model.catalog_id
        )
    elif model is service.VisualCatalogReview:
        query = query.join(
            service.VisualCatalogCandidate, service.VisualCatalogCandidate.id == model.candidate_id
        ).join(
            service.VisualCatalogVersion,
            service.VisualCatalogVersion.id == service.VisualCatalogCandidate.catalog_id,
        )
    return db.scalar(
        query.where(
            service.VisualCatalogVersion.document_version_id.in_(
                select(DocumentVersion.id).where(
                    DocumentVersion.raw_hash.in_(
                        [book["source_sha256"] for book in bundle["manifest"]["books"]]
                    )
                )
            )
        )
    )


@pytest.fixture
def bundle(runtime, tmp_path):
    directory = tmp_path / "catalogs"
    directory.mkdir()
    source_root = tmp_path / "originals"
    source_root.mkdir()
    manifest = {
        "schema": "official_native_table_review_sources_v1",
        "candidate_revision": "pymupdf_visual_regions_v3",
        "recovery_revision": "native_ruled_tables_v1",
        "pymupdf_version": pymupdf.VersionBind,
        "frozen_configuration": {"fixture": "authored software test"},
        "frozen_source_files": {},
        "freeze_sha256": "f" * 64,
        "human_ratings": 0,
        "semantic_approvals": 0,
        "answer_evidence_eligible_candidates": 0,
        "published_candidates": 0,
        "books": [],
        "region_count": 12,
        "table_count": 8,
        "candidate_rectangular_grids": 4,
        "retained_unresolved_tables": 4,
        "native_glyph_records_in_table_candidates": 0,
    }
    legacy_ids, v3_ids = [], []
    with runtime.db() as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        reviewer = User(
            email=f"reviewer-{uuid4().hex}@example.test",
            full_name="Authored independent reviewer fixture",
            hashed_password="not-a-login-password",
            role_id=admin.role_id,
            workspace_id=admin.workspace_id,
        )
        db.add(reviewer)
        db.flush()
        reviewer_id, admin_id = reviewer.id, admin.id
        for index in range(4):
            path = source_root / f"fixture-{index}.pdf"
            with pymupdf.open() as pdf:
                page = pdf.new_page()
                page.insert_text((72, 72), f"Authored software fixture {index}")
                pdf.save(path)
            source_sha = service.file_hash(path)
            book = f"Authored fixture {index}"
            legacy_sha = hashlib.sha256(f"legacy-fixture-{index}".encode()).hexdigest()
            doc = Document(title=book, owner_id=admin.id, license="Authored test material")
            db.add(doc)
            db.flush()
            version = DocumentVersion(
                document_id=doc.id,
                raw_hash=source_sha,
                media_type="application/pdf",
                size_bytes=path.stat().st_size,
                storage_path=path.name,
                original_filename=path.name,
            )
            db.add(version)
            db.flush()
            items = []
            for region_index, kind in enumerate(
                ("table_candidate", "table_candidate", "figure_image")
            ):
                old = {
                    "extractor_revision": "pymupdf_visual_regions_v2",
                    "book": book,
                    "source_sha256": source_sha,
                    "physical_pdf_page": 1,
                    "kind": kind,
                    "bbox_points": [10.0 + region_index, 10.0, 50.0, 50.0],
                    "native_text": "Authored fixture text",
                    "status": "needs_structure_review"
                    if kind == "table_candidate"
                    else "needs_visual_review",
                    "details": {"fixture": region_index},
                }
                old["region_id"] = _identity(old)
                db.add(
                    VisualRegion(
                        id=old["region_id"],
                        document_version_id=version.id,
                        physical_page=1,
                        kind=kind,
                        bbox=old["bbox_points"],
                        native_text=old["native_text"],
                        candidate_status=old["status"],
                        details=old["details"],
                        extractor_revision=old["extractor_revision"],
                        catalog_sha256=legacy_sha,
                    )
                )
                legacy_ids.append(old["region_id"])
                item = deepcopy(old)
                item["extractor_revision"] = "pymupdf_visual_regions_v3"
                item["details"] = {
                    "previous_region_id": old["region_id"],
                    "answer_evidence_eligible": False,
                    "rows": 1 if region_index == 0 else 0,
                    "columns": 1 if region_index == 0 else 0,
                    "cells": [["Fixture cell"]] if region_index == 0 else [],
                    "raw_native_glyphs": [{"char": "2", "baseline": 10.25, "fixture": True}],
                }
                item["region_id"] = _identity(item)
                items.append(item)
                v3_ids.append(item["region_id"])
            catalog = directory / f"book-{index}.jsonl.gz"
            with gzip.open(catalog, "wt", encoding="utf-8") as out:
                for item in items:
                    out.write(json.dumps(item) + "\n")
            manifest["books"].append(
                {
                    "book": book,
                    "source_sha256": source_sha,
                    "catalog_sha256": service.file_hash(catalog),
                    "previous_catalog_sha256": legacy_sha,
                    "physical_pages": 1,
                    "source_size_bytes": path.stat().st_size,
                    "catalog_file": catalog.name,
                    "all_old_region_lineages_preserved": 3,
                }
            )
        db.commit()
    _write_json(directory / "SOURCE_MANIFEST.json", manifest)
    return {
        "directory": directory,
        "storage_root": source_root,
        "manifest": manifest,
        "manifest_hash": service.file_hash(directory / "SOURCE_MANIFEST.json"),
        "admin_id": admin_id,
        "reviewer_id": reviewer_id,
        "legacy_ids": legacy_ids,
        "v3_ids": v3_ids,
    }


def _stage(db, bundle, actor_id=None):
    return service.stage_catalogs(
        db,
        db.get(User, actor_id or bundle["admin_id"]),
        bundle["directory"],
        expected_manifest_sha256=bundle["manifest_hash"],
        storage_root=bundle["storage_root"],
    )


def test_complete_import_coexists_and_repeated_import_is_exact(runtime, bundle):
    with runtime.db() as db:
        legacy_before = (
            db.execute(text("SELECT to_jsonb(v) FROM visual_regions v ORDER BY id")).scalars().all()
        )
        rows = _stage(db, bundle)
        db.commit()
        assert len(rows) == 4 and sum(row["added"] for row in rows) == 12
        assert {row["state"] for row in rows} == {"staged"}
        assert _count(db, service.VisualCatalogReview, bundle) == 0
        repeat = _stage(db, bundle)
        assert sum(row["added"] for row in repeat) == 0
        assert _count(db, service.VisualCatalogCandidate, bundle) == 12
        assert (
            legacy_before
            == db.execute(text("SELECT to_jsonb(v) FROM visual_regions v ORDER BY id"))
            .scalars()
            .all()
        )
        candidate = db.scalar(
            select(service.VisualCatalogCandidate).where(
                service.VisualCatalogCandidate.region_id == bundle["v3_ids"][0]
            )
        )
        assert candidate.raw_payload["details"]["raw_native_glyphs"][0]["baseline"] == 10.25
        assert candidate.payload_sha256 == service.payload_hash(candidate.raw_payload)
        assert (
            service.candidate_publication_state(
                db,
                db.get(User, bundle["admin_id"]),
                rows[0]["catalog_id"],
                candidate.region_id,
                storage_root=bundle["storage_root"],
            )["eligible_for_separate_publication"]
            is False
        )


def test_unapproved_activation_and_importer_self_review_are_denied(runtime, bundle):
    with runtime.db() as db:
        row = _stage(db, bundle)[0]
        admin = db.get(User, bundle["admin_id"])
        catalog = service.transition_catalog(
            db,
            admin,
            row["catalog_id"],
            expected_version=1,
            state="under_review",
            storage_root=bundle["storage_root"],
        )
        with pytest.raises(AppError) as error:
            service.transition_catalog(
                db,
                admin,
                catalog.id,
                expected_version=catalog.version,
                state="active",
                storage_root=bundle["storage_root"],
            )
        assert error.value.code == "VALIDATION_FAILED"
        with pytest.raises(AppError) as error:
            service.review_candidate(
                db,
                admin,
                catalog.id,
                bundle["v3_ids"][0],
                previous_review_id=None,
                decision="accepted",
                checks=dict.fromkeys(service.REVIEW_CHECKS, True),
                evidence="Authored independent source review fixture",
                storage_root=bundle["storage_root"],
            )
        assert error.value.code == "FORBIDDEN"


def test_authored_review_allows_only_accepted_candidate_and_never_publishes(runtime, bundle):
    with runtime.db() as db:
        row = _stage(db, bundle)[0]
        admin, reviewer = db.get(User, bundle["admin_id"]), db.get(User, bundle["reviewer_id"])
        catalog = service.transition_catalog(
            db,
            admin,
            row["catalog_id"],
            expected_version=1,
            state="under_review",
            storage_root=bundle["storage_root"],
        )
        review = service.review_candidate(
            db,
            reviewer,
            catalog.id,
            bundle["v3_ids"][0],
            previous_review_id=None,
            decision="accepted",
            checks=dict.fromkeys(service.REVIEW_CHECKS, True),
            evidence="Authored software fixture: independent source checks",
            storage_root=bundle["storage_root"],
        )
        service.transition_catalog(
            db,
            admin,
            catalog.id,
            expected_version=catalog.version,
            state="active",
            storage_root=bundle["storage_root"],
        )
        accepted = service.candidate_publication_state(
            db, admin, catalog.id, bundle["v3_ids"][0], storage_root=bundle["storage_root"]
        )
        assert (
            accepted["eligible_for_separate_publication"]
            and not accepted["answer_evidence_eligible"]
            and not accepted["published"]
        )
        pending = service.candidate_publication_state(
            db, admin, catalog.id, bundle["v3_ids"][1], storage_root=bundle["storage_root"]
        )
        assert not pending["eligible_for_separate_publication"]
        assert review.method == "independent_human"
        document = db.get(
            Document, db.get(DocumentVersion, catalog.document_version_id).document_id
        )
        document.revoked = True
        db.flush()
        assert not service.candidate_publication_state(
            db, admin, catalog.id, bundle["v3_ids"][0], storage_root=bundle["storage_root"]
        )["eligible_for_separate_publication"]
        with pytest.raises(AppError) as error:
            service.review_candidate(
                db,
                reviewer,
                catalog.id,
                bundle["v3_ids"][0],
                previous_review_id=review.id,
                decision="needs_more",
                checks=dict.fromkeys(service.REVIEW_CHECKS, False),
                evidence="Authored fixture remains withdrawn",
                storage_root=bundle["storage_root"],
            )
        assert error.value.code == "SOURCE_UNAVAILABLE"


def test_incomplete_geometry_review_and_stale_reviews_are_denied(runtime, bundle):
    with runtime.db() as db:
        row = _stage(db, bundle)[0]
        admin, reviewer = db.get(User, bundle["admin_id"]), db.get(User, bundle["reviewer_id"])
        catalog = service.transition_catalog(
            db,
            admin,
            row["catalog_id"],
            expected_version=1,
            state="under_review",
            storage_root=bundle["storage_root"],
        )
        with pytest.raises(AppError):
            service.review_candidate(
                db,
                reviewer,
                catalog.id,
                bundle["v3_ids"][1],
                previous_review_id=None,
                decision="accepted",
                checks=dict.fromkeys(service.REVIEW_CHECKS, True),
                evidence="Authored fixture cannot accept missing cells",
                storage_root=bundle["storage_root"],
            )
        review = service.review_candidate(
            db,
            reviewer,
            catalog.id,
            bundle["v3_ids"][0],
            previous_review_id=None,
            decision="needs_more",
            checks=dict.fromkeys(service.REVIEW_CHECKS, False),
            evidence="Authored fixture requires more source checking",
            storage_root=bundle["storage_root"],
        )
        with pytest.raises(AppError) as error:
            service.review_candidate(
                db,
                reviewer,
                catalog.id,
                bundle["v3_ids"][0],
                previous_review_id=None,
                decision="accepted",
                checks=dict.fromkeys(service.REVIEW_CHECKS, True),
                evidence="Authored stale review software fixture",
                storage_root=bundle["storage_root"],
            )
        assert error.value.code == "CONFLICT" and review.id


def test_import_missing_later_source_rolls_back_every_earlier_book(runtime, bundle):
    with runtime.db() as db:
        version = db.scalar(
            select(DocumentVersion).where(
                DocumentVersion.raw_hash == bundle["manifest"]["books"][-1]["source_sha256"]
            )
        )
        document = db.get(Document, version.document_id)
        document.revoked = True
        db.flush()
        with pytest.raises(AppError):
            _stage(db, bundle)
        assert _count(db, service.VisualCatalogVersion, bundle) == 0
        assert _count(db, service.VisualCatalogCandidate, bundle) == 0


def test_cross_workspace_and_student_import_cannot_read_or_stage(runtime, bundle):
    with runtime.db() as db:
        student = db.scalar(select(User).where(User.email == "student@example.com"))
        with pytest.raises(AppError) as error:
            _stage(db, bundle, student.id)
        assert error.value.code == "FORBIDDEN"
        workspace = Workspace(name="Isolated authored fixture workspace", slug=uuid4().hex)
        db.add(workspace)
        db.flush()
        foreign = User(
            email=f"foreign-{uuid4().hex}@example.test",
            full_name="Cross workspace fixture",
            hashed_password="not-a-login-password",
            role_id=db.get(User, bundle["admin_id"]).role_id,
            workspace_id=workspace.id,
        )
        db.add(foreign)
        db.flush()
        with pytest.raises(AppError) as error:
            _stage(db, bundle, foreign.id)
        assert error.value.code == "NOT_FOUND"
        assert _count(db, service.VisualCatalogVersion, bundle) == 0


@pytest.mark.parametrize(
    "table,assignment",
    [
        ("visual_catalog_candidates", "candidate_status='accepted'"),
        ("visual_catalog_versions", "catalog_sha256='modified'"),
        ("visual_catalog_candidates", "raw_payload='{}'::json"),
    ],
)
def test_database_immutable_guards_reject_raw_sql_updates(runtime, bundle, table, assignment):
    with runtime.db() as db:
        rows = _stage(db, bundle)
        db.commit()
        assert rows
        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.execute(text(f"UPDATE {table} SET {assignment}"))


def test_manifest_catalog_and_original_hash_changes_are_rejected(runtime, bundle):
    path = bundle["directory"] / "SOURCE_MANIFEST.json"
    old = path.read_bytes()
    path.write_bytes(old + b" ")
    with runtime.db() as db, pytest.raises(AppError):
        _stage(db, bundle)
    path.write_bytes(old)
    first_pdf = bundle["storage_root"] / "fixture-0.pdf"
    first_pdf.write_bytes(first_pdf.read_bytes() + b"changed")
    with runtime.db() as db, pytest.raises(AppError) as error:
        _stage(db, bundle)
    assert error.value.code == "SOURCE_UNAVAILABLE"


def test_idempotent_metadata_conflict_is_not_silently_overwritten(runtime, bundle):
    with runtime.db() as db:
        _stage(db, bundle)
        db.commit()
        manifest = deepcopy(bundle["manifest"])
        manifest["frozen_configuration"]["fixture"] = "changed metadata"
        _write_json(bundle["directory"] / "SOURCE_MANIFEST.json", manifest)
        bundle["manifest_hash"] = service.file_hash(bundle["directory"] / "SOURCE_MANIFEST.json")
        with pytest.raises(AppError) as error:
            _stage(db, bundle)
        assert error.value.code == "CONFLICT"
        assert _count(db, service.VisualCatalogCandidate, bundle) == 12


def test_database_state_guard_rejects_unreviewed_activation(runtime, bundle):
    with runtime.db() as db:
        rows = _stage(db, bundle)
        db.commit()
        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.execute(
                    text(
                        "UPDATE visual_catalog_versions SET state='active',version=version+1 WHERE id=:id"
                    ),
                    {"id": rows[0]["catalog_id"]},
                )


def test_database_review_guard_rejects_importer_approval(runtime, bundle):
    with runtime.db() as db:
        rows = _stage(db, bundle)
        admin = db.get(User, bundle["admin_id"])
        catalog = service.transition_catalog(
            db,
            admin,
            rows[0]["catalog_id"],
            expected_version=1,
            state="under_review",
            storage_root=bundle["storage_root"],
        )
        candidate = db.scalar(
            select(service.VisualCatalogCandidate).where(
                service.VisualCatalogCandidate.catalog_id == catalog.id
            )
        )
        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.add(
                    service.VisualCatalogReview(
                        candidate_id=candidate.id,
                        reviewer_id=admin.id,
                        previous_review_id=None,
                        decision="accepted",
                        method="independent_human",
                        checks=dict.fromkeys(service.REVIEW_CHECKS, True),
                        evidence="Rejected authored self approval software fixture",
                        payload_sha256=candidate.payload_sha256,
                    )
                )
                db.flush()
        assert _count(db, service.VisualCatalogReview, bundle) == 0


def test_populated_downgrade_guard_keeps_catalog_history(runtime, bundle):
    import importlib.util
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    path = (
        Path(__file__).resolve().parents[2]
        / "backend/alembic/versions/f9a05c2187de_versioned_visual_catalogs.py"
    )
    spec = importlib.util.spec_from_file_location("owned_visual_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with runtime.db() as db:
        _stage(db, bundle)
        db.commit()
        with Operations.context(MigrationContext.configure(db.connection())):
            with pytest.raises(RuntimeError, match="Preserve all visual catalog"):
                migration.downgrade()
        assert _count(db, service.VisualCatalogCandidate, bundle) == 12


def test_concurrent_database_reviews_with_same_previous_id_have_one_winner(runtime, bundle):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    with runtime.db() as db:
        rows = _stage(db, bundle)
        admin = db.get(User, bundle["admin_id"])
        catalog = service.transition_catalog(
            db,
            admin,
            rows[0]["catalog_id"],
            expected_version=1,
            state="under_review",
            storage_root=bundle["storage_root"],
        )
        candidate = db.scalar(
            select(service.VisualCatalogCandidate).where(
                service.VisualCatalogCandidate.catalog_id == catalog.id
            )
        )
        candidate_id, candidate_hash = candidate.id, candidate.payload_sha256
        db.commit()
    barrier = Barrier(2)

    def submit():
        with runtime.db() as db:
            db.execute(text("SET LOCAL statement_timeout='5s'"))
            barrier.wait(timeout=5)
            db.add(
                service.VisualCatalogReview(
                    candidate_id=candidate_id,
                    reviewer_id=bundle["reviewer_id"],
                    previous_review_id=None,
                    decision="needs_more",
                    method="independent_human",
                    checks=dict.fromkeys(service.REVIEW_CHECKS, False),
                    evidence="Authored concurrent review software fixture",
                    payload_sha256=candidate_hash,
                )
            )
            try:
                db.commit()
                return "saved"
            except DBAPIError as error:
                db.rollback()
                assert "compare and swap failed" in str(error.orig)
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(submit) for _ in range(2)]
        assert sorted(future.result(timeout=8) for future in futures) == ["conflict", "saved"]
    with runtime.db() as db:
        assert _count(db, service.VisualCatalogReview, bundle) == 1


def _v4_bundle(bundle):
    """Authored consumer fixtures; no official-source review is asserted."""
    original = bundle["directory"]
    directory = original / "v4-successor"
    directory.mkdir()
    result = dict(bundle, directory=directory)
    manifest = deepcopy(bundle["manifest"])
    manifest.update(
        schema="official_native_table_review_sources_v2",
        candidate_revision="pymupdf_visual_regions_v4",
        recovery_revision="native_ruled_tables_v2",
        inline_table_reference_count=0,
        linked_table_reference_count=0,
    )
    ids = []
    for book in manifest["books"]:
        catalog = original / book["catalog_file"]
        parent = directory / ("parent-" + catalog.name)
        parent.write_bytes(catalog.read_bytes())
        book["parent_candidate_catalog_file"] = parent.name
        book["parent_candidate_catalog_sha256"] = service.file_hash(parent)
        with gzip.open(catalog, "rt", encoding="utf-8") as stream:
            items = [json.loads(line) for line in stream]
        for item in items:
            parent_id = item["region_id"]
            item["extractor_revision"] = "pymupdf_visual_regions_v4"
            item["details"].update(
                previous_candidate_region_id=parent_id,
                previous_candidate_extractor_revision="pymupdf_visual_regions_v3",
                page_size_points=[595.0, 842.0],
            )
            if item["kind"] == "table_candidate":
                item["details"]["record_role"] = "table_body_candidate"
            item["region_id"] = _identity(item)
            ids.append(item["region_id"])
        with gzip.open(directory / catalog.name, "wt", encoding="utf-8") as stream:
            for item in items:
                stream.write(json.dumps(item) + "\n")
        book["catalog_sha256"] = service.file_hash(directory / catalog.name)
    result.update(manifest=manifest, v3_ids=ids)
    _write_json(directory / "SOURCE_MANIFEST.json", manifest)
    result["manifest_hash"] = service.file_hash(directory / "SOURCE_MANIFEST.json")
    return result


def _change_v4_first_candidate(bundle, modify):
    book = bundle["manifest"]["books"][0]
    path = bundle["directory"] / book["catalog_file"]
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        items = [json.loads(line) for line in stream]
    modify(items[0])
    items[0]["region_id"] = _identity(items[0])
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for item in items:
            stream.write(json.dumps(item) + "\n")
    book["catalog_sha256"] = service.file_hash(path)
    _write_json(bundle["directory"] / "SOURCE_MANIFEST.json", bundle["manifest"])
    bundle["manifest_hash"] = service.file_hash(bundle["directory"] / "SOURCE_MANIFEST.json")


def test_v4_staging_keeps_v3_and_v2_records_and_unapproved_counts(runtime, bundle):
    with runtime.db() as db:
        old_rows = _stage(db, bundle)
        db.commit()
        v4 = _v4_bundle(bundle)
        manifest, books = service.load_bundle(
            v4["directory"], expected_manifest_sha256=v4["manifest_hash"]
        )
        assert manifest["inline_table_reference_count"] == 0
        assert len(books) == 4
        rows = _stage(db, v4)
        db.commit()
        assert len(rows) == 4 and sum(row["added"] for row in rows) == 12
        assert _count(db, service.VisualCatalogVersion, bundle) == 8
        assert _count(db, service.VisualCatalogCandidate, bundle) == 24
        assert _count(db, service.VisualCatalogReview, bundle) == 0
        assert {row["catalog_id"] for row in rows}.isdisjoint(row["catalog_id"] for row in old_rows)
        assert sum(row["added"] for row in _stage(db, v4)) == 0
        for row in rows:
            catalog = db.get(service.VisualCatalogVersion, row["catalog_id"])
            assert catalog.counts["rectangular_tables"] == 1
            assert catalog.counts["unresolved_tables"] == 1
            assert catalog.counts["inline_table_references"] == 0
            assert catalog.state == "staged"
        candidate = service.candidate_publication_state(
            db,
            db.get(User, bundle["admin_id"]),
            rows[0]["catalog_id"],
            v4["v3_ids"][0],
            storage_root=v4["storage_root"],
        )
        assert not candidate["answer_evidence_eligible"]
        assert not candidate["published"]
        assert not candidate["eligible_for_separate_publication"]


def test_v4_rehashed_forged_parent_is_rejected_before_staging(runtime, bundle):
    v4 = _v4_bundle(bundle)
    _change_v4_first_candidate(
        v4, lambda item: item["details"].update(previous_candidate_region_id="e" * 64)
    )
    with runtime.db() as db:
        with pytest.raises(AppError) as error:
            _stage(db, v4)
        assert error.value.code == "VALIDATION_FAILED"
        assert _count(db, service.VisualCatalogVersion, v4) == 0
        assert _count(db, service.VisualCatalogCandidate, v4) == 0


def test_v4_declared_dimensions_must_match_actual_pdf_before_staging(runtime, bundle):
    v4 = _v4_bundle(bundle)
    _change_v4_first_candidate(
        v4, lambda item: item["details"].update(page_size_points=[600.0, 850.0])
    )
    service.load_bundle(v4["directory"], expected_manifest_sha256=v4["manifest_hash"])
    with runtime.db() as db:
        with pytest.raises(AppError) as error:
            _stage(db, v4)
        assert error.value.code == "VALIDATION_FAILED"
        assert _count(db, service.VisualCatalogVersion, v4) == 0
        assert _count(db, service.VisualCatalogCandidate, v4) == 0
