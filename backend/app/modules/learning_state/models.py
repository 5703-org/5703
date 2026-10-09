"""Additive learning state; memory erasure is separate from chat deletion."""

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import AuditMixin, Base
import datetime as dt


class MemorySettings(Base, AuditMixin):
    __tablename__ = "learning_memory_settings"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    revocation_epoch: Mapped[int] = mapped_column(Integer, default=0)
    event_sequence: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class MemoryEntry(Base, AuditMixin):
    __tablename__ = "learning_memory_entries"
    __table_args__ = (UniqueConstraint("owner_id", "category", "canonical_key"),)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    canonical_key: Mapped[str] = mapped_column(String(64))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str] = mapped_column(String(200), default="global")
    source_message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    match_policy: Mapped[str] = mapped_column(
        String(30), default="rules_only", server_default="rules_only"
    )
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    field_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scope_topics: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    verification: Mapped[str] = mapped_column(
        String(60), default="legacy_unverified", server_default="legacy_unverified"
    )
    writer_version: Mapped[str] = mapped_column(
        String(60),
        default="explicit_learning_memory_v1",
        server_default="explicit_learning_memory_v1",
    )
    source_details: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    effective_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_event_sequence: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class MemoryRevision(Base, AuditMixin):
    __tablename__ = "learning_memory_revisions"
    __table_args__ = (UniqueConstraint("entry_id", "entry_version"),)
    entry_id: Mapped[str] = mapped_column(ForeignKey("learning_memory_entries.id"), index=True)
    entry_version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(String(30))
    source_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")


class MemoryWriteEvent(Base, AuditMixin):
    __tablename__ = "learning_memory_write_events"
    __table_args__ = (
        UniqueConstraint("owner_id", "source_message_id"),
        UniqueConstraint("owner_id", "sequence"),
    )
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"))
    source_message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer)
    epoch: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    operations: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class MemorySuppression(Base, AuditMixin):
    __tablename__ = "learning_memory_suppressions"
    __table_args__ = (UniqueConstraint("owner_id", "source_message_id", "canonical_key"),)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    source_message_id: Mapped[str] = mapped_column(String(36))
    canonical_key: Mapped[str] = mapped_column(String(64))
    # Deliberately no deleted text, extraction payload or reversible ciphertext.


class MemorySnapshot(Base, AuditMixin):
    __tablename__ = "learning_memory_snapshots"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    revocation_epoch: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    invalidated: Mapped[bool] = mapped_column(Boolean, default=False)


class LearningTask(Base, AuditMixin):
    __tablename__ = "learning_tasks"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    initial_message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"))
    question: Mapped[str] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(String(40))
    teaching_mode: Mapped[str] = mapped_column(String(20), default="direct")
    help_level: Mapped[int] = mapped_column(Integer, default=0)
    exposure_epoch: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(20), default="active")
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    pending_tutor_question_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    pending_tutor_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_tutor_question_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    expected_response_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    turn_role: Mapped[str] = mapped_column(
        String(20), default="user_question", server_default="user_question"
    )
    last_attempt_evaluation: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AnswerPresentation(Base, AuditMixin):
    __tablename__ = "answer_presentations"
    answer_id: Mapped[str] = mapped_column(ForeignKey("answers.id"), unique=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("learning_tasks.id"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(100))


class LearningExposure(Base, AuditMixin):
    __tablename__ = "learning_exposures"
    __table_args__ = (UniqueConstraint("owner_id", "idempotency_key"),)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("learning_tasks.id"), nullable=True)
    answer_id: Mapped[str | None] = mapped_column(ForeignKey("answers.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(
        ForeignKey("answer_presentations.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class PrivateAnswerDraft(Base, AuditMixin):
    __tablename__ = "private_answer_drafts"
    request_id: Mapped[str] = mapped_column(ForeignKey("answer_requests.id"), index=True)
    memory_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("learning_memory_snapshots.id"), nullable=True
    )
    phase: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)


class SourceFragment(Base, AuditMixin):
    __tablename__ = "source_fragments"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    processing_id: Mapped[str] = mapped_column(ForeignKey("processing_runs.id"), index=True)
    source_unit_id: Mapped[str] = mapped_column(ForeignKey("source_units.id"))
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    text_hash: Mapped[str] = mapped_column(String(64))
    block_kind: Mapped[str] = mapped_column(String(40), default="prose")
    mapping_quality: Mapped[str] = mapped_column(String(40), default="exact_cleaned_text")


class AnswerAttribution(Base, AuditMixin):
    __tablename__ = "answer_attributions"
    answer_id: Mapped[str] = mapped_column(ForeignKey("answers.id"), unique=True)
    strategy: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON)
