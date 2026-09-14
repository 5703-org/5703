"""Application error type + global exception mapping (Spec A13, I04).

Safe messages go to the client. Unexpected errors log only their class and
trace identity; exception messages and tracebacks can contain SQL parameters.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import CATALOG, http_status_for, safe_message_for
from app.core.logging import get_logger, trace_id_var

logger = get_logger("app.errors")


class AppError(Exception):
    """Domain error carrying a stable catalog code."""

    def __init__(self, code: str, detail: str | None = None, internal: str | None = None):
        self.code = code
        self.detail = detail
        self.internal = internal
        super().__init__(detail or code)


def _envelope(code: str, details=None) -> dict:
    if details is None:
        details = {}
    elif isinstance(details, list):
        details = {"violations": details}
    elif isinstance(details, str):
        details = {"reason": details}
    return {
        "error": {"code": code, "message": safe_message_for(code), "details": details},
        "meta": {"trace_id": trace_id_var.get()},
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.internal:
            logger.warning("app error: %s", exc.internal, extra={"event": "app_error"})
        return JSONResponse(
            status_code=http_status_for(exc.code), content=_envelope(exc.code, exc.detail)
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": [str(p) for p in e.get("loc", [])], "msg": e.get("msg", "")}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content=_envelope("VALIDATION_FAILED", details))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = next((c for c, (s, _) in CATALOG.items() if s == exc.status_code), None)
        code = code or ("INTERNAL_ERROR" if exc.status_code >= 500 else "BAD_REQUEST")
        return JSONResponse(status_code=exc.status_code, content=_envelope(code, exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Do not attach exc_info: other installed formatters may render its
        # exception/cause messages even when our JSON formatter does not.
        logger.error(
            "Unhandled application error (%s)",
            type(exc).__name__,
            extra={"event": "unhandled_error"},
        )
        return JSONResponse(status_code=500, content=_envelope("INTERNAL_ERROR"))
