"""Additive owner-scoped learning records; practice keys have no learner projection."""

import datetime as dt
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import AuditMixin, Base


class ReadingPosition(Base, AuditMixin):
    __tablename__ = "reading_positions"
    __table_args__ = (UniqueConstraint("owner_id", "document_id"),)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    source: Mapped[dict] = mapped_column(JSON)
    char_offset: Mapped[int] = mapped_column(Integer)


class StudyGoal(Base, AuditMixin):
    __tablename__ = "study_goals"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    release_id: Mapped[str] = mapped_column(ForeignKey("corpus_releases.id"))
    depth: Mapped[str] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(30), default="active")


class StudyUnit(Base, AuditMixin):
    __tablename__ = "study_goal_units"
    __table_args__ = (UniqueConstraint("goal_id", "section_id"),)
    goal_id: Mapped[str] = mapped_column(ForeignKey("study_goals.id"), index=True)
    section_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(500))
    ordinal: Mapped[int] = mapped_column(Integer)
    concepts: Mapped[list] = mapped_column(JSON, default=list)
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class StudyConceptRelation(Base, AuditMixin):
    """Reviewed, source-bound section concepts; proposals are never learner-visible."""

    __tablename__ = "study_concept_relations"
    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('prerequisite', 'related', 'confusion')",
            name="ck_study_relation_type",
        ),
        CheckConstraint(
            "state IN ('proposed', 'approved', 'rejected')",
            name="ck_study_relation_state",
        ),
        CheckConstraint(
            "from_section_id <> to_section_id", name="ck_study_relation_distinct_sections"
        ),
    )
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    release_id: Mapped[str] = mapped_column(ForeignKey("corpus_releases.id"), index=True)
    from_section_id: Mapped[str] = mapped_column(String(64))
    to_section_id: Mapped[str] = mapped_column(String(64))
    from_concept: Mapped[str] = mapped_column(String(200))
    to_concept: Mapped[str] = mapped_column(String(200))
    relation_type: Mapped[str] = mapped_column(String(20))
    source: Mapped[dict] = mapped_column(JSON)
    source_quote: Mapped[str] = mapped_column(Text)
    source_quote_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), default="proposed")
    proposer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class PracticeItem(Base, AuditMixin):
    __tablename__ = "practice_items"
    __table_args__ = (UniqueConstraint("group_id", "item_revision"),)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    creator_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    group_id: Mapped[str] = mapped_column(String(36))
    item_revision: Mapped[int] = mapped_column(Integer)
    previous_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("practice_items.id"), nullable=True
    )
    state: Mapped[str] = mapped_column(String(30), default="draft")
    public_payload: Mapped[dict] = mapped_column(JSON)
    private_rubric: Mapped[dict] = mapped_column(JSON)
    source: Mapped[dict] = mapped_column(JSON)
    validation: Mapped[dict] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64))


class PracticeProgress(Base, AuditMixin):
    __tablename__ = "practice_progress"
    __table_args__ = (UniqueConstraint("owner_id", "item_id"),)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("practice_items.id"))
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    help_level: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(30), default="awaiting_attempt")
    full_explanation: Mapped[bool] = mapped_column(Boolean, default=False)
    shown_hints: Mapped[list] = mapped_column(JSON, default=list)
    tutor_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("learning_tasks.id"), nullable=True
    )


class PracticeAttempt(Base, AuditMixin):
    __tablename__ = "practice_attempts"
    __table_args__ = (UniqueConstraint("owner_id", "idempotency_key"),)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("practice_items.id"), index=True)
    progress_id: Mapped[str] = mapped_column(ForeignKey("practice_progress.id"))
    goal_id: Mapped[str | None] = mapped_column(ForeignKey("study_goals.id"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    body_hash: Mapped[str] = mapped_column(String(64))
    item_revision: Mapped[int] = mapped_column(Integer)
    response: Mapped[dict] = mapped_column(JSON)
    feedback: Mapped[dict] = mapped_column(JSON)
    progress_version: Mapped[int] = mapped_column(Integer)


class ReviewEntry(Base, AuditMixin):
    __tablename__ = "study_review_entries"
    __table_args__ = (
        UniqueConstraint("owner_id", "item_id"),
        UniqueConstraint("owner_id", "note_id", name="uq_review_owner_note"),
        CheckConstraint(
            "(item_id IS NOT NULL) <> (note_id IS NOT NULL)",
            name="ck_review_exactly_one_target",
        ),
    )
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[str | None] = mapped_column(ForeignKey("practice_items.id"), nullable=True)
    note_id: Mapped[str | None] = mapped_column(
        ForeignKey("study_notes.id"), nullable=True, index=True
    )
    due_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    error_categories: Mapped[list] = mapped_column(JSON, default=list)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    scheduling_reason: Mapped[str] = mapped_column(String(200))


class StudyNote(Base, AuditMixin):
    __tablename__ = "study_notes"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(30))
    source: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answer_id: Mapped[str | None] = mapped_column(ForeignKey("answers.id"), nullable=True)
    goal_id: Mapped[str | None] = mapped_column(ForeignKey("study_goals.id"), nullable=True)
    concepts: Mapped[list] = mapped_column(JSON, default=list)


class LearningRecord(Base, AuditMixin):
    __tablename__ = "learning_records"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    object_id: Mapped[str] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
