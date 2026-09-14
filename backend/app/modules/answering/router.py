"""Learner answer, evidence, job and feedback routes."""

from contracts.http import Envelope
from contracts.models import JobReceipt, MessagePage, JobOut, AnswerOut, EvidenceSnapshot
from contracts.http import FeedbackOut, SummaryOut
from fastapi import APIRouter, Depends, Header, Query
from typing import Literal
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from contracts.models import ChatMessageCreate, FeedbackInput, Contract
from app.api.v1.deps import get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.responses import ok
from app.db.session import get_db
from app.modules.identity.models import User
from app.modules.answering import service
from app.modules.answering.models import *
from app.modules.knowledge.models import Document
from app.modules.knowledge.router import serialize
from conversation.summary import summarize
from app.modules.answering import diagnostics

router = APIRouter(tags=["answering"])


@router.get("/admin/failures", response_model=Envelope[diagnostics.FailurePage])
def failures(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    state: diagnostics.FailureFilter | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    return ok(diagnostics.list_failures(db, actor, limit, offset, state).model_dump())


@router.get("/admin/failures/{request_id}", response_model=Envelope[diagnostics.FailureDetail])
def failure_details(
    request_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    return ok(diagnostics.failure_detail(db, actor, request_id).model_dump())


@router.post(
    "/sessions/{session_id}/messages", status_code=202, response_model=Envelope[JobReceipt]
)
def send_message(
    session_id: str,
    body: ChatMessageCreate,
    idempotency_key: str = Header(...),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    return ok(service.submit_chat(db, settings, actor, session_id, body, idempotency_key))


@router.get("/sessions/{session_id}/messages", response_model=Envelope[MessagePage])
def messages(
    session_id: str,
    after_sequence: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    service.owned_session(db, session_id, actor)
    return ok(service.messages_page(db, session_id, after_sequence, limit))


@router.get("/jobs/{job_id}", response_model=Envelope[JobOut])
def job(job_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(service.job_out(db, service.job_owned(db, job_id, actor)))


@router.post("/jobs/{job_id}/cancel", response_model=Envelope[JobOut])
def cancel(job_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    row = service.job_owned(db, job_id, actor)
    db.refresh(row, with_for_update=True)
    service.cancel_job(db, row)
    db.commit()
    return ok(service.job_out(db, row))


@router.post(
    "/answer-requests/{request_id}/retry", status_code=202, response_model=Envelope[JobReceipt]
)
def retry(
    request_id: str,
    idempotency_key: str = Header(...),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return ok(service.retry(db, actor, request_id, idempotency_key))


@router.post(
    "/answers/{answer_id}/regenerate", status_code=202, response_model=Envelope[JobReceipt]
)
def regenerate(
    answer_id: str,
    idempotency_key: str = Header(...),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return ok(service.regenerate(db, actor, answer_id, idempotency_key))


def owned_answer(db, id, actor):
    answer = db.get(Answer, id)
    if not answer:
        raise AppError("NOT_FOUND")
    service.request_owned(db, answer.request_id, actor)
    return answer


@router.get("/answers/{answer_id}", response_model=Envelope[AnswerOut])
def answer(answer_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return ok(service.answer_out(db, owned_answer(db, answer_id, actor)))


@router.get(
    "/answers/{answer_id}/evidence/{evidence_id}", response_model=Envelope[EvidenceSnapshot]
)
def evidence(
    answer_id: str,
    evidence_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    owned_answer(db, answer_id, actor)
    ev = db.scalar(
        select(Evidence).where(Evidence.answer_id == answer_id, Evidence.evidence_id == evidence_id)
    )
    if not ev:
        raise AppError("NOT_FOUND")
    doc = db.get(Document, ev.document_id)
    if not doc or doc.revoked:
        raise AppError("EVIDENCE_UNAVAILABLE")
    return ok(ev.payload)


@router.get("/answers/{answer_id}/feedback", response_model=Envelope[FeedbackOut | None])
def feedback(
    answer_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    owned_answer(db, answer_id, actor)
    row = db.scalar(
        select(Feedback).where(Feedback.answer_id == answer_id, Feedback.owner_id == actor.id)
    )
    return ok(serialize(row) if row else None)


@router.put("/answers/{answer_id}/feedback", response_model=Envelope[FeedbackOut])
def put_feedback(
    answer_id: str,
    body: FeedbackInput,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    answer = owned_answer(db, answer_id, actor)
    req = db.get(AnswerRequest, answer.request_id)
    if req.owner_id != actor.id:
        raise AppError("FORBIDDEN")
    # Lock the existing parent before looking for feedback: FOR UPDATE on an
    # absent feedback row alone cannot serialize simultaneous first saves.
    db.refresh(answer, with_for_update=True)
    row = db.scalar(
        select(Feedback)
        .where(Feedback.answer_id == answer_id, Feedback.owner_id == actor.id)
        .with_for_update()
    )
    if not row:
        row = Feedback(answer_id=answer_id, owner_id=actor.id)
        db.add(row)
    row.helpful = body.helpful
    row.comment = body.comment
    row.review_state = "pending"
    db.commit()
    return ok(serialize(row))


class ReviewInput(Contract):
    review_state: Literal["pending", "reviewed", "actioned"]
    review_note: str = Field(default="", max_length=5000)
    issue: str | None = Field(default=None, max_length=500)


@router.get("/admin/feedback", response_model=Envelope[list[FeedbackOut]])
def all_feedback(db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    return ok(
        [serialize(r) for r in db.scalars(select(Feedback).order_by(Feedback.created_at.desc()))]
    )


@router.patch("/admin/feedback/{feedback_id}", response_model=Envelope[FeedbackOut])
def review(
    feedback_id: str,
    body: ReviewInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
):
    row = db.get(Feedback, feedback_id)
    if not row:
        raise AppError("NOT_FOUND")
    db.refresh(row, with_for_update=True)
    if body.review_state not in ("pending", "reviewed", "actioned"):
        raise AppError("VALIDATION_FAILED")
    row.review_state = body.review_state
    row.review_note = body.review_note
    row.issue = body.issue
    db.commit()
    return ok(serialize(row))


@router.get("/sessions/{session_id}/summary", response_model=Envelope[SummaryOut])
def summary(
    session_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    service.owned_session(db, session_id, actor)
    rows = service.history_rows(db, session_id)
    context = service.select_context(
        session_id, rows, max((m["sequence"] for m in rows), default=0)
    ).model_dump()
    return ok(
        {
            k: v
            for k, v in context.items()
            if k.startswith("summary") or k == "covered_until_sequence"
        }
    )


@router.post("/sessions/{session_id}/summary", response_model=Envelope[SummaryOut])
def rebuild_summary(
    session_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)
):
    service.owned_session(db, session_id, actor, lock=True)
    rows = service.history_rows(db, session_id)
    context = service.select_context(
        session_id, rows, max((m["sequence"] for m in rows), default=0)
    ).model_dump()
    service.persist_summary(db, session_id, context)
    db.commit()
    return ok(
        {
            k: v
            for k, v in context.items()
            if k.startswith("summary") or k == "covered_until_sequence"
        }
    )
