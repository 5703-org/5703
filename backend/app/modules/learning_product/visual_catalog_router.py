"""Administrator-only catalog coexistence, candidate inspection and review."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from contracts.http import Envelope
from contracts.visual_catalogs import (
    CatalogCandidateDetailOut,
    CatalogCandidatePageOut,
    CatalogImportInput,
    CatalogImportOut,
    CatalogReviewInput,
    CatalogReviewResultOut,
    CatalogSummaryOut,
    CatalogTransitionInput,
    CatalogVersionPageOut,
)
from app.api.v1.deps import require_roles
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.responses import ok
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.knowledge.models import Document, DocumentVersion
from . import visual_catalog_versions as service

router = APIRouter(
    prefix="/admin/source-quality/catalog-versions", tags=["visual catalog versions"]
)


def _bundle_directory(settings: Settings, name: str) -> Path:
    """Resolve server-owned staging files; callers cannot nominate filesystem paths."""
    root = Path(settings.visual_catalog_staging_root).resolve()
    candidate = root / name
    directory = candidate.resolve()
    manifest = directory / "SOURCE_MANIFEST.json"
    if (
        candidate.is_symlink()
        or candidate.is_junction()
        or not directory.is_relative_to(root)
        or not directory.is_dir()
        or manifest.is_symlink()
        or not manifest.resolve().is_relative_to(directory)
        or not manifest.is_file()
        or not 1 <= manifest.stat().st_size <= 1_048_576
    ):
        raise AppError("VALIDATION_FAILED", detail="The staged bundle is unavailable or unsafe.")
    return directory


def _summary(db: Session, actor: User, catalog_id: str) -> dict:
    row = service.owned_catalog(db, actor, catalog_id, visible=False)
    version = db.get(DocumentVersion, row.document_version_id)
    document = db.get(Document, version.document_id)
    return {
        **service.catalog_summary(db, actor, catalog_id),
        "document_id": document.id,
        "document_title": document.title,
        "book": row.artifact_manifest["book"]["book"],
        "importer_id": row.importer_id,
        "source_active": document.active and not document.revoked,
    }


@router.get("", response_model=Envelope[CatalogVersionPageOut])
def versions(
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    rows = list(
        db.scalars(
            select(service.VisualCatalogVersion)
            .where(service.VisualCatalogVersion.workspace_id == actor.workspace_id)
            .order_by(
                service.VisualCatalogVersion.created_at.desc(), service.VisualCatalogVersion.id
            )
            .offset(offset)
            .limit(limit + 1)
        )
    )
    return ok(
        {
            "items": [_summary(db, actor, row.id) for row in rows[:limit]],
            "next_offset": offset + limit if len(rows) > limit else None,
        }
    )


@router.post("/imports", response_model=Envelope[CatalogImportOut])
def import_bundle(
    body: CatalogImportInput,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_roles("admin")),
):
    try:
        staged = service.stage_catalogs(
            db,
            actor,
            _bundle_directory(settings, body.bundle_name),
            expected_manifest_sha256=body.expected_manifest_sha256,
            storage_root=Path(settings.storage_root),
        )
        result = {
            "items": [
                {**_summary(db, actor, row["catalog_id"]), "added": row["added"]} for row in staged
            ],
            "added_candidates": sum(row["added"] for row in staged),
        }
        db.commit()
    except IntegrityError as exc:
        raise AppError(
            "CONFLICT", detail="The immutable catalog import conflicts with existing data."
        ) from exc
    except (OSError, ValueError, KeyError, TypeError, EOFError) as exc:
        raise AppError(
            "VALIDATION_FAILED", detail="The staged bundle could not be verified."
        ) from exc
    return ok(result)


@router.get("/{catalog_id}", response_model=Envelope[CatalogSummaryOut])
def version_detail(
    catalog_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    return ok(_summary(db, actor, catalog_id))


@router.get("/{catalog_id}/candidates", response_model=Envelope[CatalogCandidatePageOut])
def candidates(
    catalog_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    service.owned_catalog(db, actor, catalog_id)
    items = service.list_candidates(db, actor, catalog_id, offset=offset, limit=limit)
    following = db.scalar(
        select(service.VisualCatalogCandidate.id)
        .where(service.VisualCatalogCandidate.catalog_id == catalog_id)
        .order_by(
            service.VisualCatalogCandidate.physical_page, service.VisualCatalogCandidate.region_id
        )
        .offset(offset + limit)
        .limit(1)
    )
    return ok({"items": items, "next_offset": offset + limit if following else None})


@router.get(
    "/{catalog_id}/candidates/{region_id}", response_model=Envelope[CatalogCandidateDetailOut]
)
def candidate_detail(
    catalog_id: str,
    region_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    service.owned_catalog(db, actor, catalog_id)
    result = service.candidate_detail(db, actor, catalog_id, region_id)
    candidate = db.scalar(
        select(service.VisualCatalogCandidate).where(
            service.VisualCatalogCandidate.catalog_id == catalog_id,
            service.VisualCatalogCandidate.region_id == region_id,
        )
    )
    latest = db.scalar(
        select(service.VisualCatalogReview)
        .where(service.VisualCatalogReview.candidate_id == candidate.id)
        .order_by(
            service.VisualCatalogReview.reviewed_at.desc(), service.VisualCatalogReview.id.desc()
        )
        .limit(1)
    )
    result["latest_review"] = (
        {
            "id": latest.id,
            "previous_review_id": latest.previous_review_id,
            "reviewer_id": latest.reviewer_id,
            "decision": latest.decision,
            "method": latest.method,
            "checks": latest.checks,
            "evidence": latest.evidence,
            "payload_sha256": latest.payload_sha256,
            "reviewed_at": latest.reviewed_at.isoformat(),
        }
        if latest
        else None
    )
    return ok(result)


@router.post("/{catalog_id}/state", response_model=Envelope[CatalogSummaryOut])
def transition(
    catalog_id: str,
    body: CatalogTransitionInput,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_roles("admin")),
):
    service.transition_catalog(
        db,
        actor,
        catalog_id,
        expected_version=body.expected_version,
        state=body.state,
        storage_root=Path(settings.storage_root),
    )
    result = _summary(db, actor, catalog_id)
    db.commit()
    return ok(result)


@router.post(
    "/{catalog_id}/candidates/{region_id}/reviews", response_model=Envelope[CatalogReviewResultOut]
)
def review(
    catalog_id: str,
    region_id: str,
    body: CatalogReviewInput,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: User = Depends(require_roles("admin")),
):
    row = service.review_candidate(
        db,
        actor,
        catalog_id,
        region_id,
        previous_review_id=body.previous_review_id,
        decision=body.decision,
        checks=body.checks.model_dump(),
        evidence=body.evidence,
        storage_root=Path(settings.storage_root),
    )
    result = {"review_id": row.id, "catalog_version": _summary(db, actor, catalog_id)}
    db.commit()
    return ok(result)
