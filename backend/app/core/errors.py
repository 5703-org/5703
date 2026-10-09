"""Stable error code catalog (Spec A13, I03).

Codes are part of the API contract: the frontend maps codes to UI states,
so they must never be renamed silently - add a new code instead.
"""

from __future__ import annotations

# code -> (http_status, safe_message shown to end users)
CATALOG: dict[str, tuple[int, str]] = {
    "MODEL_UNAVAILABLE": (503, "The selected model service is not configured."),
    "MEMORY_POLICY_UNAVAILABLE": (
        503,
        "The learning-memory policy configuration is unavailable.",
    ),
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
    "PARSER_INPUT_LIMIT": (413, "The source exceeds the parser input limit."),
    "PARSER_OUTPUT_LIMIT": (413, "The parsed source exceeds the output limit."),
    "PARSER_TIMEOUT": (504, "Source parsing exceeded the allowed time."),
    "PARSER_FAILED": (422, "Source parsing failed. Review the original file."),
    "PARSER_EXECUTION_ERROR": (503, "The isolated source parser is unavailable."),
    "PARSER_PROTOCOL_ERROR": (502, "The isolated parser returned an invalid result."),
    "EVIDENCE_UNAVAILABLE": (410, "This original source passage is no longer available."),
    "BUDGET_EXHAUSTED": (409, "This request has used its allowed attempts or execution time."),
    "SEMANTIC_CHECK_FAILED": (
        502,
        "The answer did not pass the required evidence and teaching checks. Try a narrower question or retry.",
    ),
    "SEMANTIC_CHECK_UNAVAILABLE": (
        503,
        "The answer checker is unavailable. Retry when the model service is ready.",
    ),
    "CHECKER_INCONSISTENT": (
        502,
        "The answer checker returned an incomplete or inconsistent result. Please retry.",
    ),
    "CONTEXT_LIMIT": (
        422,
        "The question and required evidence exceed the configured model context. Try a shorter question or ask an administrator to review the model limits.",
    ),
    "PROVIDER_TIMEOUT": (504, "The model service did not respond within the allowed time."),
    "PROVIDER_NETWORK_ERROR": (503, "The model service could not be reached. Please retry."),
    "PROVIDER_HTTP_ERROR": (
        502,
        "The model service rejected the request. An administrator can inspect the provider diagnostic.",
    ),
    "BAD_REQUEST": (400, "The request is invalid."),
    "UNAUTHORIZED": (401, "Authentication is required or has failed."),
    "BAD_CREDENTIALS": (401, "Invalid email or password."),
    "LOGIN_RATE_LIMITED": (429, "Too many login attempts. Please try again later."),
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
