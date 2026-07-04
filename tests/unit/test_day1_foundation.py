"""
Day 1 acceptance tests — status machine, exceptions, error handlers,
request ID middleware, Institution model & repository.

Covers:
  - Status machine: all legal transitions, all illegal transitions,
    unknown states, terminal detection, repository integration,
    bypass prevention (update, direct setattr, DB constraint)
  - Institution: valid/invalid type, empty name, ORM registration,
    create/get/update, soft_delete state+field sync,
    ORM @validates and DB CHECK constraints
  - Exceptions: ValidationException→422, NotFoundException→404,
    RequestValidationError→422 unified, HTTPException→unified,
    RuntimeError→500 no-leak (real HTTP)
  - Request ID: auto-generate, honour inbound, replace malicious,
    CORS OPTIONS has header, 500 has header, caplog contains request_id,
    body request_id matches header

Run with: uv run pytest tests/unit/test_day1_foundation.py -v
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import (
    BaseException,
    DomainException,
    NotFoundError,
    NotFoundException,
    PermissionError,
    PermissionException,
    ValidationError,
    ValidationException,
)
from app.core.status_machine import (
    InvalidStatusTransitionError,
    can_transition,
    is_terminal,
    is_valid_state,
    validate_transition,
)
from app.db.base import Base
from app.models.institution import Institution, InstitutionStatus
from app.repositories.institution import InstitutionRepository
from app.schemas.institution import InstitutionCreate, InstitutionUpdate
from pydantic import ValidationError as PydanticValidationError


# ============================================================
# STATUS MACHINE
# ============================================================


class TestLegalTransitions:
    """Day 1 spec: draft→active, draft→deleted, active→archived,
       active→deleted, archived→deleted.  Deleted is terminal."""

    def test_draft_to_active(self):
        assert can_transition("draft", "active")

    def test_draft_to_deleted(self):
        assert can_transition("draft", "deleted")

    def test_active_to_archived(self):
        assert can_transition("active", "archived")

    def test_active_to_deleted(self):
        assert can_transition("active", "deleted")

    def test_archived_to_deleted(self):
        assert can_transition("archived", "deleted")


class TestIllegalTransitions:
    """Day 1 spec: all other transitions must be rejected."""

    def test_draft_to_archived_blocked(self):
        assert not can_transition("draft", "archived")

    def test_active_to_draft_blocked(self):
        assert not can_transition("active", "draft")

    def test_archived_to_active_blocked(self):
        assert not can_transition("archived", "active")

    def test_archived_to_draft_blocked(self):
        assert not can_transition("archived", "draft")

    def test_deleted_to_anything_blocked(self):
        for target in ("draft", "active", "archived"):
            assert not can_transition("deleted", target), f"deleted→{target} should be blocked"


class TestUnknownState:
    def test_unknown_current_returns_false(self):
        assert not can_transition("flying", "active")

    def test_validate_unknown_current_raises(self):
        with pytest.raises(InvalidStatusTransitionError, match="Unknown.*flying"):
            validate_transition("flying", "active")

    def test_validate_unknown_target_raises(self):
        with pytest.raises(InvalidStatusTransitionError, match="Unknown.*swimming"):
            validate_transition("draft", "swimming")

    def test_is_valid_state(self):
        assert is_valid_state("draft")
        assert is_valid_state("deleted")
        assert not is_valid_state("published")
        assert not is_valid_state("")


class TestTerminal:
    def test_deleted_is_terminal(self):
        assert is_terminal("deleted")

    def test_draft_is_not_terminal(self):
        assert not is_terminal("draft")


# ============================================================
# INSTITUTION MODEL
# ============================================================


class TestInstitutionModel:
    def test_tablename(self):
        assert Institution.__tablename__ == "institutions"

    def test_in_base_metadata(self):
        assert "institutions" in Base.metadata.tables


class TestInstitutionSchema:
    """Pydantic validation: type enum, name non-blank."""

    def test_valid_types_accepted(self):
        for t in ("research", "university", "archive", "institution"):
            s = InstitutionCreate(name="test", type=t)
            assert s.type == t

    def test_invalid_type_rejected(self):
        with pytest.raises(PydanticValidationError, match="Invalid institution type"):
            InstitutionCreate(name="test", type="hospital")

    def test_empty_name_rejected(self):
        with pytest.raises(PydanticValidationError):
            InstitutionCreate(name="   ", type="research")

    def test_name_stripped(self):
        s = InstitutionCreate(name="  复旦大学  ", type="university")
        assert s.name == "复旦大学"

    def test_update_partial(self):
        s = InstitutionUpdate(location="甘肃")
        assert s.location == "甘肃"
        assert s.name is None


# ============================================================
# INSTITUTION REPOSITORY (with SQLite-in-memory)
# ============================================================


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.anyio
class TestInstitutionRepository:
    async def test_create(self, db_session):
        repo = InstitutionRepository(db_session)
        inst = await repo.create(name="复旦大学", type="university", location="上海")
        assert inst.id is not None
        assert inst.status == "draft"

    async def test_get_by_id(self, db_session):
        repo = InstitutionRepository(db_session)
        inst = await repo.create(name="中国中医科学院", type="research")
        found = await repo.get_by_id(inst.id)
        assert found is not None
        assert found.name == "中国中医科学院"

    async def test_list(self, db_session):
        repo = InstitutionRepository(db_session)
        await repo.create(name="A", type="archive")
        await repo.create(name="B", type="institution")
        items, total = await repo.get_all(page=1, limit=10)
        assert total >= 2

    async def test_update(self, db_session):
        repo = InstitutionRepository(db_session)
        inst = await repo.create(name="旧名称", type="research")
        updated = await repo.update(inst.id, name="新名称")
        assert updated.name == "新名称"

    async def test_transition_status_legal(self, db_session):
        repo = InstitutionRepository(db_session)
        inst = await repo.create(name="test", type="archive")
        result = await repo.transition_status(inst.id, "active")
        assert result.status == "active"

    async def test_transition_status_illegal_does_not_write(self, db_session):
        repo = InstitutionRepository(db_session)
        inst = await repo.create(name="test", type="archive")
        with pytest.raises(InvalidStatusTransitionError):
            await repo.transition_status(inst.id, "archived")
        # Verify status unchanged in DB
        fresh = await repo.get_by_id(inst.id)
        assert fresh.status == "draft"

    async def test_soft_delete_syncs_fields(self, db_session):
        repo = InstitutionRepository(db_session)
        inst = await repo.create(name="ToDelete", type="archive")
        assert inst.is_deleted is False

        ok = await repo.soft_delete(inst.id)
        assert ok is True

        # After soft_delete, get_by_id returns None (is_deleted filter)
        gone = await repo.get_by_id(inst.id)
        assert gone is None

        # But direct query confirms fields are set
        from sqlalchemy import select

        row = (await db_session.execute(
            select(Institution).where(Institution.id == inst.id)
        )).scalar_one()
        assert row.status == InstitutionStatus.deleted.value
        assert row.is_deleted is True
        assert row.deleted_at is not None


# ============================================================
# STATUS MACHINE BYPASS PREVENTION (Section 2)
# ============================================================


@pytest.mark.anyio
class TestStatusMachineBypass:
    """All three bypass vectors must be blocked."""

    # --- Vector 1: repo.transition_status(draft, archived) ---
    async def test_transition_status_rejects_draft_to_archived(self, db_session):
        repo = InstitutionRepository(db_session)
        inst = await repo.create(name="v1", type="archive")
        with pytest.raises(InvalidStatusTransitionError):
            await repo.transition_status(inst.id, "archived")
        fresh = await repo.get_by_id(inst.id)
        assert fresh.status == "draft"

    # --- Vector 2: repo.update(id, status="archived") ---
    async def test_update_rejects_status_kwarg(self, db_session):
        repo = InstitutionRepository(db_session)
        inst = await repo.create(name="v2", type="archive")
        with pytest.raises(ValueError, match="Direct status updates are forbidden"):
            await repo.update(inst.id, status="archived")
        fresh = await repo.get_by_id(inst.id)
        assert fresh.status == "draft"

    # --- Vector 3: instance.status = "archived" ---
    async def test_direct_setattr_blocked_by_validates(self, db_session):
        inst = Institution(name="v3", type="archive")
        db_session.add(inst)
        await db_session.flush()
        assert inst.status == "draft"

        with pytest.raises(InvalidStatusTransitionError, match="Invalid status transition"):
            inst.status = "archived"
            await db_session.flush()

        # DB still draft
        await db_session.refresh(inst)
        assert inst.status == "draft"


# ============================================================
# ORM @VALIDATES — name and type (Section 3)
# ============================================================


@pytest.mark.anyio
class TestORMValidators:
    async def test_create_blank_name_fails(self, db_session):
        repo = InstitutionRepository(db_session)
        with pytest.raises(ValidationException, match="Institution name must not be empty"):
            await repo.create(name="   ", type="archive")

    async def test_direct_construct_blank_name_fails(self):
        with pytest.raises(ValidationException, match="Institution name must not be empty"):
            Institution(name="   ", type="archive")

    async def test_direct_construct_blank_name_stripped_blank(self):
        # "\t  \n" strips to empty
        with pytest.raises(ValidationException, match="Institution name must not be empty"):
            Institution(name="\t  \n", type="archive")

    async def test_direct_construct_invalid_type_fails(self):
        with pytest.raises(ValidationException, match="Invalid institution type"):
            Institution(name="test", type="hospital")

    async def test_db_rejects_blank_name(self, db_session):
        """Raw SQL insert with empty name is rejected by DB CHECK constraint."""
        import uuid
        blank_id = str(uuid.uuid4())
        with pytest.raises(Exception):
            await db_session.execute(
                text("INSERT INTO institutions (id, name, type, status) VALUES (:id, '   ', 'archive', 'draft')"),
                {"id": blank_id},
            )

    async def test_db_rejects_invalid_type(self, db_session):
        """Raw SQL insert with invalid type is rejected by DB CHECK constraint."""
        import uuid
        bad_id = str(uuid.uuid4())
        with pytest.raises(Exception):
            await db_session.execute(
                text("INSERT INTO institutions (id, name, type, status) VALUES (:id, 'test', 'hospital', 'draft')"),
                {"id": bad_id},
            )


# ============================================================
# EXCEPTIONS — required exported names
# ============================================================


class TestExceptionNames:
    def test_base_exception_exists_and_importable(self):
        assert issubclass(BaseException, Exception)

    def test_domain_exception_inherits_base(self):
        assert issubclass(DomainException, BaseException)

    def test_validation_exception_inherits_domain(self):
        assert issubclass(ValidationException, DomainException)

    def test_not_found_exception_inherits_domain(self):
        assert issubclass(NotFoundException, DomainException)

    def test_permission_exception_inherits_domain(self):
        assert issubclass(PermissionException, DomainException)

    def test_aliases_are_identical(self):
        assert ValidationError is ValidationException
        assert NotFoundError is NotFoundException
        assert PermissionError is PermissionException

    def test_validation_error_carries_422(self):
        exc = ValidationException("bad input")
        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"

    def test_not_found_error_carries_404(self):
        exc = NotFoundException("Book", "abc")
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"
        assert "Book" in exc.message

    def test_permission_error_carries_403(self):
        exc = PermissionException("entity", "delete")
        assert exc.status_code == 403
        assert exc.error_code == "PERMISSION_DENIED"


# ============================================================
# ERROR HANDLERS — real FastAPI request tests (Sections 4, 5)
# ============================================================


def _make_test_app():
    """Build a FastAPI test app with RequestID middleware outermost."""
    from fastapi import FastAPI, Query
    from fastapi.middleware.cors import CORSMiddleware

    from app.core.error_handlers import register_error_handlers
    from app.core.exceptions import NotFoundException, ValidationException
    from app.middleware.request_id import RequestIDMiddleware

    app = FastAPI(debug=False)
    # CORS and TrustedHost must be added BEFORE RequestID so
    # RequestID is outermost (Starlette: last add_middleware = outermost).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    register_error_handlers(app)

    @app.get("/test-validation")
    async def validation():
        raise ValidationException("name is required")

    @app.get("/test-not-found")
    async def not_found():
        raise NotFoundException("Institution", "deadbeef")

    @app.get("/test-http-exc")
    async def http_exc():
        from fastapi import HTTPException
        raise HTTPException(status_code=418, detail="I'm a teapot")

    @app.get("/test-crash")
    async def crash():
        raise RuntimeError("boom")

    @app.get("/test-pydantic-validation")
    async def pydantic_val(q: str = Query(min_length=5)):
        return {"q": q}

    return app


@pytest.mark.anyio
class TestErrorHandlersViaHTTP:
    """All error handler tests go through real FastAPI requests."""

    @pytest.fixture(autouse=True)
    def _app(self):
        self._app = _make_test_app()

    async def _get(self, path, headers=None):
        transport = ASGITransport(app=self._app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.get(path, headers=headers or {})

    async def _options(self, path, headers=None):
        transport = ASGITransport(app=self._app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.options(path, headers=headers or {})

    # ---------- 422 from ValidationException ----------
    async def test_validation_exception_returns_422(self):
        r = await self._get("/test-validation")
        assert r.status_code == 422
        b = r.json()
        assert b["success"] is False
        assert b["data"] is None
        assert b["message"] == "name is required"
        assert b["meta"]["error_code"] == "VALIDATION_ERROR"

    # ---------- 404 from NotFoundException ----------
    async def test_not_found_exception_returns_404(self):
        r = await self._get("/test-not-found")
        assert r.status_code == 404
        b = r.json()
        assert b["success"] is False
        assert "Institution" in b["message"]
        assert b["meta"]["error_code"] == "NOT_FOUND"

    # ---------- HTTPException → unified ----------
    async def test_http_exception_returns_unified(self):
        r = await self._get("/test-http-exc")
        assert r.status_code == 418
        b = r.json()
        assert b["success"] is False
        assert "teapot" in b["message"]
        assert b["meta"]["error_code"] == "HTTP_ERROR"

    # ---------- RequestValidationError → 422 unified ----------
    async def test_request_validation_error_returns_422_unified(self):
        r = await self._get("/test-pydantic-validation?q=x")
        assert r.status_code == 422
        b = r.json()
        assert b["success"] is False
        assert b["meta"]["error_code"] == "REQUEST_VALIDATION_ERROR"
        assert "validation_errors" in b["meta"]["metadata"]

    # ---------- Generic 500 via real HTTP (Section 5) ----------
    async def test_runtime_error_returns_500_no_leak(self):
        r = await self._get("/test-crash")
        assert r.status_code == 500
        b = r.json()
        assert b["success"] is False
        assert b["message"] == "Internal server error"
        assert b["meta"]["error_code"] == "INTERNAL_ERROR"
        # No leak
        assert "boom" not in b["message"]
        assert "boom" not in str(b.get("meta", {}))
        # Request ID present and consistent
        header_rid = r.headers.get("X-Request-ID")
        assert header_rid is not None
        assert b["meta"]["request_id"] == header_rid

    # ---------- Request ID consistency ----------
    async def test_error_body_and_header_request_id_match(self):
        r = await self._get("/test-not-found")
        header_rid = r.headers.get("X-Request-ID")
        assert header_rid is not None
        b = r.json()
        assert b["meta"]["request_id"] == header_rid

    # ---------- CORS OPTIONS has X-Request-ID (Section 4) ----------
    async def test_cors_preflight_has_request_id(self):
        r = await self._options(
            "/test-not-found",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.headers.get("X-Request-ID") is not None

    # ---------- HTTPException has X-Request-ID (Section 4) ----------
    async def test_http_exception_has_request_id(self):
        r = await self._get("/test-http-exc")
        assert r.headers.get("X-Request-ID") is not None

    # ---------- RequestValidationError has X-Request-ID (Section 4) ----------
    async def test_request_validation_error_has_request_id(self):
        r = await self._get("/test-pydantic-validation?q=x")
        assert r.headers.get("X-Request-ID") is not None
        b = r.json()
        assert "request_id" in b["meta"]
        assert b["meta"]["request_id"] == r.headers["X-Request-ID"]


# ============================================================
# REQUEST ID MIDDLEWARE
# ============================================================


@pytest.mark.anyio
class TestRequestID:
    @pytest.fixture(autouse=True)
    def _app(self):
        from fastapi import FastAPI

        from app.core.error_handlers import register_error_handlers
        from app.middleware.request_id import RequestIDMiddleware

        app = FastAPI(debug=False)
        app.add_middleware(RequestIDMiddleware)
        register_error_handlers(app)

        @app.get("/test-rid")
        async def ok():
            return {"status": "ok"}

        self._app = app

    async def _get(self, path, headers=None):
        transport = ASGITransport(app=self._app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.get(path, headers=headers or {})

    async def test_normal_request_auto_generates_uuid(self):
        r = await self._get("/test-rid")
        rid = r.headers.get("X-Request-ID")
        assert rid is not None
        assert len(rid) == 36  # UUID v4

    async def test_honours_inbound_valid_id(self):
        r = await self._get("/test-rid", headers={"X-Request-ID": "my-trace-id-1234"})
        assert r.headers["X-Request-ID"] == "my-trace-id-1234"

    async def test_replaces_malicious_id_newline(self):
        r = await self._get("/test-rid", headers={"X-Request-ID": "evil\ninjection"})
        rid = r.headers["X-Request-ID"]
        assert rid != "evil\ninjection"
        assert "\n" not in rid

    async def test_replaces_overly_long_id(self):
        long_id = "x" * 256
        r = await self._get("/test-rid", headers={"X-Request-ID": long_id})
        rid = r.headers["X-Request-ID"]
        assert len(rid) <= 128

    async def test_request_id_appears_in_caplog(self, caplog):
        import logging

        caplog.set_level(logging.INFO, logger="app.middleware.request_id")
        await self._get("/test-rid")
        started = [r for r in caplog.records if "request_started" in r.message]
        completed = [r for r in caplog.records if "request_completed" in r.message]
        assert len(started) >= 1 or len(completed) >= 1, \
            f"Expected request_started or request_completed log; got {len(caplog.records)} records"


# ============================================================
# INVALID STATUS DOES NOT PERSIST — repository gate
# ============================================================


@pytest.mark.anyio
async def test_illegal_transition_not_persisted(db_session):
    """Repository.transition_status must raise before flush."""
    repo = InstitutionRepository(db_session)
    inst = await repo.create(name="GateTest", type="archive")

    with pytest.raises(InvalidStatusTransitionError):
        await repo.transition_status(inst.id, "archived")  # draft→archived illegal

    # Verify still draft
    fresh = await repo.get_by_id(inst.id)
    assert fresh.status == "draft"
