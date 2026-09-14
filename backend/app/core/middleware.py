"""Trace middleware (Spec A10, I01).

Every request gets a trace id ( honouring an inbound X-Request-Id header ),
which is exposed on the response header and injected into logs + envelopes.
"""

from __future__ import annotations

import time
import re
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, trace_id_var

logger = get_logger("app.http")


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        supplied = request.headers.get("x-request-id", "")
        trace_id = supplied if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", supplied) else str(uuid4())
        token = trace_id_var.set(trace_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = trace_id
            logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            return response
        finally:
            trace_id_var.reset(token)
