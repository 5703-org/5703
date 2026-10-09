"""Human source-review decisions stay separate from immutable candidates."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db import models as all_models  # noqa: F401
from app.db.base import Base
from app.modules.identity.models import Role, User, Workspace
from app.modules.knowledge.models import Document, DocumentVersion, VisualRegion, VisualRegionReview
from app.modules.knowledge.visual_router import (
    VisualReviewInput,
    list_visual_regions,
    review_visual_region,
    visual_region_detail,
)


def test_review_is_workspace_scoped_and_never_promotes_candidate_to_answer_evidence(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'visual.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        role = Role(name="admin")
        own = Workspace(name="Own", slug="own")
        other = Workspace(name="Other", slug="other")
        db.add_all([role, own, other])
        db.flush()
        owner = User(
            email="source@example.org",
            full_name="Source",
            hashed_password="unused",
            role_id=role.id,
            workspace_id=own.id,
        )
        outsider = User(
            email="other@example.org",
            full_name="Other",
            hashed_password="unused",
            role_id=role.id,
            workspace_id=other.id,
        )
        db.add_all([owner, outsider])
        db.flush()
        document = Document(
            title="Source book", edition="2e", owner_id=owner.id, source_url="https://openstax.org"
        )
        db.add(document)
        db.flush()
        version = DocumentVersion(
            document_id=document.id,
            raw_hash="a" * 64,
            media_type="application/pdf",
            size_bytes=1234,
            storage_path="originals/source.pdf",
            original_filename="source.pdf",
        )
        db.add(version)
        db.flush()
        region = VisualRegion(
            id="b" * 64,
            document_version_id=version.id,
            physical_page=12,
            kind="formula_candidate",
            bbox=[72, 80, 200, 90],
            native_text="E = mc2",
            candidate_status="needs_formula_review",
            details={"limitation": "symbol layout uncertain"},
            extractor_revision="pymupdf_visual_regions_v2",
            catalog_sha256="c" * 64,
        )
        db.add(region)
        db.commit()

        with pytest.raises(AppError, match="NOT_FOUND"):
            visual_region_detail(region.id, db=db, actor=outsider)
        own_list = list_visual_regions(
            document.id, page=12, kind=None, offset=0, limit=30, db=db, actor=owner
        )["data"]
        assert len(own_list["items"]) == 1
        assert own_list["items"][0]["answer_evidence_eligible"] is False
        with pytest.raises(AppError) as validation:
            review_visual_region(
                region.id,
                VisualReviewInput(
                    decision="accepted",
                    source_page_match=True,
                    geometry_correct=False,
                    native_text_correct=True,
                    evidence="This page was checked against the local source.",
                ),
                db=db,
                actor=owner,
            )
        assert validation.value.code == "VALIDATION_FAILED"
        result = review_visual_region(
            region.id,
            VisualReviewInput(
                decision="accepted",
                source_page_match=True,
                geometry_correct=True,
                native_text_correct=True,
                evidence="The exact PDF page and native line were inspected.",
            ),
            db=db,
            actor=owner,
        )["data"]
        assert result["latest_review"]["decision"] == "accepted"
        assert result["answer_evidence_eligible"] is False
        assert db.get(VisualRegion, region.id).native_text == "E = mc2"
        assert db.query(VisualRegionReview).count() == 1
        with pytest.raises(AppError) as conflict:
            review_visual_region(
                region.id,
                VisualReviewInput(
                    decision="rejected",
                    source_page_match=False,
                    geometry_correct=False,
                    native_text_correct=False,
                    evidence="A conflicting duplicate review was attempted.",
                    previous_review_id=None,
                ),
                db=db,
                actor=owner,
            )
        assert conflict.value.code == "CONFLICT"
    engine.dispose()
