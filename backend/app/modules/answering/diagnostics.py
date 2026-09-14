"""Workspace-scoped failure inspection with explicitly selected diagnostic fields."""

from datetime import datetime
from typing import Literal

from pydantic import Field
from sqlalchemy import func, or_, select

from contracts.models import Contract
from app.core.errors import safe_message_for
from app.core.exceptions import AppError
from app.modules.answering.models import Answer, AnswerRequest, Attempt, Evidence, Job
from app.modules.identity.models import User
from app.modules.learning.models import ChatSession


class FailureCounts(Contract):
    candidates: int | None = None
    submitted: int | None = None
    cited: int | None = None


class FailureModel(Contract):
    provider: str | None = None
    model: str | None = None
    configuration_id: str | None = None


class FailureSummary(Contract):
    request_id: str
    session_id: str | None = None
    owner_id: str
    question: str
    state: str
    response_type: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    model: FailureModel
    counts: FailureCounts


class FailurePage(Contract):
    items: list[FailureSummary]
    total: int
    limit: int
    offset: int


class FailureStage(Contract):
    stage: str
    status: str
    detail: str


class FailureAttempt(Contract):
    stage: str
    status: str
    error_code: str | None = None
    duration_ms: float | None = None
    created_at: datetime


class FailureEvidence(Contract):
    candidate_chunk_ids: list[str] = Field(default_factory=list)
    submitted_chunk_ids: list[str] = Field(default_factory=list)
    cited_chunk_ids: list[str] = Field(default_factory=list)


class FailureDetail(FailureSummary):
    http_trace_id: str | None = None
    stages: list[FailureStage]
    budget: dict[str, int | float]
    attempts: list[FailureAttempt]
    retrieval_query: str | None = None
    evidence: FailureEvidence
    answer_text: str | None = None
    refusal_reason: str | None = None


FailureFilter = Literal["all", "error", "refused", "clarification", "cancelled", "answered"]


def scoped_requests(actor):
    return (
        select(AnswerRequest)
        .join(User, AnswerRequest.owner_id == User.id)
        .outerjoin(ChatSession, AnswerRequest.session_id == ChatSession.id)
        .where(
            User.workspace_id == actor.workspace_id,
            AnswerRequest.mode == "interactive_chat",
            or_(AnswerRequest.session_id.is_(None), ChatSession.deleted_at.is_(None)),
        )
    )


def _text(value, limit=160):
    return value[:limit] if isinstance(value, str) else None


def _count(value):
    return value if type(value) is int and value >= 0 else None


def _dict(value):
    return value if isinstance(value, dict) else {}


def _strings(value):
    return (
        list(dict.fromkeys(v[:160] for v in value if isinstance(v, str)))
        if isinstance(value, list)
        else []
    )


def summarize(db, req):
    answer = db.scalar(select(Answer).where(Answer.request_id == req.id))
    job = db.scalar(
        select(Job).where(Job.request_id == req.id).order_by(Job.created_at.desc(), Job.id.desc())
    )
    response = _dict(answer.response) if answer else {}
    error = _dict(job.error) if job else {}
    trace = _dict(req.trace)
    selection = _dict(trace.get("evidence_selection"))
    candidates = trace.get("retrieval_candidates")
    evidence = (
        list(db.scalars(select(Evidence).where(Evidence.answer_id == answer.id))) if answer else []
    )
    submitted_ids = _strings(selection.get("submitted_evidence_ids"))
    cited_ids = _strings(response.get("citations"))
    model = _dict(_dict(req.command).get("model_config"))
    counts = FailureCounts(
        candidates=_count(selection.get("candidate_count")),
        submitted=_count(selection.get("submitted_count")),
        cited=_count(selection.get("cited_count")),
    )
    if counts.candidates is None and isinstance(candidates, list):
        counts.candidates = len(candidates)
    if counts.submitted is None and (answer or submitted_ids):
        counts.submitted = len(evidence) if answer else len(submitted_ids)
    if answer:
        counts.cited = len(cited_ids)
    code = _text(error.get("code"))
    summary = FailureSummary(
        request_id=req.id,
        session_id=req.session_id,
        owner_id=req.owner_id,
        question=_text(_dict(req.command).get("question"), 4000) or "",
        state=req.state,
        response_type=_text(response.get("response_type")),
        error_code=code,
        # Provider/transport text can contain credentials or response bodies.
        error_message=safe_message_for(code) if code else None,
        created_at=req.created_at,
        model=FailureModel(
            **{k: _text(model.get(k)) for k in ("provider", "model", "configuration_id")}
        ),
        counts=counts,
    )
    return summary, answer, job, evidence


