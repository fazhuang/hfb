"""
Tests for app/middleware/logging.py -- RequestLoggingMiddleware.
Covers lines 5-35: logger creation, dispatch with timing and log call.
Uses httpx.ASGITransport (TestClient blocked by httpx2 deprecation).
"""

from __future__ import annotations

import logging
import re

import pytest
from app.middleware.logging import RequestLoggingMiddleware
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.anyio


def _make_logging_app():
    """Minimal FastAPI app with RequestLoggingMiddleware only."""
    app = FastAPI(debug=False)
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/error")
    async def error():
        raise RuntimeError("test-error")

    return app


class TestRequestLoggingMiddleware:
    """Coverage for logging middleware lines 5-35."""

    def test_logger_created(self):
        """Line 15: get_logger creates a logger with correct name."""
        from app.middleware.logging import logger as logging_logger

        assert logging_logger is not None
        assert isinstance(logging_logger, logging.Logger)
        assert logging_logger.name == "app.middleware.logging"

    async def test_logs_request_completed_on_success(self, caplog):
        """Lines 21-35: dispatch logs method, path, status, duration."""
        app = _make_logging_app()
        caplog.set_level(logging.INFO, logger="app.middleware.logging")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ok")
            assert resp.status_code == 200

        records = [
            r
            for r in caplog.records
            if r.name == "app.middleware.logging" and "request_completed" in r.message
        ]
        assert len(records) == 1
        msg = records[0].message
        assert "method=GET" in msg
        assert "path=/ok" in msg
        assert "status=200" in msg
        assert "duration_ms=" in msg

    async def test_error_returns_500_without_completed_log(self, caplog):
        """Error path: exception propagates before logger.info runs, so
        no 'request_completed' is logged. ASGITransport returns 500."""
        app = _make_logging_app()
        caplog.set_level(logging.INFO, logger="app.middleware.logging")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/error")
            assert resp.status_code == 500

        records = [
            r
            for r in caplog.records
            if r.name == "app.middleware.logging" and "request_completed" in r.message
        ]
        # dispatch propagates the exception before reaching logger.info,
        # so request_completed is never logged for unhandled errors.
        assert len(records) == 0

    async def test_duration_is_positive(self, caplog):
        """The duration_ms field is a non-negative float."""
        app = _make_logging_app()
        caplog.set_level(logging.INFO, logger="app.middleware.logging")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/ok")

        records = [
            r
            for r in caplog.records
            if r.name == "app.middleware.logging" and "request_completed" in r.message
        ]
        assert len(records) == 1
        msg = records[0].message

        m = re.search(r"duration_ms=(\d+\.?\d*)", msg)
        assert m is not None
        duration = float(m.group(1))
        assert duration >= 0.0

    async def test_log_message_includes_method_post(self, caplog):
        """POST method is correctly logged. The test route only accepts GET so
        we get status=405, but method=POST is logged correctly."""
        app = _make_logging_app()
        caplog.set_level(logging.INFO, logger="app.middleware.logging")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/ok", json={"data": "test"})

        records = [
            r
            for r in caplog.records
            if r.name == "app.middleware.logging" and "request_completed" in r.message
        ]
        assert len(records) == 1
        msg = records[0].message
        assert "method=POST" in msg
        assert "path=/ok" in msg
        assert "status=405" in msg
        assert "duration_ms=" in msg

    def test_middleware_is_base_http_middleware(self):
        """Line 18: RequestLoggingMiddleware extends BaseHTTPMiddleware."""
        from starlette.middleware.base import BaseHTTPMiddleware

        mw = RequestLoggingMiddleware(None)
        assert isinstance(mw, BaseHTTPMiddleware)
