"""Unified success envelope (Spec A12): {"data": ..., "meta": {"trace_id": ...}}."""

from __future__ import annotations

from typing import Any

from app.core.logging import trace_id_var


def ok(data: Any = None, meta: dict | None = None) -> dict:
    envelope_meta: dict[str, Any] = {"trace_id": trace_id_var.get()}
    if meta:
        envelope_meta.update(meta)
    return {"data": data, "meta": envelope_meta}
