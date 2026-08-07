
"""Unit tests for app.core.exceptions — DomainException hierarchy."""

from __future__ import annotations

from app.core.exceptions import (
    ConflictError,
    DomainException,
    NotFoundException,
    PermissionException,
    ValidationException,
)


class TestDomainException:
    def test_defaults(self) -> None:
        exc = DomainException("test message")
        assert exc.message == "test message"
        assert exc.error_code == "DOMAIN_ERROR"
        assert exc.status_code == 400
        assert exc.metadata == {}

    def test_with_metadata(self) -> None:
        exc = DomainException("msg", metadata={"key": "val"})
        assert exc.metadata == {"key": "val"}

    def test_is_exception(self) -> None:
        exc = DomainException("msg")
        assert isinstance(exc, Exception)


class TestValidationException:
    def test_defaults(self) -> None:
        exc = ValidationException("bad input")
        assert exc.message == "bad input"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.status_code == 422

    def test_with_metadata(self) -> None:
        exc = ValidationException("bad", metadata={"field": "name"})
        assert exc.metadata == {"field": "name"}


class TestNotFoundException:
    def test_defaults(self) -> None:
        exc = NotFoundException("Book", "id-1")
        assert exc.message == "Book with id 'id-1' not found"
        assert exc.error_code == "NOT_FOUND"
        assert exc.status_code == 404
        assert exc.metadata["entity_type"] == "Book"
        assert exc.metadata["entity_id"] == "id-1"

    def test_extra_metadata_merged(self) -> None:
        exc = NotFoundException("Person", "p-1", metadata={"extra": True})
        assert exc.metadata["extra"] is True
        assert exc.metadata["entity_type"] == "Person"


class TestPermissionException:
    def test_defaults(self) -> None:
        exc = PermissionException("report", "export")
        assert exc.error_code == "PERMISSION_DENIED"
        assert exc.status_code == 403
        assert exc.metadata["resource"] == "report"
        assert exc.metadata["action"] == "export"

    def test_merged_metadata(self) -> None:
        exc = PermissionException("doc", "delete", metadata={"owner": "u1"})
        assert exc.metadata["owner"] == "u1"
        assert exc.metadata["resource"] == "doc"


class TestConflictError:
    def test_defaults(self) -> None:
        exc = ConflictError("version conflict")
        assert exc.message == "version conflict"
        assert exc.error_code == "CONFLICT"
        assert exc.status_code == 409
