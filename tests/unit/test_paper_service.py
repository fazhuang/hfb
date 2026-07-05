"""Integration tests for PaperService — 8-module paper generation."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.paper_service import PaperService


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_paper_empty_graph(db_session):
    """Paper generation with no academic edges should return empty chains."""
    svc = PaperService(db_session)
    paper = await svc.generate_paper(
        source_type="person", source_id="nonexistent",
        target_type="book", target_id="nonexistent",
    )
    assert paper["paper_id"] is not None
    assert len(paper["paper_id"]) == 64  # SHA-256 hex
    assert "modules" in paper
    assert "markdown" in paper
    modules = paper["modules"]
    assert "title" in modules
    assert "abstract" in modules
    assert modules["abstract"]["path_count"] == 0


@pytest.mark.asyncio
async def test_generate_paper_produces_markdown(db_session):
    """Paper generation should produce well-formed Markdown."""
    svc = PaperService(db_session)
    paper = await svc.generate_paper(
        source_type="person", source_id="p1",
    )
    md = paper["markdown"]
    assert md.startswith("# ")
    assert "## 摘要" in md
    assert "## 证据链" in md
    assert "## 讨论与冲突检测" in md
    assert "## 方法论附注" in md


@pytest.mark.asyncio
async def test_generate_paper_deterministic(db_session):
    """Same inputs should produce the same paper_id (SHA-256)."""
    svc1 = PaperService(db_session)
    svc2 = PaperService(db_session)
    paper1 = await svc1.generate_paper(
        source_type="person", source_id="p1",
        target_type="book", target_id="b1",
    )
    paper2 = await svc2.generate_paper(
        source_type="person", source_id="p1",
        target_type="book", target_id="b1",
    )
    assert paper1["paper_id"] == paper2["paper_id"]
