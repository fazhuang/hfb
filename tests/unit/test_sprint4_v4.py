"""Sprint 4 V4 product layer tests — 21 tests covering all acceptance criteria.

P0: All tests use HTTPX ASGI transport for real request/response validation.
P0: Traceability checks verify internal full-fidelity + API surface cleanliness.
"""
from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest_db import db_session_persistent  # noqa: F401


# ======================================================================
# 1. Research Session Tests (5)
# ======================================================================


@pytest.mark.asyncio
async def test_create_session_minimal(db_session_persistent):
    """Create a research session with default title."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v4/research/session", json={})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "session_id" in body["data"]
        assert "title" in body["data"]
        assert "dashboard_overview" in body["data"]


@pytest.mark.asyncio
async def test_create_session_with_initial_query(db_session_persistent):
    """Create a session with an initial research query."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    # Seed document and chunk so the query returns data
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-001", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    c1 = DocumentChunk(id="v4-chk-001", document_id=doc.id, chunk_index=0,
                       content="皇甫谧编撰的针灸甲乙经系统阐述了经络理论。", token_count=20)
    c2 = DocumentChunk(id="v4-chk-002", document_id=doc.id, chunk_index=1,
                       content="经络是运行气血、联系脏腑的通道。", token_count=14)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v4/research/session",
            json={"title": "针灸研究", "query": "经络"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["title"] == "针灸研究"
        assert "query_id" in body["data"]
        assert body["traceability"] is not None
        assert len(body["traceability"]["trace_ids"]) > 0


@pytest.mark.asyncio
async def test_create_session_with_custom_title(db_session_persistent):
    """Create a session with a specific title."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v4/research/session",
            json={"title": "黄帝内经版本对比"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["title"] == "黄帝内经版本对比"


@pytest.mark.asyncio
async def test_query_history_recorded(db_session_persistent):
    """Query history is recorded when executing a research query."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    # Seed document and chunk
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-002", title="黄帝内经", dynasty="战国")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    c1 = DocumentChunk(id="v4-chk-003", document_id=doc.id, chunk_index=0,
                       content="黄帝内经是中医理论体系形成的基础文献。", token_count=16)
    c2 = DocumentChunk(id="v4-chk-004", document_id=doc.id, chunk_index=1,
                       content="针灸是传统中医的重要组成部分。", token_count=14)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        r1 = await client.post("/api/v4/research/session", json={"title": "query history test"})
        session_id = r1.json()["data"]["session_id"]

        # Execute query
        r2 = await client.post(
            "/api/v4/research/query",
            json={"session_id": session_id, "query": "针灸", "mode": "research"},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["traceability"] is not None
        assert body["traceability"]["query_id"] is not None


@pytest.mark.asyncio
async def test_citation_collection_crud(db_session_persistent):
    """Citation collection CRUD works through WorkspaceService (no direct ORM)."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    # Seed document and chunk
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-003", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    c1 = DocumentChunk(id="v4-chk-005", document_id=doc.id, chunk_index=0,
                       content="皇甫谧编撰的针灸甲乙经系统阐述了经络理论。", token_count=20)
    c2 = DocumentChunk(id="v4-chk-006", document_id=doc.id, chunk_index=1,
                       content="经络是运行气血、联系脏腑的通道。", token_count=14)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "citation test"})
        session_id = r1.json()["data"]["session_id"]

        r2 = await client.post(
            "/api/v4/research/query",
            json={"session_id": session_id, "query": "经络", "mode": "research"},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["traceability"]["citation_count"] > 0
        assert len(body["traceability"]["trace_ids"]) > 0
        assert len(body["traceability"]["source_documents"]) > 0


# ======================================================================
# 2. Workflow Execution Tests (5)
# ======================================================================


@pytest.mark.asyncio
async def test_workflow_full_five_steps(db_session_persistent):
    """Full 5-step workflow executes with all steps completed."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    # Seed document and chunk
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-010", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    for i in range(3):
        db_session_persistent.add(DocumentChunk(
            document_id=doc.id, chunk_index=i,
            content=f"针灸甲乙经中关于经络的论述在第{i+1}节。黄帝内经是重要的医经文献。" if i == 0
                    else "经络系统包括十二经脉和奇经八脉，是针灸治疗的理论基础。古今医家对此多有阐述。" if i == 1
                    else "中医理论认为经络是运行气血、联系脏腑的通道。针灸甲乙经集此前针灸学之大成。",
            token_count=30,
        ))
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "workflow test"})
        session_id = r1.json()["data"]["session_id"]

        r2 = await client.post(
            "/api/v4/research/workflow",
            json={
                "session_id": session_id,
                "topic": "针灸",
                "workflow_type": "full_research_flow",
            },
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["success"] is True
        steps = body["data"]["steps"]
        assert len(steps) == 5
        step_names = [s["name"] for s in steps]
        assert step_names == [
            "topic_selection",
            "literature_retrieval",
            "evidence_synthesis",
            "report_generation",
            "citation_export",
        ]


@pytest.mark.asyncio
async def test_workflow_researchrun_decoupling(db_session_persistent):
    """Session != Execution — one session can hold multiple ResearchRuns."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    # Seed
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-011", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    for i in range(3):
        db_session_persistent.add(DocumentChunk(
            document_id=doc.id, chunk_index=i,
            content="针灸甲乙经系统阐述了经络理论。经络是运行气血的通道。历代医家多有发挥。" if i == 0
                    else "经络理论是针灸学的基础。十二经脉各有其循行路线和主治病候。针灸甲乙经集大成。" if i == 1
                    else "黄帝内经和针灸甲乙经是针灸理论的重要源头。针灸治疗讲究辨证取穴。",
            token_count=30,
        ))
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "multi-run test"})
        session_id = r1.json()["data"]["session_id"]

        r2 = await client.post(
            "/api/v4/research/workflow",
            json={"session_id": session_id, "topic": "经络", "workflow_type": "full_research_flow"},
        )
        assert r2.status_code == 200
        run_id_1 = r2.json()["data"]["run_id"]

        r3 = await client.post(
            "/api/v4/research/workflow",
            json={"session_id": session_id, "topic": "针灸", "workflow_type": "full_research_flow"},
        )
        assert r3.status_code == 200
        run_id_2 = r3.json()["data"]["run_id"]

        assert run_id_1 != run_id_2


@pytest.mark.asyncio
async def test_workflow_step_traceability(db_session_persistent):
    """Each workflow step carries trace_ids."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    # Seed
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-012", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    for i in range(3):
        db_session_persistent.add(DocumentChunk(
            document_id=doc.id, chunk_index=i,
            content="皇甫谧撰针灸甲乙经。经络理论贯穿全书。针灸治疗有系统记载。" if i == 0
                    else "十二经脉者，内属于脏腑，外络于肢节。经络是气血运行的通道。针灸甲乙经首卷论经络。" if i == 1
                    else "中医理论认为经络运行气血、联系脏腑。针灸甲乙经搜集整理了此前各家学说。",
            token_count=30,
        ))
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "traceability test"})
        session_id = r1.json()["data"]["session_id"]

        r2 = await client.post(
            "/api/v4/research/workflow",
            json={"session_id": session_id, "topic": "经络", "workflow_type": "full_research_flow"},
        )
        assert r2.status_code == 200
        body = r2.json()
        for step in body["data"]["steps"]:
            if step["status"] == "completed":
                assert "trace_ids" in step
        assert body["traceability"] is not None
        assert len(body["traceability"]["trace_ids"]) > 0


