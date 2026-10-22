"""Shared, non-normalizing checks for persisted user text."""


def reject_null_character(value: str | None) -> str | None:
    """Reject actual U+0000 without changing text or idempotency identities."""
    if value is not None and "\x00" in value:
        raise ValueError("Text contains an unsupported null character (U+0000). Remove it and retry.")
    return value
