"""Unit tests for BaseService CRUD methods."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.base import BaseService


class FakeRepo:
    def __init__(self, session):
        self.session = session
        self.create = AsyncMock()
        self.update = AsyncMock()
        self.soft_delete = AsyncMock(return_value=True)
        self.hard_delete = AsyncMock(return_value=True)


class FakeSchema:
    def model_dump(self, exclude_unset=True):
        return {"key": "val"}


class ConcreteService(BaseService[FakeRepo, FakeSchema, FakeSchema]):
    repository_class = FakeRepo


@pytest.fixture
def svc():
    session = MagicMock()
    return ConcreteService(session)


@pytest.mark.asyncio
async def test_validate_create_does_not_raise(svc):
    await svc._validate_create({})  # no-op, must not raise


@pytest.mark.asyncio
async def test_validate_update_does_not_raise(svc):
    await svc._validate_update(uuid4(), {})  # no-op, must not raise


@pytest.mark.asyncio
async def test_create_calls_validate_then_repo_create(svc):
    schema = FakeSchema()
    result = await svc.create(schema)

    svc.repo.create.assert_awaited_once_with(key="val")
    assert result is svc.repo.create.return_value


@pytest.mark.asyncio
async def test_update_calls_validate_then_repo_update(svc):
    schema = FakeSchema()
    uid = uuid4()
    result = await svc.update(uid, schema)

    svc.repo.update.assert_awaited_once_with(uid, key="val")
    assert result is svc.repo.update.return_value


@pytest.mark.asyncio
async def test_hard_delete_delegates(svc):
    uid = uuid4()
    result = await svc.hard_delete(uid)

    svc.repo.hard_delete.assert_awaited_once_with(uid)
    assert result is True


@pytest.mark.asyncio
async def test_soft_delete_delegates(svc):
    uid = uuid4()
    result = await svc.soft_delete(uid)

    svc.repo.soft_delete.assert_awaited_once_with(uid)
    assert result is True
