"""Shared platform tables (Spec M06): transactional outbox.

Written inside the same transaction as the business data, so a committed
change can never lose its event; a rolled-back change never publishes one.
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','delivered','failed','dead')", name="ck_outbox_status"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
