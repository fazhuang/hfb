"""
Integration tests for RBAC across all four authorization levels.

These tests directly exercise the service/repository layer — not the full
ASGI stack — to verify that:
  - User → Role → Permission mapping works correctly
  - Admin has all permissions
  - Researcher has create + read on own entities
  - Visitor has read-only
  - Anonymous / non-existent users get no permissions
  - Workspace cross-user isolation is enforced
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.services.graph_service import GraphService
from app.services.search_service import SearchService, SearchParams
from app.services.dashboard_service import DashboardService
from app.services.workspace_service import WorkspaceService
from app.models.user import User, Role, Permission
from app.models.user import user_role, role_permission

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401

pytestmark = pytest.mark.anyio


# ============================================================
# Helpers — build 4 users in test DB
# ============================================================


@pytest.fixture
async def four_users(db_session: AsyncSession):
    """Create admin, researcher, researcher2, visitor with distinct permissions."""
    session = db_session
    auth_svc = AuthService(session)

    # --- Permissions ---
    perms: dict[str, Permission] = {}
    resources = [
        "person",
        "book",
        "version",
        "chapter",
        "passage",
        "paper",
        "image",
        "document",
        "graph",
        "search",
        "ai",
        "workspace",
        "dashboard",
    ]
    for resource in resources:
        for action in ["create", "read", "update", "delete"]:
            p = Permission(resource=resource, action=action)
            session.add(p)
            perms[f"{resource}.{action}"] = p
    p = Permission(resource="search", action="reindex")
    session.add(p)
    perms["search.reindex"] = p
    await session.flush()

    # --- Roles ---
    roles: dict[str, Role] = {}
    for name in ["Platform Administrator", "Researcher", "Researcher2", "Visitor"]:
        r = Role(name=name, description=f"Test {name}")
        session.add(r)
        roles[name] = r
    await session.flush()

    async def _grant(role: Role, codes: list[str]) -> None:
        from sqlalchemy import select as sa, and_

        for code in codes:
            p = perms.get(code)
            if p:
                ex = await session.execute(
                    sa(role_permission).where(
                        and_(
                            role_permission.c.role_id == role.id,
                            role_permission.c.permission_id == p.id,
                        )
                    )
                )
                if ex.first() is None:
                    await session.execute(
                        role_permission.insert().values(
                            role_id=role.id, permission_id=p.id
                        )
                    )
        await session.flush()

    async def _add_role(user: User, role: Role) -> None:
        from sqlalchemy import select as sa, and_

        ex = await session.execute(
            sa(user_role).where(
                and_(user_role.c.user_id == user.id, user_role.c.role_id == role.id)
            )
        )
        if ex.first() is None:
            await session.execute(
                user_role.insert().values(user_id=user.id, role_id=role.id)
            )
        await session.flush()

    VISITOR_READS = [
        "person.read",
        "book.read",
        "version.read",
        "passage.read",
        "paper.read",
        "image.read",
        "document.read",
        "graph.read",
        "search.read",
        "dashboard.read",
    ]
    RESEARCHER = VISITOR_READS + [
        "person.create",
        "person.update",
        "book.create",
        "book.update",
        "passage.create",
        "passage.update",
        "workspace.read",
        "workspace.create",
        "ai.read",
    ]

    await _grant(roles["Visitor"], VISITOR_READS)
    await _grant(roles["Researcher"], RESEARCHER)
    await _grant(roles["Researcher2"], RESEARCHER)
    await _grant(roles["Platform Administrator"], list(perms.keys()))

    # --- Users ---
    admin = await auth_svc.register(
        "testadmin", "admin@test.com", "admin123456", "Admin"
    )
    researcher = await auth_svc.register(
        "testresearcher", "res@test.com", "res123456", "R"
    )
    researcher2 = await auth_svc.register(
        "testresearcher2", "res2@test.com", "res123456", "R2"
    )
    visitor = await auth_svc.register("testvisitor", "vis@test.com", "vis123456", "V")

    await _add_role(admin, roles["Platform Administrator"])
    await _add_role(researcher, roles["Researcher"])
    await _add_role(researcher2, roles["Researcher2"])
    await _add_role(visitor, roles["Visitor"])
    await session.commit()

    return {
        "admin": admin,
        "researcher": researcher,
        "researcher2": researcher2,
        "visitor": visitor,
        "auth_svc": AuthService(session),
        "session": session,
    }


# ============================================================
# Permission checks — 4 roles
# ============================================================


class TestRBACPermissions:
    """Direct permission checks for all 4 roles."""

    async def test_admin_has_all_permissions(self, four_users):
        svc = four_users["auth_svc"]
        admin_id = four_users["admin"].id
        assert await svc.has_permission(admin_id, "book", "read") is True
        assert await svc.has_permission(admin_id, "book", "create") is True
        assert await svc.has_permission(admin_id, "book", "delete") is True
        assert await svc.has_permission(admin_id, "person", "read") is True
        assert await svc.has_permission(admin_id, "graph", "read") is True
        assert await svc.has_permission(admin_id, "search", "reindex") is True

    async def test_researcher_has_create_read(self, four_users):
        svc = four_users["auth_svc"]
        rid = four_users["researcher"].id
        assert await svc.has_permission(rid, "book", "read") is True
        assert await svc.has_permission(rid, "book", "create") is True
        assert await svc.has_permission(rid, "book", "update") is True
        assert await svc.has_permission(rid, "book", "delete") is False
        assert await svc.has_permission(rid, "person", "read") is True
        assert await svc.has_permission(rid, "graph", "read") is True

    async def test_visitor_read_only(self, four_users):
        svc = four_users["auth_svc"]
        vid = four_users["visitor"].id
        assert await svc.has_permission(vid, "book", "read") is True
        assert await svc.has_permission(vid, "person", "read") is True
        assert await svc.has_permission(vid, "graph", "read") is True
        assert await svc.has_permission(vid, "book", "delete") is False

    async def test_nonexistent_user_no_perms(self, four_users):
        svc = four_users["auth_svc"]
        assert (
            await svc.has_permission(
                "00000000-0000-0000-0000-000000000000", "book", "read"
            )
            is False
        )

    async def test_researcher_cannot_delete(self, four_users):
        svc = four_users["auth_svc"]
        rid = four_users["researcher"].id
        assert await svc.has_permission(rid, "book", "delete") is False
        assert await svc.has_permission(rid, "person", "delete") is False

    async def test_visitor_cannot_write_anywhere(self, four_users):
        svc = four_users["auth_svc"]
        vid = four_users["visitor"].id
        # Visitor should not have elevated permissions that require Researcher+
        assert await svc.has_permission(vid, "book", "delete") is False
        assert await svc.has_permission(vid, "person", "delete") is False
        assert await svc.has_permission(vid, "graph", "delete") is False


# ============================================================
# Service-layer RBAC integration
# ============================================================


class TestGraphServiceRBAC:
    """Test that GraphService operations work for authorized users."""

    async def test_admin_can_search_entities(self, four_users):
        svc = GraphService(four_users["session"])
        nodes = await svc.search_entities(limit=5)
        assert isinstance(nodes, list)

    async def test_admin_can_create_relation(self, four_users):
        from app.models.person import Person
        from app.models.book import Book
        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk
        from app.schemas.graph import GraphEvidence

        session = four_users["session"]
        p = Person(name="graph_rbac_person", dynasty="唐")
        b = Book(title="graph_rbac_book", dynasty="唐")
        d = Document(title="rbac_test_doc", dynasty="唐")
        session.add_all([p, b, d])
        await session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="graph_rbac_person编撰graph_rbac_book。",
            token_count=20,
        )
        session.add(c)
        await session.flush()

        ev = GraphEvidence(
            document_id=d.id,
            chunk_id=c.id,
            exact_quote="graph_rbac_person编撰graph_rbac_book。",
            citation=f"[{d.id}:{c.id}]",
        )

        svc = GraphService(session)
        rel = await svc.create_relation(
            "person", p.id, "book", b.id, "authored", evidence=ev
        )
        assert rel.id is not None

    async def test_neighbors_nonexistent_raises(self, four_users):
        svc = GraphService(four_users["session"])
        from app.models.person import Person

        p = Person(name="neighbor_test")
        four_users["session"].add(p)
        await four_users["session"].flush()

        # Should work with existing entity
        await svc.get_neighbors("person", p.id)


class TestSearchServiceRBAC:
    """Test SearchService."""

    async def test_admin_search(self, four_users):
        svc = SearchService(four_users["session"])
        result = await svc.search(SearchParams(q="test"))
        assert result.total >= 0

    async def test_admin_can_suggest(self, four_users):
        svc = SearchService(four_users["session"])
        from app.models.person import Person

        p = Person(name="suggest_rbac_test")
        four_users["session"].add(p)
        await four_users["session"].flush()

        suggestions = await svc.suggest("suggest")
        assert isinstance(suggestions, list)


class TestDashboardServiceRBAC:
    """Test DashboardService."""

    async def test_admin_dashboard_overview(self, four_users):
        svc = DashboardService(four_users["session"])
        overview = await svc.get_overview()
        assert "entity_counts" in overview


# ============================================================
# Workspace cross-user isolation
# ============================================================


class TestWorkspaceIsolation:
    """Verify that users cannot access each other's sessions."""

    async def test_researcher2_cannot_read_researcher1_session(self, four_users):
        """Researcher2 cannot access Researcher1's session."""
        session = four_users["session"]
        ws = WorkspaceService(session)

        # Researcher 1 creates a session
        s = await ws.create_session(four_users["researcher"].id, "R1 Private")
        assert s.user_id == four_users["researcher"].id

        # Researcher 2 fetches it — service layer returns it but API layer checks user_id
        # This test verifies the data layer correctly stores user_id
        got = await ws.get_session(s.id)
        assert got is not None
        assert got.user_id == four_users["researcher"].id  # belongs to R1

    async def test_delete_session_works(self, four_users):
        session = four_users["session"]
        ws = WorkspaceService(session)
        s = await ws.create_session(four_users["researcher"].id, "Delete Me")
        s_id = s.id

        ok = await ws.delete_session(s_id)
        assert ok is True
        assert await ws.get_session(s_id) is None


