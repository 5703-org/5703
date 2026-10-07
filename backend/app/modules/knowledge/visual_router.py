"""Pinned original-page viewing and separate administrator visual-source review."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.responses import ok
from app.db.base import utcnow
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.knowledge.models import Document, DocumentVersion, VisualRegion, VisualRegionReview


router = APIRouter(tags=["source quality"])


class VisualReviewInput(BaseModel):
    decision: Literal["accepted", "rejected", "needs_more"]
    source_page_match: bool
    geometry_correct: bool
    native_text_correct: bool
    evidence: str = Field(min_length=12, max_length=2000)
    previous_review_id: str | None = None


def _owned_region(db: Session, actor: User, region_id: str, *, lock: bool = False):
    query = select(VisualRegion).where(VisualRegion.id == region_id)
    if lock:
        query = query.with_for_update()
    region = db.scalar(query)
    if region is None:
        raise AppError("NOT_FOUND")
    version = db.get(DocumentVersion, region.document_version_id)
    document = db.get(Document, version.document_id) if version else None
    owner = db.get(User, document.owner_id) if document else None
    if owner is None or owner.workspace_id != actor.workspace_id:
        raise AppError("NOT_FOUND")
    return region, document, version


def _latest_review(db: Session, region_id: str) -> VisualRegionReview | None:
    return db.scalar(
        select(VisualRegionReview)
        .where(VisualRegionReview.region_id == region_id)
        .order_by(VisualRegionReview.reviewed_at.desc(), VisualRegionReview.id.desc())
        .limit(1)
    )


def _public_record(db: Session, region: VisualRegion, document: Document, version: DocumentVersion):
    review = _latest_review(db, region.id)
    return {
        "id": region.id,
        "document_id": document.id,
        "document_version_id": version.id,
        "title": document.title,
        "source_sha256": version.raw_hash,
        "physical_pdf_page": region.physical_page,
        "kind": region.kind,
        "bbox_points": region.bbox,
        "native_text": region.native_text,
        "candidate_status": region.candidate_status,
        "details": region.details,
        "extractor_revision": region.extractor_revision,
        "catalog_sha256": region.catalog_sha256,
        "latest_review": {
            "id": review.id,
            "decision": review.decision,
            "checks": review.checks,
            "evidence": review.evidence,
            "reviewed_at": review.reviewed_at.isoformat(),
        }
        if review
        else None,
        "answer_evidence_eligible": False,
    }


@router.get("/admin/source-quality/visual-regions")
def list_visual_regions(
    document_id: str,
    page: int | None = Query(None, ge=1),
    kind: Literal["figure_image", "table_candidate", "formula_candidate"] | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    query = (
        select(VisualRegion, Document, DocumentVersion)
        .join(DocumentVersion, DocumentVersion.id == VisualRegion.document_version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .join(User, User.id == Document.owner_id)
        .where(Document.id == document_id, User.workspace_id == actor.workspace_id)
        .order_by(VisualRegion.physical_page, VisualRegion.id)
    )
    if page is not None:
        query = query.where(VisualRegion.physical_page == page)
    if kind is not None:
        query = query.where(VisualRegion.kind == kind)
    rows = db.execute(query.offset(offset).limit(limit + 1)).all()
    return ok(
        {
            "items": [_public_record(db, *row) for row in rows[:limit]],
            "next_offset": offset + limit if len(rows) > limit else None,
        }
    )


@router.get("/admin/source-quality/visual-regions/{region_id}")
def visual_region_detail(
    region_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    return ok(_public_record(db, *_owned_region(db, actor, region_id)))


@router.post("/admin/source-quality/visual-regions/{region_id}/reviews", status_code=201)
def review_visual_region(
    region_id: str,
    body: VisualReviewInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    region, document, version = _owned_region(db, actor, region_id, lock=True)
    latest = _latest_review(db, region_id)
    if (latest.id if latest else None) != body.previous_review_id:
        raise AppError(
            "CONFLICT", detail="The region review changed. Reload before recording a decision."
        )
    checks = {
        "source_page_match": body.source_page_match,
        "geometry_correct": body.geometry_correct,
        "native_text_correct": body.native_text_correct,
    }
    if body.decision == "accepted" and not all(checks.values()):
        raise AppError("VALIDATION_FAILED", detail="All source checks are required for acceptance.")
    db.add(
        VisualRegionReview(
            region_id=region_id,
            reviewer_id=actor.id,
            decision=body.decision,
            checks=checks,
            evidence=body.evidence,
            reviewed_at=utcnow(),
        )
    )
    db.commit()
    return ok(_public_record(db, region, document, version))


@router.get("/learning/library/{document_id}/original-page/{page}")
def original_pdf_page(
    document_id: str,
    page: int,
    document_version_id: str,
    source_sha256: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    if page < 1:
        raise AppError("VALIDATION_FAILED")
    # The reader's release projection enforces active, non-revoked, same-workspace
    # source membership before the original file is opened.
    from app.modules.learning_product.library import released_rows

    _, rows = released_rows(db, actor, document_id=document_id)
    versions = {row[3].id: row[3] for row in rows}
    if len(versions) != 1:
        raise AppError("EVIDENCE_UNAVAILABLE")
    version = next(iter(versions.values()))
    if version.id != document_version_id or version.raw_hash != source_sha256:
        raise AppError("EVIDENCE_UNAVAILABLE", detail="The requested textbook version has changed.")
    return _render_original(version, page, settings)


@router.get("/admin/source-quality/visual-regions/{region_id}/original-page")
def visual_region_original_page(
    region_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
    settings: Settings = Depends(get_settings),
):
    region, _, version = _owned_region(db, actor, region_id)
    return _render_original(version, region.physical_page, settings)


def _render_original(version: DocumentVersion, page: int, settings: Settings) -> Response:
    root = Path(settings.storage_root).resolve()
    source = (root / version.storage_path).resolve()
    if (
        not source.is_relative_to(root)
        or source.suffix.lower() != ".pdf"
        or not source.name.startswith(version.raw_hash)
        or not source.is_file()
    ):
        raise AppError("SOURCE_UNAVAILABLE")
    try:
        import pymupdf

        with pymupdf.open(source) as pdf:
            if page > len(pdf):
                raise AppError("NOT_FOUND")
            source_page = pdf[page - 1]
            page_rect = source_page.rect
            image = source_page.get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25), alpha=False)
            png = image.tobytes("png")
    except AppError:
        raise
    except (ImportError, RuntimeError, ValueError, OSError):
        raise AppError("SOURCE_UNAVAILABLE") from None
    return Response(
        png,
        media_type="image/png",
        headers={
            "Cache-Control": "private, no-store",
            "X-Source-SHA256": version.raw_hash,
            "X-Physical-PDF-Page": str(page),
            "X-PDF-Page-Width": str(page_rect.width),
            "X-PDF-Page-Height": str(page_rect.height),
        },
    )
