"""Learning module API schemas."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class SessionRename(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    version: int = Field(ge=1)  # optimistic locking (Spec B05)


class SessionOut(BaseModel):
    id: str
    title: str
    status: str
    version: int
    created_at: dt.datetime
    updated_at: dt.datetime
