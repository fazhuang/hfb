"""
Tests for AI and Workspace services.

Per HFB-PS-1705 AI Research Workspace Product Specification.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.person import Person
from app.models.book import Book
from app.services.ai_service import AIService, RateLimiter
from app.services.rag_service import RAGService
from app.services.workspace_service import WorkspaceService

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401


# ============================================================
# Rate Limiter
# ============================================================


class TestRateLimiter:
    def test_allows_requests_up_to_limit(self) -> None:
        rl = RateLimiter(max_per_minute=5)
        for _ in range(5):
            assert rl.allow() is True

    def test_denies_over_limit(self) -> None:
        rl = RateLimiter(max_per_minute=3)
        for _ in range(3):
            assert rl.allow() is True
        assert rl.allow() is False

    def test_remaining(self) -> None:
        rl = RateLimiter(max_per_minute=5)
        assert rl.remaining == 5
        rl.allow()
        assert rl.remaining == 4


# ============================================================
# AIService (mock mode — no API key)
# ============================================================


class TestAIService:
    def test_available_false_by_default(self) -> None:
        svc = AIService()
        assert svc.available is False  # No API key in test

    def test_rate_limit_available(self) -> None:
        svc = AIService()
        assert svc.check_rate_limit() is True

    @pytest.mark.asyncio
    async def test_summarize_mock(self) -> None:
        svc = AIService()
        result = await svc.summarize("针灸甲乙经是皇甫谧编撰的经典著作。", max_words=30)
        assert "摘要" in result or "AI" in result
        assert "针灸" in result

    @pytest.mark.asyncio
    async def test_translate_mock(self) -> None:
        svc = AIService()
        result = await svc.translate("凡刺之法，必候日月星辰。", target_lang="现代汉语")
        assert "翻译" in result or "AI" in result

    @pytest.mark.asyncio
    async def test_compare_mock(self) -> None:
        svc = AIService()
        result = await svc.ai_compare("凡刺之法", "凡刺之要", "源版本", "目标版本")
        assert "相似度" in result or "差异" in result


# ============================================================
# Workspace Service
# ============================================================


@pytest.mark.asyncio
class TestWorkspaceService:
    async def test_create_and_get_session(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-1",
            username="test_user_1",
            email="user-1@test.com",
            hashed_password="test-hash-1",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-1", "测试研究会话")
        assert s.id is not None
        assert s.title == "测试研究会话"

        got = await svc.get_session(s.id)
        assert got is not None
        assert got.title == "测试研究会话"

    async def test_list_sessions(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-2",
            username="test_user_2",
            email="user-2@test.com",
            hashed_password="test-hash-2",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        await svc.create_session("user-2", "研究1")
        await svc.create_session("user-2", "研究2")

        sessions = await svc.list_sessions("user-2")
        assert len(sessions) >= 2

    async def test_update_session(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-3",
            username="test_user_3",
            email="user-3@test.com",
            hashed_password="test-hash-3",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-3", "原标题")

        updated = await svc.update_session(
            s.id, title="新标题", active_entities=["b1", "p2"]
        )
        assert updated is not None
        assert updated.title == "新标题"

    async def test_delete_session(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-4",
            username="test_user_4",
            email="user-4@test.com",
            hashed_password="test-hash-4",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-4", "待删除")

        ok = await svc.delete_session(s.id)
        assert ok is True
        assert await svc.get_session(s.id) is None

    async def test_chat_history(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-5",
            username="test_user_5",
            email="user-5@test.com",
            hashed_password="test-hash-5",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-5", "聊天测试")

        await svc.append_chat_message(s.id, "user", "什么是针灸？")
        await svc.append_chat_message(s.id, "assistant", "针灸是一种中医治疗方法...")

        history = await svc.get_chat_history(s.id)
        assert len(history) >= 2
        assert history[0]["role"] == "user"
        assert "针灸" in history[0]["content"]

    async def test_create_and_list_notes(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-6",
            username="test_user_6",
            email="user-6@test.com",
            hashed_password="test-hash-6",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-6", "笔记测试")

        await svc.create_note(s.id, "这是一条测试笔记", entity_type="book", tags="重要")
        await svc.create_note(s.id, "另一条笔记", entity_type="passage")

        notes = await svc.list_notes(s.id)
        assert len(notes) >= 2

    async def test_update_note(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-7",
            username="test_user_7",
            email="user-7@test.com",
            hashed_password="test-hash-7",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-7", "更新笔记测试")
        n = await svc.create_note(s.id, "原始内容")

        updated = await svc.update_note(n.id, content="更新后内容")
        assert updated is not None
        assert updated.content == "更新后内容"

    async def test_delete_note(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-8",
            username="test_user_8",
            email="user-8@test.com",
            hashed_password="test-hash-8",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-8", "删除笔记测试")
        n = await svc.create_note(s.id, "待删除笔记")

        ok = await svc.delete_note(n.id)
        assert ok is True

        notes = await svc.list_notes(s.id)
        assert not any(x.id == n.id for x in notes)


# ============================================================
# RAG Service
# ============================================================


@pytest.mark.asyncio
class TestRAGService:
    async def test_retrieve_empty(self, db_session: AsyncSession) -> None:
        svc = RAGService(db_session)
        chunks = await svc.retrieve("nonexistent_xyz_query", top_k=3)
        assert len(chunks) == 0

    async def test_assemble_context_empty(self, db_session: AsyncSession) -> None:
        svc = RAGService(db_session)
        ctx = await svc.assemble_context("nonexistent_xyz_query")
        assert ctx == ""

    async def test_retrieve_with_data(self, db_session: AsyncSession) -> None:
        p = Person(name="扁鹊", dynasty="春秋", biography="扁鹊是春秋时期著名医学家。")
        db_session.add(p)
        await db_session.flush()

        b = Book(title="难经", dynasty="春秋", abstract="《难经》相传为扁鹊所著。")
        db_session.add(b)
        await db_session.flush()

        svc = RAGService(db_session)
        chunks = await svc.retrieve("扁鹊", entity_types=["person", "book"], top_k=3)
        assert len(chunks) >= 1
        # Should find either person or book about 扁鹊
        assert any("扁鹊" in str(c.get("content", "")) for c in chunks)

    async def test_assemble_context_with_data(self, db_session: AsyncSession) -> None:
        p = Person(name="王叔和", dynasty="西晋", biography="王叔和编次《伤寒论》。")
        db_session.add(p)
        await db_session.flush()

        svc = RAGService(db_session)
        ctx = await svc.assemble_context("王叔和", top_k=2)
        assert len(ctx) > 0
        assert "王叔和" in ctx
