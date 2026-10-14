"""Local administrator inspection of unpublished drafts with live source checks."""

from datetime import datetime
import hashlib
from typing import Literal

from pydantic import Field
from sqlalchemy import select

from contracts.models import Contract
from generation.adapters import redact
from app.core.exceptions import AppError
from app.modules.answering.diagnostics import scoped_requests
from app.modules.answering.models import AnswerRequest
from app.modules.identity.models import User
from app.modules.knowledge.models import Chunk, Document, ReleaseChunk
from app.modules.learning_state.models import PrivateAnswerDraft


class DraftReviewSource(Contract):
    evidence_id: str
    chunk_id: str
    title: str
    section: str
    pages: list[int]
    text_hash: str
    excerpts: list[str]


class DraftReviewItem(Contract):
    id: str
    revision: int | None = None
    recorded_at: datetime
    answer_text: str
    truncated: bool
    source_status: Literal["validated", "incomplete_binding", "source_unavailable", "no_sources"]
    sources: list[DraftReviewSource] = Field(default_factory=list)
    withheld_source_count: int = Field(ge=0)


class DraftReviewPage(Contract):
    request_id: str
    items: list[DraftReviewItem]
    truncated: bool
    scope: Literal["local_admin_unpublished_drafts_v1"] = "local_admin_unpublished_drafts_v1"


def _bindings(req: AnswerRequest) -> dict[str, str]:
    selection = req.trace.get("evidence_selection", {})
    if not isinstance(selection, dict):
        return {}
    ids = selection.get("submitted_evidence_ids")
    chunks = selection.get("submitted_chunk_ids")
    if (
        not isinstance(ids, list)
        or not isinstance(chunks, list)
        or len(ids) != len(chunks)
        or any(not isinstance(v, str) for v in ids + chunks)
        or len(set(ids)) != len(ids)
    ):
        return {}
    return dict(zip(ids, chunks, strict=True))


def _source(db, actor, req, view, bindings):
    if not isinstance(view, dict) or not isinstance(view.get("evidence_id"), str):
        return None
    evidence_id = view["evidence_id"]
    chunk_id = bindings.get(evidence_id)
    if not chunk_id or not req.release_id:
        return None
    chunk = db.get(Chunk, chunk_id)
    if not chunk or not db.get(ReleaseChunk, (req.release_id, chunk_id)):
        return None
    document = db.get(Document, chunk.document_id)
    owner = db.get(User, document.owner_id) if document else None
    if (
        not document
        or not document.active
        or document.revoked
        or not owner
        or owner.workspace_id != actor.workspace_id
        or hashlib.sha256(chunk.text.encode()).hexdigest() != chunk.text_hash
    ):
        return None
    segments = view.get("segments")
    if not isinstance(segments, list) or not segments or len(segments) > 30:
        return None
    excerpts = []
    for segment in segments:
        text = segment.get("text") if isinstance(segment, dict) else None
        if not isinstance(text, str) or not text.strip() or text not in chunk.text:
            return None
        # Separate excerpt boundaries survive the projection; no invented continuity.
        excerpts.append(redact(text, limit=12000))
    return DraftReviewSource(
        evidence_id=evidence_id,
        chunk_id=chunk.id,
        title=redact(document.title, limit=500),
        section=redact(chunk.section, limit=500),
        pages=[p for p in chunk.pages if type(p) is int and p > 0],
        text_hash=chunk.text_hash,
        excerpts=excerpts,
    )


def review_drafts(db, actor, request_id):
    """Read saved text locally. Inspection cannot publish or override a checker."""
    if actor.role.name != "admin":
        raise AppError("FORBIDDEN")
    req = db.scalar(scoped_requests(actor).where(AnswerRequest.id == request_id))
    if not req:
        raise AppError("NOT_FOUND")
    if req.state in {"queued", "running", "retrieving", "generating", "checking"}:
        raise AppError("CONFLICT")
    rows = list(
        db.scalars(
            select(PrivateAnswerDraft)
            .where(
                PrivateAnswerDraft.request_id == req.id,
                PrivateAnswerDraft.phase == "generated_draft",
            )
            .order_by(PrivateAnswerDraft.created_at, PrivateAnswerDraft.id)
            .limit(51)
        )
    )
    bindings = _bindings(req)
    items = []
    for row in rows[:50]:
        payload = row.payload if isinstance(row.payload, dict) else {}
        response = payload.get("response", {})
        answer_text = response.get("answer_text", "") if isinstance(response, dict) else ""
        if not isinstance(answer_text, str):
            answer_text = ""
        projection = payload.get("projection", {})
        views = projection.get("citation_views", []) if isinstance(projection, dict) else []
        views = views if isinstance(views, list) else []
        sources = [s for v in views[:30] if (s := _source(db, actor, req, v, bindings))]
        withheld = len(views) - len(sources)
        status = (
            "no_sources"
            if not views
            else "incomplete_binding"
            if not bindings
            else "source_unavailable"
            if withheld
            else "validated"
        )
        items.append(
            DraftReviewItem(
                id=row.id,
                revision=payload.get("revision") if type(payload.get("revision")) is int else None,
                recorded_at=row.created_at,
                answer_text=redact(answer_text, limit=12000),
                truncated=len(answer_text) > 12000,
                source_status=status,
                sources=sources,
                withheld_source_count=withheld,
            )
        )
    return DraftReviewPage(request_id=req.id, items=items, truncated=len(rows) > 50)
