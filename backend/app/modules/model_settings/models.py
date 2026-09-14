"""Immutable configuration, credential, test and activation records."""

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, new_uuid, utcnow


class ModelCredential(Base):
    __tablename__ = "model_credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    ciphertext: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelConfiguration(Base):
    __tablename__ = "model_configurations"
    __table_args__ = (
        UniqueConstraint("group_id", "revision", name="uq_model_config_group_revision"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    group_id: Mapped[str] = mapped_column(String(36), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    previous_id: Mapped[str | None] = mapped_column(ForeignKey("model_configurations.id"))
    name: Mapped[str] = mapped_column(String(120))
    preset: Mapped[str] = mapped_column(String(60))
    public_config: Mapped[dict] = mapped_column(JSON)
    config_hash: Mapped[str] = mapped_column(String(64))
    credential_id: Mapped[str | None] = mapped_column(ForeignKey("model_credentials.id"))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelConnectionTest(Base):
    __tablename__ = "model_connection_tests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    configuration_id: Mapped[str] = mapped_column(ForeignKey("model_configurations.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    diagnostic_code: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(String(500))
    latency_ms: Mapped[int] = mapped_column(Integer)
    usage: Mapped[dict] = mapped_column(JSON)
    tested_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ActiveModelConfiguration(Base):
    __tablename__ = "active_model_configurations"
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    configuration_id: Mapped[str | None] = mapped_column(ForeignKey("model_configurations.id"))
    version: Mapped[int] = mapped_column(Integer, default=0)


class ModelActivation(Base):
    __tablename__ = "model_activations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    previous_id: Mapped[str | None] = mapped_column(ForeignKey("model_configurations.id"))
    configuration_id: Mapped[str | None] = mapped_column(ForeignKey("model_configurations.id"))
    test_id: Mapped[str | None] = mapped_column(ForeignKey("model_connection_tests.id"))
    active_version: Mapped[int] = mapped_column(Integer)
    activated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def _immutable(_mapper, _connection, _target):
    raise ValueError("Model history is immutable; create a new version instead.")


for _record in (ModelCredential, ModelConfiguration, ModelConnectionTest, ModelActivation):
    event.listen(_record, "before_update", _immutable)
    event.listen(_record, "before_delete", _immutable)
