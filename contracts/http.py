"""Typed HTTP envelopes and runtime views shared by OpenAPI consumers."""

from typing import Generic, Literal, TypeVar
from pydantic import BaseModel, ConfigDict
from contracts.models import Contract, ErrorData

T = TypeVar("T")


class ResponseMeta(BaseModel):
    model_config = ConfigDict(extra="allow")
    trace_id: str


class Envelope(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")
    data: T
    meta: ResponseMeta


class ErrorEnvelope(BaseModel):
    error: ErrorData
    meta: ResponseMeta


class FeedbackOut(Contract):
    id: str
    answer_id: str
    owner_id: str
    helpful: bool | None
    comment: str
    review_state: Literal["pending", "reviewed", "actioned"]
    review_note: str
    issue: str | None
    version: int
    created_at: str
    updated_at: str


class SummaryOut(Contract):
    summary_id: str | None
    summary_hash: str | None
    covered_until_sequence: int | None
    summary_text: str | None


class CapabilitiesOut(Contract):
    model_mode: Literal["mock", "live"]
    chat_ready: bool
    evaluation_ready: bool
    missing_reasons: dict[str, list[str]]
    providers: list[dict]
    feature_flags: dict[str, bool]
    contract_versions: list[dict[str, str]]