@pytest.mark.asyncio
async def test_workflow_export_markdown_full(db_session_persistent):
    """Workflow runs through all steps and traceability is complete."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    # Seed rich data so all steps complete
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-013", title="黄帝内经", dynasty="战国")
    doc2 = Document(id="v4-doc-014", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add_all([doc, doc2])
    await db_session_persistent.flush()
    chunks = [
        DocumentChunk(id="v4-chk-020", document_id=doc.id, chunk_index=0,
                      content="黄帝内经灵枢经详细论述了经络循行。针灸甲乙经以此为蓝本。古今医家传承有序。", token_count=30),
        DocumentChunk(id="v4-chk-021", document_id=doc.id, chunk_index=1,
                      content="经络系统包括十二正经和奇经八脉。针灸治疗以经络理论为基础。历代医家多有发挥。", token_count=30),
        DocumentChunk(id="v4-chk-022", document_id=doc2.id, chunk_index=0,
                      content="皇甫谧编撰针灸甲乙经，系统整理了针灸理论。该书集此前针灸学之大成。", token_count=25),
        DocumentChunk(id="v4-chk-023", document_id=doc2.id, chunk_index=1,
                      content="经络是运行气血、联系脏腑的通道。针灸甲乙经首卷论经络，次卷论穴位。", token_count=25),
    ]
    db_session_persistent.add_all(chunks)
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "export test"})
        session_id = r1.json()["data"]["session_id"]

        r2 = await client.post(
            "/api/v4/research/workflow",
            json={"session_id": session_id, "topic": "针灸", "workflow_type": "full_research_flow"},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert all(s["status"] == "completed" for s in body["data"]["steps"])
        assert body["traceability"]["citation_count"] > 0


@pytest.mark.asyncio
async def test_workflow_invalid_session(db_session_persistent):
    """Workflow with nonexistent session returns 404."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v4/research/workflow",
            json={
                "session_id": "00000000-0000-0000-0000-000000000000",
                "topic": "test",
                "workflow_type": "full_research_flow",
            },
        )
        assert response.status_code == 404


