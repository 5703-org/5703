"""Administrator corpus controls backed by real processing jobs."""

from contracts.http import Envelope

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from contracts.models import Contract
from app.api.v1.deps import require_roles, get_current_user
from app.core.config import get_settings, Settings
from app.core.exceptions import AppError
from app.core.responses import ok
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.knowledge.models import *
from app.modules.knowledge import service
from app.modules.answering.models import Job

router = APIRouter(tags=["knowledge"])


class ProcessInput(Contract):
    configuration: dict = Field(default_factory=dict)
    exclusions: dict[str, str] = Field(default_factory=dict)


class ReleaseInput(Contract):
    processing_run_ids: list[str] = Field(min_length=1, max_length=100)
    configuration_id: str | None = None
    name: str = Field(default="Corpus release", min_length=1, max_length=200)


class ConfigInput(Contract):
    kind: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    values: dict


def serialize(value):
    result = {c.name: getattr(value, c.name) for c in value.__table__.columns}
    return {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in result.items()}


def document_out(db, document, detail=False):
    versions = list(
        db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.created_at.desc())
        )
    )
    runs = list(
        db.scalars(
            select(ProcessingRun)
            .where(ProcessingRun.document_version_id.in_([v.id for v in versions]))
            .order_by(ProcessingRun.created_at.desc())
        )
    )
    data = {
        **serialize(document),
        "versions": [serialize(v) for v in versions],
        "processing_runs": [serialize(r) for r in runs],
        "latest_state": runs[0].state if runs else "registered",
    }
    if detail:
        data["units"] = [
            serialize(u)
            for u in db.scalars(
                select(SourceUnit)
                .where(SourceUnit.processing_id.in_([r.id for r in runs]))
                .order_by(SourceUnit.sequence)
            )
        ]
    return data


@router.get("/documents", response_model=Envelope[list[dict]])
def documents(db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    return ok(
        [
            document_out(db, d)
            for d in db.scalars(select(Document).order_by(Document.created_at.desc()))
        ]
    )


@router.post("/documents", status_code=201, response_model=Envelope[dict])
async def upload(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=500),
    edition: str = Form(""),
    source_url: str = Form(""),
    license: str = Form("Not specified"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
    settings: Settings = Depends(get_settings),
):
    data = await file.read(settings.max_upload_bytes + 1)
    doc, version, duplicate = service.ingest(
        db, settings, actor.id, file.filename, data, title, edition, source_url, license
    )
    db.commit()
    return ok(
        {"document": document_out(db, doc), "version": serialize(version), "duplicate": duplicate}
    )


@router.get("/documents/{document_id}", response_model=Envelope[dict])
def document(
    document_id: str, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))
):
    doc = db.get(Document, document_id)
    if not doc:
        raise AppError("NOT_FOUND")
    return ok(document_out(db, doc, True))


@router.post("/documents/{document_id}/process", status_code=202, response_model=Envelope[dict])
def process(
    document_id: str,
    body: ProcessInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    run, job = service.queue_process(db, document_id, actor.id, body.configuration, body.exclusions)
    db.commit()
    return ok({"processing_id": run.id, "job_id": job.id if job else None})


@router.get("/processing-runs/{processing_id}/quality", response_model=Envelope[dict])
def processing_quality(
    processing_id: str, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))
):
    return ok(service.processing_quality(db, processing_id))


@router.get("/processing-runs/{before_id}/diff/{after_id}", response_model=Envelope[dict])
def processing_diff(
    before_id: str,
    after_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    return ok(service.processing_diff(db, before_id, after_id))


def change_visibility(db, id, action):
    doc = db.get(Document, id)
    if not doc:
        raise AppError("NOT_FOUND")
    if action == "restore" and doc.revoked:
        raise AppError(
            "CONFLICT", detail="Revoked content requires a new authorized source version."
        )
    doc.active = action == "restore"
    if action == "revoke":
        doc.revoked = True
    doc.version += 1
    db.commit()
    return ok(document_out(db, doc))


@router.post("/documents/{document_id}/deactivate", response_model=Envelope[dict])
def deactivate(
    document_id: str, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))
):
    return change_visibility(db, document_id, "deactivate")


@router.post("/documents/{document_id}/restore", response_model=Envelope[dict])
def restore(
    document_id: str, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))
):
    return change_visibility(db, document_id, "restore")


@router.post("/documents/{document_id}/revoke", response_model=Envelope[dict])
def revoke(
    document_id: str, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))
):
    return change_visibility(db, document_id, "revoke")


@router.get("/corpus/releases", response_model=Envelope[list[dict]])
def releases(db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    return ok(
        [
            serialize(r)
            for r in db.scalars(select(CorpusRelease).order_by(CorpusRelease.created_at.desc()))
        ]
    )


@router.post("/corpus/releases", status_code=202, response_model=Envelope[dict])
def create_release(
    body: ReleaseInput, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))
):
    release, job = service.queue_release(
        db, actor.id, body.processing_run_ids, body.configuration_id, body.name
    )
    db.commit()
    return ok({"release_id": release.id, "job_id": job.id})


@router.post("/corpus/releases/{release_id}/activate", response_model=Envelope[dict])
@router.post("/corpus/releases/{release_id}/rollback", response_model=Envelope[dict])
def activate(
    release_id: str, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))
):
    release = service.activate(db, release_id)
    db.commit()
    return ok(serialize(release))


@router.get("/configurations", response_model=Envelope[list[dict]])
def configs(db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    return ok(
        [
            serialize(r)
            for r in db.scalars(select(Configuration).order_by(Configuration.created_at.desc()))
        ]
    )


@router.post("/configurations", status_code=201, response_model=Envelope[dict])
def create_config(
    body: ConfigInput, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))
):
    value = service.config_create(db, body.kind, body.name, body.values)
    db.commit()
    return ok(serialize(value))
