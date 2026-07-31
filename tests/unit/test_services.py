"""
Tests for the service layer validation hooks (Sprint 3 scope).
"""

import pytest
from app.schemas.document import DocumentCreate
from app.schemas.person import PersonCreate
from app.services.document_service import DocumentService
from app.services.person_service import PersonService
from sqlalchemy.ext.asyncio import AsyncSession

# conftest_db.py fixtures must be imported — not auto-discovered by pytest
from tests.conftest_db import db_session  # noqa: F401


class TestDocumentService:
    """Test DocumentService validation."""

    @pytest.mark.asyncio
    async def test_create_valid(self, db_session: AsyncSession):
        svc = DocumentService(db_session)
        doc = await svc.create(DocumentCreate(title="针灸甲乙经", language="zh"))
        assert doc.title == "针灸甲乙经"

    @pytest.mark.asyncio
    async def test_create_empty_title_raises(self, db_session: AsyncSession):
        svc = DocumentService(db_session)
        with pytest.raises(ValueError, match="title"):
            await svc.create(DocumentCreate(title=""))

    @pytest.mark.asyncio
    async def test_soft_delete(self, db_session: AsyncSession):
        svc = DocumentService(db_session)
        doc = await svc.create(DocumentCreate(title="Test Doc", language="zh"))
        ok = await svc.soft_delete(doc.id)
        assert ok is True


class TestPersonService:
    """Test PersonService validation."""

    @pytest.mark.asyncio
    async def test_create_empty_name_raises(self, db_session: AsyncSession):
        svc = PersonService(db_session)
        with pytest.raises(ValueError, match="name"):
            await svc.create(PersonCreate(name=""))
