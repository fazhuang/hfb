
"""Unit tests for app.core.error_handlers — all exception handlers."""

from __future__ import annotations

import pytest
from app.core.error_handlers import (
    _attach_request_id,
    _error_envelope,
    _get_request_id,
    domain_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    request_validation_handler,
    status_transition_handler,
)
from app.core.exceptions import DomainException
from app.core.status_machine import InvalidStatusTransitionError
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


# --- Pure functions (no async dependency) ---


class TestErrorEnvelope:
    def test_structure(self) -> None:
        envelope = _error_envelope(404, "Not found", "NOT_FOUND", "req-1")
        assert envelope["success"] is False
        assert envelope["message"] == "Not found"
        assert envelope["meta"]["error_code"] == "NOT_FOUND"
        assert envelope["meta"]["request_id"] == "req-1"
        assert envelope["data"] is None
        assert "timestamp" in envelope

    def test_with_metadata(self) -> None:
        envelope = _error_envelope(422, "Bad", "VALIDATION", "r2", metadata={"fields": ["x"]})
        assert envelope["meta"]["metadata"] == {"fields": ["x"]}


class TestGetRequestId:
    def test_returns_state_value(self) -> None:
        scope = {"type": "http", "method": "GET", "path": "/"}
        request = Request(scope)
        request.state.request_id = "abc-123"
        assert _get_request_id(request) == "abc-123"

    def test_unknown_when_missing(self) -> None:
        scope = {"type": "http", "method": "GET", "path": "/"}
        request = Request(scope)
        assert _get_request_id(request) == "unknown"


class TestAttachRequestId:
    def test_adds_header_when_present(self) -> None:
        from fastapi.responses import JSONResponse

        scope = {"type": "http", "method": "GET", "path": "/"}
        request = Request(scope)
        request.state.request_id = "req-hdr"
        resp = JSONResponse(status_code=400, content={})
        _attach_request_id(request, resp)
        assert resp.headers["X-Request-ID"] == "req-hdr"

    def test_skips_when_unknown(self) -> None:
        from fastapi.responses import JSONResponse

        scope = {"type": "http", "method": "GET", "path": "/"}
        request = Request(scope)
        resp = JSONResponse(status_code=400, content={})
        _attach_request_id(request, resp)
        assert "X-Request-ID" not in resp.headers


# --- Async handlers ---


@pytest.mark.asyncio
class TestHandlers:
    async def test_domain_exception_handler(self) -> None:
        scope = {"type": "http", "method": "GET", "path": "/"}
        request = Request(scope)
        exc = DomainException("bad request", status_code=400, error_code="BAD")
        resp = await domain_exception_handler(request, exc)
        assert resp.status_code == 400
        body = resp.body.decode()
        assert "bad request" in body

    async def test_status_transition_handler(self) -> None:
        scope = {"type": "http", "method": "GET", "path": "/"}
        request = Request(scope)
        exc = InvalidStatusTransitionError("from draft to published")
        resp = await status_transition_handler(request, exc)
        assert resp.status_code == 409

    async def test_request_validation_handler(self) -> None:
        scope = {"type": "http", "method": "POST", "path": "/"}
        request = Request(scope)
        from fastapi.exceptions import RequestValidationError
        from pydantic import BaseModel, ValidationError

        # Build a minimal validation error
        class TestModel(BaseModel):
            name: str

        try:
            TestModel(name=None)  # type: ignore[arg-type]
        except Exception:
            # fallback: create a minimal validation error manually
            exc = RequestValidationError(errors=[])
            resp = await request_validation_handler(request, exc)
            assert resp.status_code == 422
            body = resp.body.decode()
            assert "validation" in body.lower()

    async def test_http_exception_handler(self) -> None:
        scope = {"type": "http", "method": "GET", "path": "/"}
        request = Request(scope)
        exc = StarletteHTTPException(status_code=401, detail="Unauthorized")
        resp = await http_exception_handler(request, exc)
        assert resp.status_code == 401
        body = resp.body.decode()
        assert "Unauthorized" in body

    async def test_generic_exception_handler(self) -> None:
        scope = {"type": "http", "method": "GET", "path": "/"}
        request = Request(scope)
        exc = ValueError("unexpected error")
        resp = await generic_exception_handler(request, exc)
        assert resp.status_code == 500
        body = resp.body.decode()
        assert "Internal server error" in body
