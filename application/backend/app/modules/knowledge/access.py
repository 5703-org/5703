"""Authorize source objects in the verified actor's workspace before exposing them."""

from sqlalchemy import select
from app.core.exceptions import AppError
from app.modules.identity.models import User
from app.modules.knowledge.models import Document, DocumentVersion, ProcessingRun


def _workspace(db, actor_id):
    workspace_id = db.scalar(select(User.workspace_id).where(User.id == actor_id))
    if workspace_id is None:
        raise AppError("NOT_FOUND")
    return workspace_id


def workspace_document(db, actor_id, document_id, *, lock=False):
    query = (
        select(Document)
        .join(User, User.id == Document.owner_id)
        .where(Document.id == document_id, User.workspace_id == _workspace(db, actor_id))
    )
    if lock:
        query = query.with_for_update(of=Document)
    document = db.scalar(query)
    if document is None:
        raise AppError("NOT_FOUND")
    return document


def workspace_processing(db, actor_id, processing_id):
    run = db.scalar(
        select(ProcessingRun)
        .join(DocumentVersion, DocumentVersion.id == ProcessingRun.document_version_id)
        .join(Document, Document.id == DocumentVersion.document_id)
        .join(User, User.id == Document.owner_id)
        .where(ProcessingRun.id == processing_id, User.workspace_id == _workspace(db, actor_id))
    )
    if run is None:
        raise AppError("NOT_FOUND")
    return run
