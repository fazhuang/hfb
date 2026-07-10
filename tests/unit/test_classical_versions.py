"""
Tests for ClassicalVersion model, schemas, validation, CRUD, and route-level soft-delete.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from main import app as fastapi_app
from app.models.classical_version import ClassicalVersion
from app.db.base import BaseModel
from app.schemas.classical_version import (
    ClassicalVersionCreate,
    ClassicalVersionUpdate,
    ClassicalVersionBrief,
)

from tests.conftest_db import db_session  # noqa: F401

pytestmark = pytest.mark.anyio


# ============================================================
# Helpers
# ============================================================


def _auth_headers(user_id: str = "test-user-1") -> dict:
    """Create a valid JWT for the given user_id."""
    from app.services.auth_service import create_access_token
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


async def _seed_user_with_perms(session, user_id, username, permission_codes, is_superuser=False):
    from app.models.user import User, Role, Permission
    from app.models.user import user_role, role_permission

    user = User(
        id=user_id, username=username, email=f"{username}@test.com",
        hashed_password="pw", is_active=True, is_superuser=is_superuser,
    )
    session.add(user)
    role = Role(id=f"role-{username}", name=username, description=f"Test {username}")
    session.add(role)
    await session.flush()
    await session.execute(user_role.insert().values(user_id=user_id, role_id=role.id))
    for code in permission_codes:
        resource, action = code.split(".", 1)
        perm = Permission(id=f"perm-{code}-{username}", resource=resource, action=action, description=code)
        session.add(perm)
        await session.flush()
        await session.execute(role_permission.insert().values(role_id=role.id, permission_id=perm.id))
    await session.flush()


@pytest.fixture
def client():
    transport = ASGITransport(app=fastapi_app)
    return AsyncClient(transport=transport, base_url="http://test")


# ============================================================
# Model
# ============================================================


class TestClassicalVersionModel:
    def test_tablename(self):
        assert ClassicalVersion.__tablename__ == "classical_versions"

    def test_inherits_base_model(self):
        assert issubclass(ClassicalVersion, BaseModel)

    def test_has_expected_columns(self):
        cols = {c.name for c in ClassicalVersion.__table__.columns}
        expected = {
            "id", "created_at", "updated_at", "deleted_at", "is_deleted",
            "work_title", "version_name", "dynasty", "edition_type",
            "volume_count", "repository", "source_url", "image_url",
            "public_domain_status", "ocr_text_available",
            "citation_note", "academic_note", "review_status",
        }
        assert expected.issubset(cols)


# ============================================================
# Schemas
# ============================================================


class TestClassicalVersionSchemas:
    def test_create_minimal_valid(self):
        data = ClassicalVersionCreate(
            work_title="针灸甲乙经",
            version_name="明嘉靖刻本",
            source_url="https://example.com/edition/1",
            public_domain_status="unknown",
        )
        assert data.public_domain_status == "unknown"

    def test_create_missing_public_domain_status_fails(self):
        with pytest.raises(ValueError):
            ClassicalVersionCreate(work_title="x", version_name="y", source_url="http://z")

    def test_create_missing_source_url_fails(self):
        with pytest.raises(ValueError):
            ClassicalVersionCreate(
                work_title="x", version_name="y",
                public_domain_status="unknown",
            )

    def test_create_full(self):
        data = ClassicalVersionCreate(
            work_title="针灸甲乙经",
            version_name="宋刻本",
            dynasty="宋",
            edition_type="刻本",
            volume_count=12,
            repository="国家图书馆",
            source_url="https://example.com/2",
            image_url="https://example.com/images/2",
            public_domain_status="confirmed_public_domain",
            ocr_text_available=True,
            citation_note="据《中国古籍总目》著录",
            academic_note="此本为现存最早刻本",
            review_status="approved",
        )
        assert data.volume_count == 12
        assert data.public_domain_status == "confirmed_public_domain"

    def test_update_partial(self):
        data = ClassicalVersionUpdate(review_status="approved")
        assert data.review_status == "approved"
        assert data.work_title is None

    def test_brief_from_attributes(self):
        import uuid
        from datetime import datetime, timezone

        cv = ClassicalVersion(
            id=str(uuid.uuid4()),
            work_title="针灸甲乙经",
            version_name="清抄本",
            dynasty="清",
            edition_type="抄本",
            repository="上海图书馆",
            public_domain_status="confirmed_public_domain",
            review_status="approved",
            created_at=datetime.now(timezone.utc),
        )
        brief = ClassicalVersionBrief.model_validate(cv)
        assert brief.work_title == "针灸甲乙经"
        assert brief.id is not None


# ============================================================
# Service validation
# ============================================================


class TestClassicalVersionValidation:
    @pytest.fixture
    def service(self, db_session):
        from app.api.v1.classical_versions import ClassicalVersionService
        return ClassicalVersionService(db_session)

    async def test_rejects_bad_pd_status(self, service):
        with pytest.raises(ValueError, match="public_domain_status"):
            await service._validate_create({
                "work_title": "x",
                "version_name": "y",
                "source_url": "http://z",
                "public_domain_status": "nonsense",
            })

    async def test_rejects_bad_review_status(self, service):
        with pytest.raises(ValueError, match="review_status"):
            await service._validate_create({
                "work_title": "x",
                "version_name": "y",
                "source_url": "http://z",
                "public_domain_status": "unknown",
                "review_status": "nonsense",
            })

    async def test_rejects_bad_edition_type(self, service):
        with pytest.raises(ValueError, match="edition_type"):
            await service._validate_create({
                "work_title": "x",
                "version_name": "y",
                "source_url": "http://z",
                "public_domain_status": "unknown",
                "edition_type": "nonsense",
            })

    async def test_rejects_missing_source_url(self, service):
        with pytest.raises(ValueError, match="source_url"):
            await service._validate_create({
                "work_title": "x", "version_name": "y",
                "public_domain_status": "unknown",
            })

    async def test_ok(self, service):
        await service._validate_create({
            "work_title": "针灸甲乙经",
            "version_name": "明刻本",
            "source_url": "https://example.com",
            "public_domain_status": "unknown",
            "review_status": "pending_review",
        })


# ============================================================
# CRUD via service (DB integration)
# ============================================================


class TestClassicalVersionCRUD:
    @pytest.fixture
    def service(self, db_session):
        from app.api.v1.classical_versions import ClassicalVersionService
        return ClassicalVersionService(db_session)

    async def test_create_and_get(self, service):
        obj = await service.create(ClassicalVersionCreate(
            work_title="针灸甲乙经",
            version_name="明嘉靖刻本",
            dynasty="明",
            edition_type="刻本",
            volume_count=12,
            repository="国家图书馆",
            source_url="https://example.com/edition/1",
            public_domain_status="confirmed_public_domain",
            review_status="pending_review",
        ))
        assert obj.id is not None
        assert obj.work_title == "针灸甲乙经"

        fetched = await service.get_by_id(obj.id)
        assert fetched is not None
        assert fetched.version_name == "明嘉靖刻本"

    async def test_update(self, service):
        obj = await service.create(ClassicalVersionCreate(
            work_title="针灸甲乙经",
            version_name="清刻本",
            source_url="https://example.com/edition/2",
            public_domain_status="unknown",
        ))
        updated = await service.repo.update(obj.id, review_status="approved", dynasty="清")
        assert updated is not None
        assert updated.review_status == "approved"

    async def test_soft_delete(self, service):
        obj = await service.create(ClassicalVersionCreate(
            work_title="针灸甲乙经",
            version_name="待删除版本",
            source_url="https://example.com/edition/3",
            public_domain_status="unknown",
        ))
        assert await service.soft_delete(obj.id) is True
        assert await service.get_by_id(obj.id) is None

    async def test_list_pagination(self, service):
        for i in range(5):
            await service.create(ClassicalVersionCreate(
                work_title=f"work-{i}",
                version_name=f"v{i}",
                source_url=f"https://example.com/{i}",
                public_domain_status="unknown",
            ))
        items, total = await service.list(page=1, limit=3)
        assert len(items) == 3
        assert total == 5

    async def test_search(self, service):
        await service.create(ClassicalVersionCreate(
            work_title="针灸甲乙经",
            version_name="宋刻本",
            source_url="https://example.com/song",
            public_domain_status="unknown",
        ))
        await service.create(ClassicalVersionCreate(
            work_title="伤寒论",
            version_name="明刻本",
            source_url="https://example.com/ming",
            public_domain_status="unknown",
        ))
        items, total = await service.search("甲乙经")
        assert total == 1
        assert items[0].work_title == "针灸甲乙经"


# ============================================================
# Route: DELETE → soft-delete (blocking fix)
# ============================================================


class TestClassicalVersionDeleteIsSoftDelete:
    """DELETE /api/admin/classical-versions/{id} must soft-delete, not hard-delete."""

    async def test_superuser_delete_is_soft_delete(self, db_session):
        from app.middleware import auth as auth_mod
        from app.db.database import get_session
        from app.services.auth_service import AuthService
        from app.services.auth_service import decode_token, create_access_token

        # Seed
        from app.api.v1.classical_versions import ClassicalVersionService
        svc = ClassicalVersionService(db_session)
        obj = await svc.create(ClassicalVersionCreate(
            work_title="针灸甲乙经",
            version_name="测试软删除",
            source_url="https://example.com/del-test",
            public_domain_status="unknown",
        ))
        created_id = obj.id

        # Set up overrides: wire db_session + auth
        token = create_access_token("test-user-1")

        async def _get_session():
            yield db_session

        async def _get_current_user(request=None):
            return decode_token(token)["sub"]

        async def _get_auth_service():
            svc = AuthService(db_session)

            class _A:
                def __init__(self):
                    self.session = db_session

                async def has_permission(self, uid, r, a):
                    return await svc.has_permission(uid, r, a)

                async def has_any_permission(self, uid, *p):
                    return await svc.has_any_permission(uid, *p)

            return _A()

        fastapi_app.dependency_overrides[get_session] = _get_session
        fastapi_app.dependency_overrides[auth_mod.get_current_user] = _get_current_user
        fastapi_app.dependency_overrides[auth_mod.get_auth_service] = _get_auth_service
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(
                    f"/api/admin/classical-versions/{created_id}",
                    headers=_auth_headers("test-user-1"),
                )
                assert response.status_code == 200
        finally:
            fastapi_app.dependency_overrides.clear()

        # Row still exists in DB
        stmt = select(ClassicalVersion).where(ClassicalVersion.id == created_id)
        result = await svc.session.execute(stmt)
        row = result.scalar_one_or_none()
        assert row is not None, "row must still exist after soft-delete"
        assert row.is_deleted is True, "is_deleted must be True"
        assert row.deleted_at is not None, "deleted_at must be set"

        # Not visible through normal reads
        fetched = await svc.get_by_id(created_id)
        assert fetched is None, "soft-deleted row must not be visible via get_by_id"

        items, total = await svc.list()
        assert total == 0, "soft-deleted row must not appear in list"


# ============================================================
# Route: missing public_domain_status → 422 (non-blocking fix)
# ============================================================


class TestClassicalVersionPublicDomainRequired:
    """public_domain_status is required — no default."""

    async def test_missing_public_domain_status_422(self, db_session):
        from app.middleware import auth as auth_mod
        from app.db.database import get_session
        from app.services.auth_service import AuthService
        from app.services.auth_service import decode_token, create_access_token

        token = create_access_token("test-user-1")

        async def _get_session():
            yield db_session

        async def _get_current_user(request=None):
            return decode_token(token)["sub"]

        async def _get_auth_service():
            svc = AuthService(db_session)

            class _A:
                def __init__(self):
                    self.session = db_session

                async def has_permission(self, uid, r, a):
                    return await svc.has_permission(uid, r, a)

                async def has_any_permission(self, uid, *p):
                    return await svc.has_any_permission(uid, *p)

            return _A()

        fastapi_app.dependency_overrides[get_session] = _get_session
        fastapi_app.dependency_overrides[auth_mod.get_current_user] = _get_current_user
        fastapi_app.dependency_overrides[auth_mod.get_auth_service] = _get_auth_service
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/admin/classical-versions",
                    headers=_auth_headers(),
                    json={
                        "work_title": "针灸甲乙经",
                        "version_name": "明刻本",
                        "source_url": "https://example.com/ming",
                    },
                )
                assert response.status_code == 422
        finally:
            fastapi_app.dependency_overrides.clear()
