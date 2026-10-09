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
    checker_configuration_id: Mapped[str | None] = mapped_column(
        ForeignKey("model_configurations.id")
    )


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
    answer_probe_id: Mapped[str | None] = mapped_column(ForeignKey("model_compatibility_runs.id"))
    checker_probe_id: Mapped[str | None] = mapped_column(ForeignKey("model_compatibility_runs.id"))
    checker_configuration_id: Mapped[str | None] = mapped_column(
        ForeignKey("model_configurations.id")
    )


class ModelCompatibilityRun(Base):
    __tablename__ = "model_compatibility_runs"
    __table_args__ = (
        UniqueConstraint("configuration_id", "idempotency_key", name="uq_model_probe_key"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    configuration_id: Mapped[str] = mapped_column(ForeignKey("model_configurations.id"), index=True)
    tested_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    input_hash: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(20))
    tier: Mapped[str] = mapped_column(String(20))
    network_label: Mapped[str] = mapped_column(String(80))
    config_hash: Mapped[str] = mapped_column(String(64))
    test_version: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="running")
    diagnostic_code: Mapped[str] = mapped_column(String(60), default="PROBE_RUNNING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModelCompatibilityStage(Base):
    __tablename__ = "model_compatibility_stages"
    __table_args__ = (UniqueConstraint("run_id", "tier", name="uq_model_probe_stage"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("model_compatibility_runs.id"), index=True)
    tier: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="started")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)


def _immutable(_mapper, _connection, _target):
    raise ValueError("Model history is immutable; create a new version instead.")


for _record in (ModelCredential, ModelConfiguration, ModelConnectionTest, ModelActivation):
    event.listen(_record, "before_update", _immutable)
    event.listen(_record, "before_delete", _immutable)


def _finished_immutable(_mapper, connection, target):
    # The only update is started -> terminal. Request identity cannot be revised.
    from sqlalchemy import inspect, select

    state = inspect(target)
    permitted = (
        {"status", "diagnostic_code", "completed_at"}
        if isinstance(target, ModelCompatibilityRun)
        else {"status", "metadata_json", "result_json", "completed_at"}
    )
    if any(
        attribute.history.has_changes()
        for attribute in state.attrs
        if attribute.key not in permitted
    ):
        _immutable(None, None, None)
    if (
        connection.execute(
            select(target.__table__.c.completed_at).where(target.__table__.c.id == target.id)
        ).scalar()
        is not None
    ):
        _immutable(None, None, None)


for _record in (ModelCompatibilityRun, ModelCompatibilityStage):
    event.listen(_record, "before_update", _finished_immutable)
    event.listen(_record, "before_delete", _immutable)