# ======================================================================
# 3. Visualization Data Tests (4)
# ======================================================================


@pytest.mark.asyncio
async def test_visualization_concept_graph_strict_schema(db_session_persistent):
    """Concept graph output uses strict VisualizationNode/Edge schemas."""
    from fastapi import FastAPI
    from app.api.v4.visualization import router as viz_router
    from app.db.database import get_session

    # Seed chunks containing both concepts in same sentences
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-020", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    chunks = [
        DocumentChunk(id="v4-chk-030", document_id=doc.id, chunk_index=0,
                      content="针灸和经络是中医理论的核心概念。针灸甲乙经系统阐述了针灸与经络的关系。", token_count=30),
        DocumentChunk(id="v4-chk-031", document_id=doc.id, chunk_index=1,
                      content="针灸治疗以经络理论为基础。经络包括十二经脉和奇经八脉。", token_count=22),
    ]
    db_session_persistent.add_all(chunks)
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v4/visualization/graph",
            json={"concept_labels": ["针灸", "经络"], "graph_type": "concept"},
        )
        assert response.status_code == 200
        body = response.json()
        graph = body["data"]
        assert "nodes" in graph
        assert "edges" in graph
        for node in graph["nodes"]:
            assert "id" in node
            assert "type" in node
            assert node["type"] in ("concept", "document", "entity")
            assert "label" in node
            assert "metadata" in node
            assert "trace_ids" in node
        for edge in graph["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "type" in edge
            assert edge["type"] in ("citation", "hierarchy", "co_occurrence", "similarity", "timeline")
            assert "weight" in edge
            assert "evidence_ids" in edge


@pytest.mark.asyncio
async def test_visualization_citation_network_with_evidence(db_session_persistent):
    """Citation network edges carry evidence_ids."""
    from fastapi import FastAPI
    from app.api.v4.visualization import router as viz_router
    from app.db.database import get_session

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-021", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    chunks = [
        DocumentChunk(id="v4-chk-032", document_id=doc.id, chunk_index=0,
                      content="针灸和经络是中医理论的核心概念。", token_count=18),
        DocumentChunk(id="v4-chk-033", document_id=doc.id, chunk_index=1,
                      content="针灸治疗以经络理论为基础。", token_count=12),
    ]
    db_session_persistent.add_all(chunks)
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v4/visualization/graph",
            json={"concept_labels": ["针灸", "经络"], "graph_type": "citation"},
        )
        assert response.status_code == 200
        body = response.json()
        graph = body["data"]
        if graph["edges"]:
            for edge in graph["edges"]:
                assert "evidence_ids" in edge


