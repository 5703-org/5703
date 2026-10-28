"""Immutable source processing and released chunk membership."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import AuditMixin, Base
from pgvector.sqlalchemy import Vector


class Document(Base, AuditMixin):
    __tablename__ = "documents"
    title: Mapped[str] = mapped_column(String(500))
    edition: Mapped[str] = mapped_column(String(200), default="")
    source_url: Mapped[str] = mapped_column(Text, default="")
    license: Mapped[str] = mapped_column(Text, default="Not specified")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class DocumentVersion(Base, AuditMixin):
    __tablename__ = "document_versions"
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    raw_hash: Mapped[str] = mapped_column(String(64), unique=True)
    media_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(250))


class Configuration(Base, AuditMixin):
    __tablename__ = "configurations"
    kind: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))
    values: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)


class ProcessingRun(Base, AuditMixin):
    __tablename__ = "processing_runs"
    __table_args__ = (UniqueConstraint("document_version_id", "config_hash"),)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    config_hash: Mapped[str] = mapped_column(String(64))
    configuration: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(40), default="registered")
    counts: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SourceUnit(Base, AuditMixin):
    __tablename__ = "source_units"
    processing_id: Mapped[str] = mapped_column(ForeignKey("processing_runs.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    page: Mapped[int] = mapped_column(Integer)
    section: Mapped[str] = mapped_column(String(500))
    raw_text: Mapped[str] = mapped_column(Text)
    cleaned_text: Mapped[str] = mapped_column(Text)
    quality: Mapped[str] = mapped_column(String(30))
    issues: Mapped[list] = mapped_column(JSON, default=list)


class Chunk(Base, AuditMixin):
    __tablename__ = "chunks"
    processing_id: Mapped[str] = mapped_column(ForeignKey("processing_runs.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    text_hash: Mapped[str] = mapped_column(String(64))
    section: Mapped[str] = mapped_column(String(500))
    pages: Mapped[list] = mapped_column(JSON)
    spans: Mapped[list] = mapped_column(JSON)
    tokens: Mapped[int] = mapped_column(Integer)


class CorpusRelease(Base, AuditMixin):
    __tablename__ = "corpus_releases"
    name: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(40), default="building")
    configuration: Mapped[dict] = mapped_column(JSON)
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ReleaseChunk(Base):
    __tablename__ = "release_chunks"
    release_id: Mapped[str] = mapped_column(ForeignKey("corpus_releases.id"), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunks.id"), primary_key=True)
    embedding: Mapped[list] = mapped_column(Vector().with_variant(JSON, "sqlite"))
    dimension: Mapped[int] = mapped_column(Integer)
    model_revision: Mapped[str] = mapped_column(String(200))


class ActiveCorpus(Base):
    __tablename__ = "active_corpus"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    release_id: Mapped[str | None] = mapped_column(ForeignKey("corpus_releases.id"), nullable=True)


class RetrievalEpoch(Base):
    __tablename__ = "retrieval_epochs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(36))


class VisualRegion(Base):
    """Immutable native-PDF candidate, excluded from released answer evidence."""

    __tablename__ = "visual_regions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), index=True)
    physical_page: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    bbox: Mapped[list] = mapped_column(JSON, nullable=False)
    native_text: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_status: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    extractor_revision: Mapped[str] = mapped_column(String(80), nullable=False)
    catalog_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class VisualRegionReview(Base, AuditMixin):
    """Separate human decision; original candidate bytes remain unchanged."""

    __tablename__ = "visual_region_reviews"

    region_id: Mapped[str] = mapped_column(ForeignKey("visual_regions.id"), index=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    checks: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def _immutable_visual(_mapper, _connection, _target):
    raise ValueError("Source-bound visual candidates are immutable; import a new catalog version.")


for _visual_model in (VisualRegion, VisualRegionReview):
    event.listen(_visual_model, "before_update", _immutable_visual)
    event.listen(_visual_model, "before_delete", _immutable_visual)
