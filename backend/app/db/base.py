"""Declarative base + shared audit columns (Spec B03, A09).

IDs are UUID strings (portable across SQLite dev and Postgres prod),
timestamps are timezone-aware UTC.
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_uuid() -> str:
    return str(uuid4())


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    pass


class AuditMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    # Optimistic-locking counter (Spec B05): every mutating update bumps it.
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
