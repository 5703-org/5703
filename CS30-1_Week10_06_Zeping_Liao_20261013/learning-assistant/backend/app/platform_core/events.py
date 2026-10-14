"""Domain event helpers (Spec M06).

publish_event() must be called with the same Session that writes the
business data, inside one transaction.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import trace_id_var
from app.platform_core.models import OutboxEvent

EVENT_VERSION = "1.0"


def publish_event(
    db: Session, event_type: str, payload: dict, workspace_id: str | None = None
) -> OutboxEvent:
    event = OutboxEvent(
        event_type=event_type,
        event_version=EVENT_VERSION,
        workspace_id=workspace_id,
        trace_id=trace_id_var.get() if trace_id_var.get() != "-" else None,
        payload=payload,
    )
    db.add(event)
    return event