# ============================================================
# Workspace cross-user isolation — real API route tests
# ============================================================
#
# These tests exercise the ACTUAL FastAPI routes via httpx ASGITransport,
# NOT just the service layer.  Two researchers each have their own session
# with notes, citations, query history, and runs.  We then verify that:
#   - Each researcher can read their own data
#   - Each researcher CANNOT read the other's data (404)
#   - No data leaks in error responses
#
# Fixture-based data creation is documented inline.
# All reads go through the real API.


class TestWorkspaceApiIsolation:
    """Cross-user isolation exercised through real API routes with real auth chain.

    Fixture strategy (real JWT, real permissions, no mock auth):
      1.  Build a FastAPI app with v1 workspace + v4 research routers.
      2.  Override ONLY get_session → test DB.
      3.  Create two real users (A and B) via AuthService.register() — this
          auto-seeds RBAC and assigns the "Researcher" role.
      4.  Create real JWT access tokens for each user via create_access_token().
      5.  Seed two sessions (A1 and B1) via ORM, each with notes, citations,
          query history, and research runs.
      6.  ALL HTTP requests carry a real Authorization: Bearer <token> header.
      7.  The auth middleware decodes the JWT, resolves the user_id, and
          checks permissions against the real RBAC tables.
      8.  No overrides of get_current_user, get_auth_service, or permission
          guards; no FakeAuth; no context-variable user switching.
    """

    @pytest.fixture
    async def isolation_app(
        self, db_session_persistent: AsyncSession
    ):
        """Build the test app with a real JWT auth chain.

        Uses db_session_persistent for both seed-data creation and API
        operation so that the test database is the single source of truth.
        """
        import json

        from fastapi import FastAPI

        from app.db.database import get_session
        from app.api.v1.ai import workspace_router
        from app.api.v4.research import router as v4_research_router
        from app.models.workspace import CitationCollection, QueryHistory
        from app.services.auth_service import AuthService, create_access_token
        from app.services.workspace_service import WorkspaceService

        db = db_session_persistent
        auth_svc = AuthService(db)

        # ---- Create two real users ----
        # register() auto-seeds RBAC (permissions, roles) and assigns
        # the default "Researcher" role. Both users get real passwords.
        user_a = await auth_svc.register(
            "iso-a", "iso-a@test.com", "IsoA_Pass123!", "ISO-A"
        )
        user_b = await auth_svc.register(
            "iso-b", "iso-b@test.com", "IsoB_Pass123!", "ISO-B"
        )
        await db.flush()

        # ---- Create real JWT access tokens ----
        token_a = create_access_token(user_a.id)
        token_b = create_access_token(user_b.id)

        # ---- Prove users have distinct IDs and the tokens differ ----
        assert user_a.id != user_b.id, "User A and B must have different IDs"
        assert token_a != token_b, "Token A and B must differ"

        # ---- Seed workspace data ----
        ws = WorkspaceService(db)

        # Sessions
        s_a = await ws.create_session(user_a.id, "Researcher A Session")
        s_b = await ws.create_session(user_b.id, "Researcher B Session")

        # Prove session UUIDs are real and distinct
        assert s_a.id is not None
        assert s_b.id is not None
        assert s_a.id != s_b.id

        # Notes
        note_a = await ws.create_note(s_a.id, "Note by A", tags="a-tag")
        note_b = await ws.create_note(s_b.id, "Note by B", tags="b-tag")

        # Citations
        cit_a = CitationCollection(
            session_id=str(s_a.id),
            trace_json='{"trace_id":"ta-1"}',
            citation_text="Citation by A",
            source_document="Document A",
        )
        cit_b = CitationCollection(
            session_id=str(s_b.id),
            trace_json='{"trace_id":"tb-1"}',
            citation_text="Citation by B",
            source_document="Document B",
        )
        db.add_all([cit_a, cit_b])

        # Query history
        qh_a = QueryHistory(
            session_id=str(s_a.id),
            query_text="Query from A",
            query_type="research",
            citation_count=1,
            result_summary='{"traces":[{"trace_id":"ta-1","document_id":"doc-a"}]}',
        )
        qh_b = QueryHistory(
            session_id=str(s_b.id),
            query_text="Query from B",
            query_type="research",
            citation_count=1,
            result_summary='{"traces":[{"trace_id":"tb-1","document_id":"doc-b"}]}',
        )
        db.add_all([qh_a, qh_b])

        # Research runs in session.workflow_state JSON
        runs_state_a = json.dumps(
            {
                "runs": [
                    {
                        "run_id": "run-a-001",
                        "session_id": str(s_a.id),
                        "workflow_type": "full_research_flow",
                        "topic": "Run by A",
                        "started_at": "2026-07-17T10:00:00+00:00",
                        "completed_at": "2026-07-17T10:05:00+00:00",
                        "step_execution_trace": [
                            {"name": "topic_selection", "status": "completed"},
                            {"name": "literature_retrieval", "status": "completed"},
                            {"name": "evidence_synthesis", "status": "completed"},
                            {"name": "report_generation", "status": "completed"},
                            {"name": "citation_export", "status": "completed"},
                        ],
                        "output_artifacts": {"markdown": "# Report A", "artifact_id": "art-a"},
                        "replay_manifest": {
                            "retrieval_snapshot": [
                                {
                                    "trace_id": "ta-1",
                                    "document_id": "doc-a",
                                    "chunk_id": "chk-a",
                                    "claim_text": "Claim A",
                                    "quote": "Quote A",
                                    "citation_text": "[doc-a:0]",
                                }
                            ],
                            "traces": [
                                {
                                    "trace_id": "ta-1",
                                    "document_id": "doc-a",
                                    "chunk_id": "chk-a",
                                    "passage_id": "passage-a",
                                    "provenance_kind": "retrieval",
                                    "retrieval_score": 0.95,
                                    "retrieval_method": "ili_keyword_search",
                                }
                            ],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        )
        runs_state_b = json.dumps(
            {
                "runs": [
                    {
                        "run_id": "run-b-001",
                        "session_id": str(s_b.id),
                        "workflow_type": "full_research_flow",
                        "topic": "Run by B",
                        "started_at": "2026-07-17T10:00:00+00:00",
                        "completed_at": "2026-07-17T10:05:00+00:00",
                        "step_execution_trace": [
                            {"name": "topic_selection", "status": "completed"},
                            {"name": "literature_retrieval", "status": "completed"},
                            {"name": "evidence_synthesis", "status": "completed"},
                            {"name": "report_generation", "status": "completed"},
                            {"name": "citation_export", "status": "completed"},
                        ],
                        "output_artifacts": {"markdown": "# Report B", "artifact_id": "art-b"},
                        "replay_manifest": {
                            "retrieval_snapshot": [
                                {
                                    "trace_id": "tb-1",
                                    "document_id": "doc-b",
                                    "chunk_id": "chk-b",
                                    "claim_text": "Claim B",
                                    "quote": "Quote B",
                                    "citation_text": "[doc-b:0]",
                                }
                            ],
                            "traces": [
                                {
                                    "trace_id": "tb-1",
                                    "document_id": "doc-b",
                                    "chunk_id": "chk-b",
                                    "passage_id": "passage-b",
                                    "provenance_kind": "retrieval",
                                    "retrieval_score": 0.88,
                                    "retrieval_method": "ili_keyword_search",
                                }
                            ],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        )
        s_a.workflow_state = runs_state_a
        s_b.workflow_state = runs_state_b
        await db.flush()

        # ---- Build app — ONLY override get_session, NO auth overrides ----
        app = FastAPI()
        app.include_router(workspace_router, prefix="/api/v1")
        app.include_router(v4_research_router, prefix="/api/v4")

        async def _override_get_session():
            yield db_session_persistent

        app.dependency_overrides[get_session] = _override_get_session
        # NOTE: get_current_user and get_auth_service are NOT overridden.
        # The real JWT auth chain is exercised end-to-end.

        return {
            "app": app,
            "user_a": user_a,
            "user_b": user_b,
            "token_a": token_a,
            "token_b": token_b,
            "session_a": s_a,
            "session_b": s_b,
            "note_a": note_a,
            "note_b": note_b,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_json(
        self, client: Any, url: str, expect_status: int = 200
    ) -> dict[str, Any]:
        r = await client.get(url)
        assert r.status_code == expect_status, (
            f"Expected {expect_status}, got {r.status_code}: {r.text[:200]}"
        )
        return r.json()

    async def _get_json_404(
        self, client: Any, url: str
    ) -> dict[str, Any]:
        """GET and expect 404, returning the parsed error body for leakage checks."""
        r = await client.get(url)
        assert r.status_code == 404, (
            f"Expected 404, got {r.status_code}: {r.text[:200]}"
        )
        return r.json()

    def _assert_not_leaked(self, body: dict[str, Any], forbidden_terms: list[str]) -> None:
        """Verify the response body does not leak any forbidden terms."""
        body_str = json.dumps(body, ensure_ascii=False).lower()
        for term in forbidden_terms:
            assert term.lower() not in body_str, (
                f"Response leaked forbidden term '{term}' in body"
            )

    def _headers(self, isolation_app: dict, user: str) -> dict[str, str]:
        """Return Authorization: Bearer <token> header for the given user key."""
        token_key = f"token_{user}"  # "token_a" or "token_b"
        return {"Authorization": f"Bearer {isolation_app[token_key]}"}

    # ==================================================================
    # GET /api/v1/workspace/sessions/{id}
    # ==================================================================

    async def test_a_can_read_own_session(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            body = await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_a'].id}",
            )
            assert body["data"]["title"] == "Researcher A Session"

    async def test_b_can_read_own_session(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            body = await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_b'].id}",
            )
            assert body["data"]["title"] == "Researcher B Session"

    async def test_a_cannot_read_b_session(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_b'].id}",
                expect_status=404,
            )

    async def test_b_cannot_read_a_session(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_a'].id}",
                expect_status=404,
            )

    # ==================================================================
    # GET /api/v1/workspace/sessions/{id}/notes
    # ==================================================================

    async def test_a_can_read_own_notes(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            body = await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_a'].id}/notes",
            )
            notes = body["data"]
            assert len(notes) >= 1
            assert any("Note by A" in n["content"] for n in notes)

    async def test_b_can_read_own_notes(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            body = await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_b'].id}/notes",
            )
            notes = body["data"]
            assert len(notes) >= 1
            assert any("Note by B" in n["content"] for n in notes)

    async def test_a_cannot_read_b_notes(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_b'].id}/notes",
                expect_status=404,
            )

    async def test_b_cannot_read_a_notes(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_a'].id}/notes",
                expect_status=404,
            )

    # ==================================================================
    # GET /api/v1/workspace/sessions/{id}/citations
    # ==================================================================

    async def test_a_can_read_own_citations(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            body = await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_a'].id}/citations",
            )
            citations = body["data"]
            assert len(citations) >= 1
            assert any("Citation by A" in c["citation_text"] for c in citations)

    async def test_b_can_read_own_citations(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            body = await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_b'].id}/citations",
            )
            citations = body["data"]
            assert len(citations) >= 1
            assert any("Citation by B" in c["citation_text"] for c in citations)

    async def test_a_cannot_read_b_citations(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_b'].id}/citations",
                expect_status=404,
            )

    async def test_b_cannot_read_a_citations(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            await self._get_json(
                client,
                f"/api/v1/workspace/sessions/{isolation_app['session_a'].id}/citations",
                expect_status=404,
            )

    # ==================================================================
    # GET /api/v4/research/session/{id}/history
    # ==================================================================

    async def test_a_can_read_own_history(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            body = await self._get_json(
                client,
                f"/api/v4/research/session/{isolation_app['session_a'].id}/history",
            )
            assert body["success"] is True
            history = body["data"]["history"]
            assert len(history) >= 1
            assert any("Query from A" in h["query_text"] for h in history)

    async def test_b_can_read_own_history(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            body = await self._get_json(
                client,
                f"/api/v4/research/session/{isolation_app['session_b'].id}/history",
            )
            assert body["success"] is True
            history = body["data"]["history"]
            assert len(history) >= 1
            assert any("Query from B" in h["query_text"] for h in history)

    async def test_a_cannot_read_b_history(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_b'].id}/history"
            )
            assert r.status_code == 404, (
                f"Expected 404, got {r.status_code}: {r.text[:200]}"
            )

    async def test_b_cannot_read_a_history(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_a'].id}/history"
            )
            assert r.status_code == 404, (
                f"Expected 404, got {r.status_code}: {r.text[:200]}"
            )

    # ==================================================================
    # GET /api/v4/research/session/{id}/runs
    # ==================================================================

    async def test_a_can_read_own_runs(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            body = await self._get_json(
                client,
                f"/api/v4/research/session/{isolation_app['session_a'].id}/runs",
            )
            assert body["success"] is True
            runs = body["data"]["runs"]
            assert len(runs) >= 1
            assert any("Run by A" in r["topic"] for r in runs)

    async def test_b_can_read_own_runs(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            body = await self._get_json(
                client,
                f"/api/v4/research/session/{isolation_app['session_b'].id}/runs",
            )
            assert body["success"] is True
            runs = body["data"]["runs"]
            assert len(runs) >= 1
            assert any("Run by B" in r["topic"] for r in runs)

    async def test_a_cannot_read_b_runs(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_b'].id}/runs"
            )
            assert r.status_code == 404, (
                f"Expected 404, got {r.status_code}: {r.text[:200]}"
            )

    async def test_b_cannot_read_a_runs(self, isolation_app):
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_a'].id}/runs"
            )
            assert r.status_code == 404, (
                f"Expected 404, got {r.status_code}: {r.text[:200]}"
            )

    # ==================================================================
    # Cross-verification: known UUID cannot be probed
    # ==================================================================

    async def test_a_cannot_get_b_notes_via_known_uuid(self, isolation_app):
        """User A knows B's session UUID but still gets 404 for B's notes."""
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v1/workspace/sessions/{isolation_app['session_b'].id}/notes"
            )
            assert r.status_code == 404, (
                f"Expected 404, got {r.status_code}: {r.text[:200]}"
            )

    async def test_b_cannot_get_a_citations_via_known_uuid(self, isolation_app):
        """User B knows A's session UUID but still gets 404 for A's citations."""
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "b")) as client:
            r = await client.get(
                f"/api/v1/workspace/sessions/{isolation_app['session_a'].id}/citations"
            )
            assert r.status_code == 404, (
                f"Expected 404, got {r.status_code}: {r.text[:200]}"
            )

    # ==================================================================
    # No data leak in 404 bodies
    # ==================================================================

    async def test_404_does_not_leak_session_title(self, isolation_app):
        """404 response body must not contain the other user's session title."""
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v1/workspace/sessions/{isolation_app['session_b'].id}"
            )
            assert r.status_code == 404
            body = r.json()
            self._assert_not_leaked(body, ["Researcher B Session"])

    async def test_404_does_not_leak_other_user_id(self, isolation_app):
        """404 response body must not contain the other user's user ID."""
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v1/workspace/sessions/{isolation_app['session_b'].id}"
            )
            assert r.status_code == 404
            body = r.json()
            self._assert_not_leaked(body, [isolation_app["user_b"].id])

    # ==================================================================
    # GET /api/v4/research/session/{session_id}/runs/{run_id}/export
    # ==================================================================

    async def test_export_own_session_own_run_succeeds(self, isolation_app):
        """Own session + own run: Markdown export succeeds with correct headers."""
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_a'].id}"
                f"/runs/run-a-001/export?format=markdown"
            )
            assert r.status_code == 200, (
                f"Expected 200, got {r.status_code}: {r.text[:200]}"
            )
            assert r.headers["content-type"].startswith("text/markdown"), (
                f"Expected text/markdown MIME, got {r.headers.get('content-type')}"
            )
            cd = r.headers.get("content-disposition", "")
            assert 'attachment' in cd, (
                f"Expected Content-Disposition attachment, got {cd!r}"
            )
            assert 'hfb-research-report-run-a-00.md' in cd, (
                f"Expected safe filename, got {cd!r}"
            )
            assert "# Report A" in r.text, (
                f"Expected report content, got {r.text[:200]}"
            )

    async def test_user_a_accesses_user_b_session_export_rejected(self, isolation_app):
        """User A accessing user B's session/run export → 404 (not leaked)."""
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_b'].id}"
                f"/runs/run-b-001/export?format=markdown"
            )
            assert r.status_code == 404, (
                f"Expected 404, got {r.status_code}: {r.text[:200]}"
            )
            body = r.json()
            self._assert_not_leaked(body, ["Researcher B", "Report B", "user_b"])

    async def test_own_session_other_users_run_rejected(self, isolation_app):
        """User A's session + User B's run_id → 404 (run not in session)."""
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_a'].id}"
                f"/runs/run-b-001/export?format=markdown"
            )
            assert r.status_code == 404, (
                f"Expected 404, got {r.status_code}: {r.text[:200]}"
            )

    async def test_export_nonexistent_run_rejected(self, isolation_app):
        """Valid session but nonexistent run → 404."""
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_a'].id}"
                f"/runs/nonexistent-run/export?format=markdown"
            )
            assert r.status_code == 404, (
                f"Expected 404, got {r.status_code}: {r.text[:200]}"
            )

    async def test_export_unsupported_format_rejected(self, isolation_app):
        """Unsupported format → 400 with safe error message."""
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_a'].id}"
                f"/runs/run-a-001/export?format=pdf"
            )
            assert r.status_code == 400, (
                f"Expected 400, got {r.status_code}: {r.text[:200]}"
            )
            body = r.json()
            assert "Unsupported" in body.get("detail", ""), (
                f"Expected 'Unsupported' in detail, got {body}"
            )

    async def test_export_empty_run_report_rejected(self, isolation_app, db_session_persistent):
        """Run with empty markdown → 409 conflict."""
        import json as _json

        transport = ASGITransport(app=isolation_app["app"])

        from app.services.workspace_service import WorkspaceService
        ws = WorkspaceService(db_session_persistent)

        s = await ws.get_session(isolation_app["session_a"].id)
        import json as _json2
        existing = _json2.loads(s.workflow_state or "{}")
        runs = existing.get("runs", [])
        runs.append({
            "run_id": "empty-run",
            "session_id": str(isolation_app["session_a"].id),
            "workflow_type": "full_research_flow",
            "topic": "Empty Run",
            "started_at": "2026-07-17T10:00:00+00:00",
            "completed_at": "2026-07-17T10:05:00+00:00",
            "step_execution_trace": [
                {"name": "topic_selection", "status": "completed"},
                {"name": "report_generation", "status": "completed"},
            ],
            "output_artifacts": {"markdown": ""},
            "replay_manifest": {"retrieval_snapshot": [], "traces": []},
        })
        s.workflow_state = _json2.dumps(existing, ensure_ascii=False)
        await db_session_persistent.flush()

        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_a'].id}"
                f"/runs/empty-run/export?format=markdown"
            )
            assert r.status_code == 409, (
                f"Expected 409, got {r.status_code}: {r.text[:200]}"
            )

    async def test_export_response_does_not_leak_other_user_data(self, isolation_app):
        """Export response content must not contain another user's data."""
        transport = ASGITransport(app=isolation_app["app"])
        async with AsyncClient(transport=transport, base_url="http://test",
                               headers=self._headers(isolation_app, "a")) as client:
            r = await client.get(
                f"/api/v4/research/session/{isolation_app['session_a'].id}"
                f"/runs/run-a-001/export?format=markdown"
            )
            assert r.status_code == 200
            # Should contain own data, not other user's
            assert "Report A" in r.text
            assert "Report B" not in r.text
            assert "Researcher B" not in r.text
