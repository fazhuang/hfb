"""
Request ID middleware — injects X-Request-ID into every response and log context.

Generates a UUID per request if not provided by the client.
Validates inbound values; rejects control characters, newlines, and excessive length.
Logs request_started / request_completed / request_failed with structured data.
"""
from __future__ import annotations

import re
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_REQUEST_ID_LENGTH = 128
_VALID_REQUEST_ID_RE = re.compile(r"^[a-zA-Z0-9\-_.@]+$")


def _sanitize_request_id(raw: str | None) -> str:
    """Validate or replace a client-supplied request ID.

    Rejects IDs that contain newlines, control characters, or are >128 chars.
    Returns a fresh UUID v4 if the supplied value is unsafe.
    """
    if raw is None:
        return str(uuid4())
    if len(raw) > _MAX_REQUEST_ID_LENGTH:
        return str(uuid4())
    if not _VALID_REQUEST_ID_RE.match(raw):
        return str(uuid4())
    return raw


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensures every response carries a valid X-Request-ID header.

    Must be registered last (last add_middleware call) so Starlette wraps it
    as the outermost layer — error handlers, CORS preflight, and downstream
    middleware always have access to request.state.request_id.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        inbound = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
        request_id = _sanitize_request_id(inbound)
        request.state.request_id = request_id

        start = time.monotonic()
        logger.info(
            "request_started request_id=%s method=%s path=%s",
            request_id, request.method, request.url.path,
        )

        response: Response | None = None
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            logger.exception(
                "request_failed request_id=%s method=%s path=%s elapsed_ms=%s",
                request_id, request.method, request.url.path, elapsed_ms,
            )
            raise
        else:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            logger.info(
                "request_completed request_id=%s method=%s path=%s status=%d elapsed_ms=%s",
                request_id, request.method, request.url.path,
                response.status_code, elapsed_ms,
            )
        finally:
            if response is not None:
                response.headers["X-Request-ID"] = request_id

        return response
