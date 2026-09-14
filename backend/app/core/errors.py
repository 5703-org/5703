"""Stable error code catalog (Spec A13, I03).

Codes are part of the API contract: the frontend maps codes to UI states,
so they must never be renamed silently - add a new code instead.
"""

from __future__ import annotations

# code -> (http_status, safe_message shown to end users)
CATALOG: dict[str, tuple[int, str]] = {
    "MODEL_UNAVAILABLE": (503, "The selected model service is not configured."),
    "SESSION_BUSY": (
        409,
        "Wait for the current response or stop it before sending another message.",
    ),
    "IDEMPOTENCY_CONFLICT": (409, "This request key was already used for different content."),
    "RETRY_NOT_ALLOWED": (409, "This request can no longer be retried. Send a new message."),
    "REGENERATE_NOT_ALLOWED": (409, "Only the latest active answer can be regenerated."),
    "UPLOAD_TOO_LARGE": (413, "The uploaded file exceeds the configured size limit."),
    "UNSUPPORTED_MEDIA": (415, "Upload a valid PDF or UTF-8 text file."),
    "SOURCE_UNAVAILABLE": (503, "The required source is currently unavailable."),
    "EVIDENCE_UNAVAILABLE": (410, "This original source passage is no longer available."),
    "BUDGET_EXHAUSTED": (409, "This request has used its allowed attempts or execution time."),
    "BAD_REQUEST": (400, "The request is invalid."),
    "UNAUTHORIZED": (401, "Authentication is required or has failed."),
    "BAD_CREDENTIALS": (401, "Invalid email or password."),
    "TOKEN_INVALID": (401, "The token is invalid or has expired."),
    "FORBIDDEN": (403, "You do not have permission to perform this action."),
    "NOT_FOUND": (404, "The requested resource was not found."),
    "CONFLICT": (409, "The operation conflicts with the current state of the resource."),
    "VALIDATION_FAILED": (422, "The request could not be validated."),
    "INTERNAL_ERROR": (500, "An unexpected error occurred."),
}


def http_status_for(code: str) -> int:
    return CATALOG.get(code, (500, ""))[0]


def safe_message_for(code: str) -> str:
    return CATALOG.get(code, (500, "An unexpected error occurred."))[1]
