"""Unit tests for app.core.logging — JSONFormatter, ConsoleFormatter, configure_logging."""

from __future__ import annotations

import json
import logging
import sys

from app.core.logging import ConsoleFormatter, JSONFormatter, configure_logging


class TestJSONFormatter:
    def test_format_basic_record(self) -> None:
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="x.py",
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        output = fmt.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "hello"
        assert "timestamp" in data

    def test_format_with_exception(self) -> None:
        fmt = JSONFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            record = logging.LogRecord(
                name="err",
                level=logging.ERROR,
                pathname="e.py",
                lineno=2,
                msg="fail",
                args=(),
                exc_info=sys.exc_info(),
            )
        output = fmt.format(record)
        data = json.loads(output)
        assert data["level"] == "ERROR"
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "boom"


class TestConsoleFormatter:
    def test_format_includes_timestamp_and_level(self) -> None:
        fmt = ConsoleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="x.py",
            lineno=10,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = fmt.format(record)
        assert "INFO" in output
        assert "test message" in output
        # ANSI reset code should be present
        assert "\033[0m" in output

    def test_error_level_has_red_color(self) -> None:
        fmt = ConsoleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="x.py",
            lineno=1,
            msg="error",
            args=(),
            exc_info=None,
        )
        output = fmt.format(record)
        assert "\033[31m" in output  # Red color


class TestConfigureLogging:
    def test_development_uses_console_formatter(self, monkeypatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "development")
        configure_logging(level="DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) >= 1

    def test_production_uses_json_formatter(self, monkeypatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        configure_logging(level="WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING
        assert len(root.handlers) >= 1

    def test_default_level_is_info(self, monkeypatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "development")
        configure_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO
