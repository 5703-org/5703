"""Durable conversation requests, immutable snapshots and atomic publication."""

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import AuditMixin, Base


class Message(Base, AuditMixin):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence"),
        CheckConstraint("role in ('user','assistant')"),
    )
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(30), default="queued")
    active_answer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Snapshot(Base, AuditMixin):
    __tablename__ = "snapshots"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("sessions.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))


class SessionSummary(Base, AuditMixin):
    __tablename__ = "session_summaries"
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    covered_until_sequence: Mapped[int] = mapped_column(Integer)
    source_message_ids: Mapped[list] = mapped_column(JSON)
    summary_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    token_count: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(80))
    invalidated: Mapped[bool] = mapped_column(Boolean, default=False)


class AnswerRequest(Base, AuditMixin):
    __tablename__ = "answer_requests"
    __table_args__ = (UniqueConstraint("owner_id", "route", "idempotency_key"),)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    route: Mapped[str] = mapped_column(String(250))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    body_hash: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(30))
    response_schema: Mapped[str] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(30), default="queued")
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.id"), nullable=True, index=True
    )
    user_message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    assistant_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True
    )
    context_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("snapshots.id"), nullable=True
    )
    profile_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("snapshots.id"), nullable=True
    )
    release_id: Mapped[str | None] = mapped_column(ForeignKey("corpus_releases.id"), nullable=True)
    config_id: Mapped[str | None] = mapped_column(ForeignKey("configurations.id"), nullable=True)
    regeneration_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    item_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    command: Mapped[dict] = mapped_column(JSON, default=dict)
    budget: Mapped[dict] = mapped_column(JSON, default=dict)
    trace: Mapped[dict] = mapped_column(JSON, default=dict)


class Job(Base, AuditMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "state in ('queued','running','retry_wait','succeeded','failed','cancelled')"
        ),
    )
    request_id: Mapped[str | None] = mapped_column(
        ForeignKey("answer_requests.id"), nullable=True, index=True
    )
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(40), default="answer")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(40), default="queued")
    execution_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class Attempt(Base, AuditMixin):
    __tablename__ = "attempts"
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class Answer(Base, AuditMixin):
    __tablename__ = "answers"
    request_id: Mapped[str] = mapped_column(ForeignKey("answer_requests.id"), unique=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    response_schema: Mapped[str] = mapped_column(String(40))
    response: Mapped[dict] = mapped_column(JSON)
    model_mode: Mapped[str] = mapped_column(String(20))
    timing: Mapped[dict] = mapped_column(JSON, default=dict)


class Evidence(Base, AuditMixin):
    __tablename__ = "evidence_snapshots"
    __table_args__ = (UniqueConstraint("answer_id", "evidence_id"),)
    answer_id: Mapped[str] = mapped_column(ForeignKey("answers.id"), index=True)
    evidence_id: Mapped[str] = mapped_column(String(40))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    chunk_id: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)


class Citation(Base, AuditMixin):
    __tablename__ = "citations"
    __table_args__ = (UniqueConstraint("answer_id", "evidence_id"),)
    answer_id: Mapped[str] = mapped_column(ForeignKey("answers.id"))
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_snapshots.id"))


class Feedback(Base, AuditMixin):
    __tablename__ = "feedback"
    __table_args__ = (UniqueConstraint("answer_id", "owner_id"),)
    answer_id: Mapped[str] = mapped_column(ForeignKey("answers.id"))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    review_state: Mapped[str] = mapped_column(String(30), default="pending")
    review_note: Mapped[str] = mapped_column(Text, default="")
    issue: Mapped[str | None] = mapped_column(String(500), nullable=True)