def list_failures(db, actor, limit=50, offset=0, state=None):
    query = scoped_requests(actor)
    if state != "all":
        query = (
            query.where(AnswerRequest.state == state)
            if state
            else query.where(
                AnswerRequest.state.in_(["error", "refused", "clarification", "cancelled"])
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(AnswerRequest.created_at.desc(), AnswerRequest.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return FailurePage(
        items=[summarize(db, row)[0] for row in rows], total=total, limit=limit, offset=offset
    )


def failure_detail(db, actor, request_id):
    req = db.scalar(scoped_requests(actor).where(AnswerRequest.id == request_id))
    if not req:
        raise AppError("NOT_FOUND")
    summary, answer, job, stored = summarize(db, req)
    trace = _dict(req.trace)
    selection = _dict(trace.get("evidence_selection"))
    candidates = trace.get("retrieval_candidates")
    candidate_ids = _strings(selection.get("candidate_chunk_ids"))
    if not candidate_ids and isinstance(candidates, list):
        candidate_ids = _strings([_dict(item).get("chunk_id") for item in candidates])
    response = _dict(answer.response) if answer else {}
    cited_ids = _strings(response.get("citations"))
    prepared = _dict(trace.get("prepared_query"))
    attempts = []
    records = db.scalars(
        select(Attempt)
        .join(Job, Attempt.job_id == Job.id)
        .where(Job.request_id == req.id)
        .order_by(Attempt.created_at, Attempt.sequence)
    )
    for record in records:
        payload = _dict(record.payload)
        error = _dict(payload.get("error"))
        elapsed = payload.get("latency_ms")
        attempts.append(
            FailureAttempt(
                stage=_text(payload.get("stage")) or "generation",
                status="error" if error else (_text(payload.get("phase")) or "recorded"),
                error_code=_text(error.get("code")),
                duration_ms=elapsed if type(elapsed) in (int, float) and elapsed >= 0 else None,
                created_at=record.created_at,
            )
        )
    count = summary.counts
    stages = [
        FailureStage(
            stage="query",
            status="recorded" if prepared else "unavailable",
            detail=_text(prepared.get("intent")) or "Question preparation",
        ),
        FailureStage(
            stage="retrieval",
            status="recorded" if count.candidates is not None else "unavailable",
            detail=f"Candidate passages: {count.candidates}"
            if count.candidates is not None
            else "Candidate count was not recorded",
        ),
        FailureStage(
            stage="evidence",
            status="recorded" if count.submitted is not None else "unavailable",
            detail=f"Submitted passages: {count.submitted}"
            if count.submitted is not None
            else "Submitted count was not recorded",
        ),
        FailureStage(
            stage=job.stage if job else "request",
            status=job.state if job else req.state,
            detail=summary.error_message or summary.response_type or req.state,
        ),
    ]
    budget = {
        k: v
        for k, v in _dict(req.budget).items()
        if k
        in {
            "consumed_calls",
            "active_seconds",
            "format_repairs",
            "transient_retries",
            "max_calls",
            "max_active_seconds",
        }
        and type(v) in (int, float)
    }
    return FailureDetail(
        **summary.model_dump(),
        http_trace_id=_text(trace.get("http_trace_id")),
        stages=stages,
        budget=budget,
        attempts=attempts,
        retrieval_query=_text(prepared.get("retrieval_query") or prepared.get("query"), 4000),
        evidence=FailureEvidence(
            candidate_chunk_ids=candidate_ids,
            submitted_chunk_ids=[item.chunk_id for item in stored]
            or _strings(selection.get("submitted_chunk_ids")),
            cited_chunk_ids=[item.chunk_id for item in stored if item.evidence_id in cited_ids],
        ),
        answer_text=_text(response.get("answer_text"), 30000),
        refusal_reason=_text(response.get("refusal_reason")),
    )