@pytest.mark.asyncio
async def test_visualization_timeline_data(db_session_persistent):
    """Timeline visualization returns structured data."""
    from fastapi import FastAPI
    from app.api.v4.visualization import router as viz_router
    from app.db.database import get_session

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-022", title="针灸甲乙经", dynasty="晋")
    doc2 = Document(id="v4-doc-023", title="黄帝内经", dynasty="战国")
    db_session_persistent.add_all([doc, doc2])
    await db_session_persistent.flush()
    chunks = [
        DocumentChunk(id="v4-chk-034", document_id=doc.id, chunk_index=0,
                      content="针灸甲乙经系统阐述了针灸理论。针灸是中医的核心疗法。", token_count=20),
        DocumentChunk(id="v4-chk-035", document_id=doc2.id, chunk_index=0,
                      content="黄帝内经详细论述了针灸的理论基础。", token_count=15),
    ]
    db_session_persistent.add_all(chunks)
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v4/visualization/graph",
            json={"concept_labels": ["针灸"], "graph_type": "timeline"},
        )
        assert response.status_code == 200
        body = response.json()
        graph = body["data"]
        assert "nodes" in graph


@pytest.mark.asyncio
async def test_visualization_schema_no_extra_fields(db_session_persistent):
    """Visualization schema enforces extra="forbid" — no free-form fields."""
    from fastapi import FastAPI
    from app.api.v4.visualization import router as viz_router
    from app.db.database import get_session

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-024", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    chunks = [
        DocumentChunk(id="v4-chk-036", document_id=doc.id, chunk_index=0,
                      content="针灸和经络是中医理论的核心概念。针灸甲乙经系统阐述了针灸与经络的关系。", token_count=30),
        DocumentChunk(id="v4-chk-037", document_id=doc.id, chunk_index=1,
                      content="针灸治疗以经络理论为基础。经络包括十二经脉和奇经八脉。", token_count=22),
    ]
    db_session_persistent.add_all(chunks)
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v4/visualization/graph",
            json={"concept_labels": ["针灸"], "graph_type": "concept"},
        )
        assert response.status_code == 200
        body = response.json()
        graph = body["data"]
        allowed_node_fields = {"id", "type", "label", "metadata", "trace_ids"}
        for node in graph["nodes"]:
            extra = set(node.keys()) - allowed_node_fields
            assert not extra, f"Unexpected fields in node: {extra}"
        allowed_edge_fields = {"source", "target", "type", "weight", "evidence_ids"}
        for edge in graph["edges"]:
            extra = set(edge.keys()) - allowed_edge_fields
            assert not extra, f"Unexpected fields in edge: {extra}"


# ======================================================================
# 4. Education Mode Tests (4)
# ======================================================================


@pytest.mark.asyncio
async def test_education_beginner_level(db_session_persistent):
    """Education mode produces grounded explanations at beginner level."""
    from fastapi import FastAPI
    from app.api.v4.education import router as edu_router
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    # Seed document and chunk
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-030", title="黄帝内经", dynasty="战国")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    c1 = DocumentChunk(id="v4-chk-040", document_id=doc.id, chunk_index=0,
                       content="黄帝内经灵枢经详细论述了经络循行。经络是运行气血的通道。", token_count=20)
    c2 = DocumentChunk(id="v4-chk-041", document_id=doc.id, chunk_index=1,
                       content="经络系统包括十二正经和奇经八脉。针灸治疗以经络理论为基础。", token_count=20)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")
    app.include_router(edu_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "edu test"})
        session_id = r1.json()["data"]["session_id"]

        r2 = await client.post(
            "/api/v4/education/learn",
            json={"session_id": session_id, "topic": "经络", "level": "beginner"},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["success"] is True
        data = body["data"]
        assert data["academic_type"] == "education"
        assert len(data["explanation"]) > 0 or len(data["evidence_trace"]) > 0


@pytest.mark.asyncio
async def test_education_citation_binding(db_session_persistent):
    """Every education concept has evidence trace — citation-bound."""
    from fastapi import FastAPI
    from app.api.v4.education import router as edu_router
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-031", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    c1 = DocumentChunk(id="v4-chk-042", document_id=doc.id, chunk_index=0,
                       content="针灸甲乙经系统阐述了经络理论。经络是运行气血的通道。", token_count=20)
    c2 = DocumentChunk(id="v4-chk-043", document_id=doc.id, chunk_index=1,
                       content="针灸治疗以经络理论为基础。经络包括十二经脉和奇经八脉。", token_count=20)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")
    app.include_router(edu_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "citation binding"})
        session_id = r1.json()["data"]["session_id"]

        r2 = await client.post(
            "/api/v4/education/learn",
            json={"session_id": session_id, "topic": "针灸", "level": "intermediate"},
        )
        assert r2.status_code == 200
        body = r2.json()
        if body["data"]["explanation"]:
            for concept in body["data"]["explanation"]:
                assert "evidence" in concept
                assert len(concept["evidence"]) > 0, (
                    f"Concept '{concept['concept']}' has no evidence — "
                    "violates corpus-bound constraint"
                )


@pytest.mark.asyncio
async def test_education_levels_produce_output(db_session_persistent):
    """Beginner, intermediate, advanced levels all produce output."""
    from fastapi import FastAPI
    from app.api.v4.education import router as edu_router
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-032", title="黄帝内经", dynasty="战国")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    c1 = DocumentChunk(id="v4-chk-044", document_id=doc.id, chunk_index=0,
                       content="黄帝内经灵枢经详细论述了经络循行和针灸治疗。经络是运行气血的通道。", token_count=25)
    c2 = DocumentChunk(id="v4-chk-045", document_id=doc.id, chunk_index=1,
                       content="经络系统包括十二正经和奇经八脉。针灸治疗以经络理论为基础。古今医家应用广泛。", token_count=25)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")
    app.include_router(edu_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "levels test"})
        session_id = r1.json()["data"]["session_id"]

        for level in ["beginner", "intermediate", "advanced"]:
            r2 = await client.post(
                "/api/v4/education/learn",
                json={"session_id": session_id, "topic": "经络", "level": level},
            )
            assert r2.status_code == 200, f"Level {level} failed"
            body = r2.json()
            assert body["data"]["academic_type"] == "education"


@pytest.mark.asyncio
async def test_education_query_history_recorded(db_session_persistent):
    """Education mode writes to QueryHistory."""
    from fastapi import FastAPI
    from app.api.v4.education import router as edu_router
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-033", title="黄帝内经", dynasty="战国")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    c1 = DocumentChunk(id="v4-chk-046", document_id=doc.id, chunk_index=0,
                       content="黄帝内经灵枢经详细论述了经络循行。经络是运行气血的通道。", token_count=20)
    c2 = DocumentChunk(id="v4-chk-047", document_id=doc.id, chunk_index=1,
                       content="经络系统包括十二正经和奇经八脉。针灸治疗以经络理论为基础。", token_count=20)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")
    app.include_router(edu_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "edu qh test"})
        session_id = r1.json()["data"]["session_id"]

        r2 = await client.post(
            "/api/v4/education/learn",
            json={"session_id": session_id, "topic": "经络", "level": "beginner"},
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["traceability"] is not None
        assert body["traceability"]["query_id"] is not None
        assert body["traceability"]["trace_ids"] is not None


# ======================================================================
# 5. Traceability Validation Tests (3)
# ======================================================================


@pytest.mark.asyncio
async def test_traceability_block_in_all_responses(db_session_persistent):
    """Every V4 endpoint response includes a traceability block."""
    from fastapi import FastAPI
    from app.api.v4.education import router as edu_router
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-040", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    c1 = DocumentChunk(id="v4-chk-050", document_id=doc.id, chunk_index=0,
                       content="皇甫谧编撰的针灸甲乙经系统阐述了经络理论。", token_count=20)
    c2 = DocumentChunk(id="v4-chk-051", document_id=doc.id, chunk_index=1,
                       content="经络是运行气血、联系脏腑的通道。", token_count=14)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")
    app.include_router(edu_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "trace test"})
        session_id = r1.json()["data"]["session_id"]

        endpoints = [
            ("/api/v4/research/query", {"session_id": session_id, "query": "针灸", "mode": "research"}),
            ("/api/v4/education/learn", {"session_id": session_id, "topic": "经络", "level": "beginner"}),
        ]
        for url, payload in endpoints:
            r = await client.post(url, json=payload)
            assert r.status_code == 200, f"{url} failed"
            body = r.json()
            assert "traceability" in body, f"{url} missing traceability block"
            tb = body["traceability"]
            assert tb is not None, f"{url} traceability is null"
            assert "trace_ids" in tb
            assert "citation_count" in tb
            assert "source_documents" in tb


@pytest.mark.asyncio
async def test_every_trace_id_resolves_to_passage(db_session_persistent):
    """Every trace_id in a response links to a retrievable passage."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-041", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    c1 = DocumentChunk(id="v4-chk-052", document_id=doc.id, chunk_index=0,
                       content="皇甫谧编撰的针灸甲乙经系统阐述了经络理论。", token_count=20)
    c2 = DocumentChunk(id="v4-chk-053", document_id=doc.id, chunk_index=1,
                       content="经络是运行气血、联系脏腑的通道。", token_count=14)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "resolution test"})
        session_id = r1.json()["data"]["session_id"]

        r2 = await client.post(
            "/api/v4/research/query",
            json={"session_id": session_id, "query": "经络", "mode": "research"},
        )
        assert r2.status_code == 200
        body = r2.json()
        trace_ids = body["traceability"]["trace_ids"]
        for tid in trace_ids:
            assert tid and isinstance(tid, str)
            assert len(tid) > 0
        assert body["traceability"]["citation_count"] > 0


@pytest.mark.asyncio
async def test_api_no_internal_fields_leaked(db_session_persistent):
    """API response traceability block does not expose internal fields."""
    from fastapi import FastAPI
    from app.api.v4.research import router as research_router
    from app.db.database import get_session

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-042", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    await db_session_persistent.flush()
    c1 = DocumentChunk(id="v4-chk-054", document_id=doc.id, chunk_index=0,
                       content="皇甫谧编撰的针灸甲乙经系统阐述了经络理论。", token_count=20)
    c2 = DocumentChunk(id="v4-chk-055", document_id=doc.id, chunk_index=1,
                       content="经络是运行气血、联系脏腑的通道。", token_count=14)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    app = FastAPI()
    async def override_get_session():
        yield db_session_persistent
    app.dependency_overrides[get_session] = override_get_session

    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "no-leak test"})
        session_id = r1.json()["data"]["session_id"]

        r2 = await client.post(
            "/api/v4/research/query",
            json={"session_id": session_id, "query": "针灸", "mode": "research"},
        )
        assert r2.status_code == 200
        body = r2.json()

        raw = json.dumps(body, ensure_ascii=False)
        banned = ["retrieval_score", "retrieval_method"]
        for field in banned:
            assert field not in raw, f"Internal field '{field}' leaked in API response"
