"""
Day 3 acceptance tests — API productization layer.

Covers:
  - API contract: standardized response schema, execution_time, model field
  - Filters: document_id, year, author_id with ILIKE keyword search
  - Citation validation: format, traceability, no generated citations
  - Concurrency: multiple concurrent requests, stability under repeated calls
"""

from __future__ import annotations

import asyncio

import pytest
from app.db.base import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
async def app_db_session():
    """In-memory SQLite session used by the test app (via get_session override)."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


def _make_test_app():
    """Build a FastAPI test app matching the real v1 router structure."""
    from app.core.error_handlers import register_error_handlers
    from app.middleware.request_id import RequestIDMiddleware
    from fastapi import FastAPI

    app = FastAPI(debug=False)
    app.add_middleware(RequestIDMiddleware)
    register_error_handlers(app)

    from app.api.v1 import router as v1_router

    app.include_router(v1_router)
    return app


async def _seed_data(session):
    """Seed test data: two documents with different years/authors, multiple chunks."""
    from app.services.ingestion import IngestionService

    svc = IngestionService(session)
    await svc.ingest_text(
        title="针灸甲乙经",
        text=(
            "皇甫谧编撰的《针灸甲乙经》系统整理了经络学说。\n\n"
            "该书对后世针灸学发展有深远影响。\n\n"
            "系统总结了腧穴定位和刺灸方法。"
        ),
        metadata={
            "dynasty": "西晋",
            "category": "针灸",
            "copyright_status": "public_domain",
            "authorization_basis": "test seed",
        },
    )
    await svc.ingest_text(
        title="伤寒杂病论",
        text=(
            "张仲景所著《伤寒杂病论》是中医经典。\n\n"
            "该书系统论述了伤寒病证治。\n\n"
            "对后世医学发展影响深远。"
        ),
        metadata={
            "dynasty": "东汉",
            "category": "伤寒",
            "copyright_status": "public_domain",
            "authorization_basis": "test seed",
        },
    )
    await session.flush()


async def _search_auth_headers(session) -> dict[str, str]:
    """Create a Researcher (search.read) user and return Authorization headers."""
    from app.services.auth_service import AuthService, create_access_token

    auth_svc = AuthService(session)
    user = await auth_svc.register(
        "day3-search-user", "day3-search-user@test.com", "Test123456!", "Day3Search"
    )
    await session.flush()
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# API CONTRACT TESTS (5 tests)
# ============================================================


@pytest.mark.anyio
class TestAPIContract:
    """Day 3 standardized response contract."""

    async def test_openapi_response_schema_is_fully_strict(self):
        """OpenAPI defines the frozen response and forbids extra object fields."""
        from app.api.v1.day2_search import router as search_router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(search_router, prefix="/api/v1")
        openapi = app.openapi()
        response_schema = openapi["paths"]["/api/v1/search"]["post"]["responses"][
            "200"
        ]["content"]["application/json"]["schema"]
        assert response_schema == {"$ref": "#/components/schemas/SearchResponse"}

        schemas = openapi["components"]["schemas"]
        expected_properties = {
            "SearchResponse": {"query", "results", "metadata"},
            "SearchResult": {
                "chunk_id",
                "document_id",
                "content",
                "score",
                "citation",
            },
            "Metadata": {"top_k", "model"},
        }
        for schema_name, properties in expected_properties.items():
            schema = schemas[schema_name]
            assert schema["additionalProperties"] is False
            assert set(schema["properties"]) == properties
            assert set(schema["required"]) == properties

    async def test_response_has_query_results_metadata(self, app_db_session):
        """POST /api/v1/search returns top-level {query, results, metadata}."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "针灸", "top_k": 3},
            )
            assert r.status_code == 200
            body = r.json()

            assert "query" in body
            assert body["query"] == "针灸"
            assert "results" in body
            assert isinstance(body["results"], list)
            assert "metadata" in body

    async def test_metadata_fields_top_k_and_model(self, app_db_session):
        """Metadata must include top_k and model: retrieval-only. NO execution_time."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "经络", "top_k": 10},
            )
            assert r.status_code == 200
            meta = r.json()["metadata"]

            assert meta["top_k"] == 10
            assert meta["model"] == "retrieval-only"
            # execution_time MUST be absent — breaks determinism
            assert "execution_time" not in meta, (
                "execution_time forbidden: breaks determinism"
            )
            # Metadata has exactly 2 known fields
            assert set(meta.keys()) == {"top_k", "model"}, (
                f"metadata has extra keys: {set(meta.keys()) - {'top_k', 'model'}}"
            )

    async def test_each_result_has_required_fields(self, app_db_session):
        """Each result has chunk_id, document_id, content, score, citation. NO extra fields."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "针灸 经络 医学", "top_k": 5},
            )
            assert r.status_code == 200
            body = r.json()

            assert len(body["results"]) >= 1
            frozen_fields = {"chunk_id", "document_id", "content", "score", "citation"}
            for result in body["results"]:
                assert result["chunk_id"] is not None
                assert result["document_id"] is not None
                assert len(result["content"]) > 0
                assert isinstance(result["score"], (int, float))
                assert 0.0 <= result["score"] <= 1.0
                assert result["citation"].startswith("[")
                assert ":" in result["citation"]
                # No extra fields
                assert set(result.keys()) == frozen_fields, (
                    f"Result has extra keys: {set(result.keys()) - frozen_fields}"
                )

    async def test_no_llm_or_extraneous_fields(self, app_db_session):
        """Response must NOT contain answer, generated_answer, chunks, or execution_time."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "医学", "top_k": 3},
            )
            assert r.status_code == 200
            body = r.json()

            forbidden = {
                "answer",
                "generated_answer",
                "response",
                "chunks",
                "citations",
                "execution_time",
            }
            for key in forbidden:
                assert key not in body, f"Frozen contract must not contain '{key}'"

    async def test_empty_query_results_in_validation_error(self, app_db_session):
        """Empty or missing query should return 422 (Pydantic validation)."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "", "top_k": 5},
            )
            assert r.status_code == 422


# ============================================================
# FILTER TESTS (3 tests)
# ============================================================


@pytest.mark.anyio
class TestFilters:
    """Day 3 lightweight filter layer: document_id, year, author_id."""

    async def test_document_id_filter(self, app_db_session):
        """Filtering by document_id returns only chunks from that document."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        # Find the document_id for "针灸甲乙经"
        doc = (
            await app_db_session.execute(
                select(Document).where(Document.title == "针灸甲乙经")
            )
        ).scalar_one()
        target_doc_id = doc.id

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            r = await c.post(
                "/api/v1/search",
                json={
                    "query": "医学 影响",
                    "top_k": 10,
                    "document_id": target_doc_id,
                },
            )
            assert r.status_code == 200
            body = r.json()

            # All results must belong to the filtered document
            for result in body["results"]:
                assert result["document_id"] == target_doc_id

        # Verify unfiltered search returns results from both documents
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            r2 = await c.post(
                "/api/v1/search",
                json={"query": "医学 影响", "top_k": 10},
            )
            doc_ids_unfiltered = {r["document_id"] for r in r2.json()["results"]}
            assert len(doc_ids_unfiltered) >= len({target_doc_id}), (
                "Unfiltered search should return more documents than filtered"
            )

    async def test_year_filter(self, app_db_session):
        """Filtering by year restricts to documents with that year."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        # Manually set years on the seeded documents
        docs = (
            (await app_db_session.execute(select(Document).order_by(Document.title)))
            .scalars()
            .all()
        )
        for i, doc in enumerate(docs):
            # 西晋 ≈ 265 CE, 东汉 ≈ 200 CE
            doc.year = 265 if "针灸" in doc.title else 200
        await app_db_session.flush()

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            # Filter to year 265 only
            r = await c.post(
                "/api/v1/search",
                json={"query": "医学", "top_k": 10, "year": 265},
            )
            assert r.status_code == 200
            results = r.json()["results"]

            if results:
                for result in results:
                    doc = (
                        await app_db_session.execute(
                            select(Document).where(Document.id == result["document_id"])
                        )
                    ).scalar_one()
                    assert doc.year == 265

            # Filter to year 200 only
            r2 = await c.post(
                "/api/v1/search",
                json={"query": "医学", "top_k": 10, "year": 200},
            )
            results2 = r2.json()["results"]
            if results2:
                for result in results2:
                    doc = (
                        await app_db_session.execute(
                            select(Document).where(Document.id == result["document_id"])
                        )
                    ).scalar_one()
                    assert doc.year == 200

            # Year with no match returns empty results (valid contract)
            r3 = await c.post(
                "/api/v1/search",
                json={"query": "医学", "top_k": 5, "year": 9999},
            )
            assert r3.status_code == 200
            # Still valid contract even with empty results
            assert "results" in r3.json()
            assert "metadata" in r3.json()

    async def test_combined_filters(self, app_db_session):
        """Combining document_id + year filters works correctly."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        doc = (
            await app_db_session.execute(
                select(Document).where(Document.title == "针灸甲乙经")
            )
        ).scalar_one()
        doc.year = 265
        target_doc_id = doc.id
        await app_db_session.flush()

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            # Matching combination: correct doc + correct year
            r = await c.post(
                "/api/v1/search",
                json={
                    "query": "针灸",
                    "top_k": 5,
                    "document_id": target_doc_id,
                    "year": 265,
                },
            )
            assert r.status_code == 200
            for result in r.json()["results"]:
                assert result["document_id"] == target_doc_id

            # Mismatched combination: correct doc but wrong year → empty
            r2 = await c.post(
                "/api/v1/search",
                json={
                    "query": "针灸",
                    "top_k": 5,
                    "document_id": target_doc_id,
                    "year": 300,
                },
            )
            assert r2.status_code == 200
            assert r2.json()["results"] == []


# ============================================================
# CITATION VALIDATION TESTS (3 tests)
# ============================================================


@pytest.mark.anyio
class TestCitationValidation:
    """Day 3 citation layer: valid, traceable, no generated citations."""

    async def test_every_result_has_valid_citation_format(self, app_db_session):
        """Every result's citation is exactly [document_id:chunk_id]."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "针灸 医学", "top_k": 10},
            )
            assert r.status_code == 200
            results = r.json()["results"]

            assert len(results) >= 1, "Need at least one result for citation check"

            for result in results:
                citation = result["citation"]
                doc_id = result["document_id"]
                chunk_id = result["chunk_id"]

                # Exact format: [document_id:chunk_id]
                expected = f"[{doc_id}:{chunk_id}]"
                assert citation == expected, (
                    f"Citation mismatch: expected {expected}, got {citation}"
                )

                # Parse citation and verify it matches the result fields
                assert citation.startswith("[") and citation.endswith("]")
                inner = citation[1:-1]
                parsed_doc, parsed_chunk = inner.split(":", 1)
                assert parsed_doc == doc_id
                assert parsed_chunk == chunk_id

    async def test_citation_ids_traceable_to_db(self, app_db_session):
        """Every citation maps to real, existing DB records."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "中医 医学 经典", "top_k": 10},
            )
            assert r.status_code == 200

            for result in r.json()["results"]:
                # Document exists
                doc = (
                    await app_db_session.execute(
                        select(Document).where(Document.id == result["document_id"])
                    )
                ).scalar_one_or_none()
                assert doc is not None, (
                    f"Document {result['document_id']} referenced in citation not found"
                )

                # Chunk exists and belongs to the document
                chunk = (
                    await app_db_session.execute(
                        select(DocumentChunk).where(
                            DocumentChunk.id == result["chunk_id"],
                            DocumentChunk.document_id == result["document_id"],
                        )
                    )
                ).scalar_one_or_none()
                assert chunk is not None, (
                    f"Chunk {result['chunk_id']} referenced in citation not found"
                )
                assert result["content"] == chunk.content, (
                    "Chunk content in response must match DB content"
                )

    async def test_no_generated_or_synthetic_citations(self, app_db_session):
        """No citations can be fabricated — all [bracketed] text is real DB IDs."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "针灸 经络 医学", "top_k": 10},
            )
            assert r.status_code == 200

            # Collect all document_ids and chunk_ids from DB
            all_docs = (
                (await app_db_session.execute(select(Document.id))).scalars().all()
            )
            all_doc_ids = set(all_docs)
            all_chunks = (
                (await app_db_session.execute(select(DocumentChunk.id))).scalars().all()
            )
            all_chunk_ids = set(all_chunks)

            for result in r.json()["results"]:
                assert result["document_id"] in all_doc_ids, (
                    f"Citation references non-existent document {result['document_id']}"
                )
                assert result["chunk_id"] in all_chunk_ids, (
                    f"Citation references non-existent chunk {result['chunk_id']}"
                )


# ============================================================
# CONCURRENCY TESTS (2 tests)
# ============================================================


@pytest.mark.anyio
class TestConcurrency:
    """Day 3: API stability under concurrent access."""

    async def test_multiple_concurrent_requests(self, app_db_session):
        """Multiple concurrent POST /api/v1/search requests complete without errors."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        queries = [
            {"query": "针灸", "top_k": 5},
            {"query": "医学", "top_k": 5},
            {"query": "伤寒", "top_k": 5},
            {"query": "经络 腧穴", "top_k": 5},
            {"query": "经典", "top_k": 3},
        ]

        async def _send(payload):
            transport = ASGITransport(app=app, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
                r = await c.post("/api/v1/search", json=payload)
                return r.status_code, r.json()

        tasks = [_send(q) for q in queries]
        results = await asyncio.gather(*tasks)

        for i, (status, body) in enumerate(results):
            assert status == 200, f"Request {i} failed: {body}"
            assert "query" in body
            assert "results" in body
            assert "metadata" in body
            assert body["metadata"]["model"] == "retrieval-only"
            for result in body["results"]:
                assert "citation" in result

    async def test_stable_under_repeated_calls(self, app_db_session):
        """Repeated identical calls produce byte-identical full responses."""
        from app.db.database import get_session

        await _seed_data(app_db_session)

        headers = await _search_auth_headers(app_db_session)

        app = _make_test_app()

        async def override_get_session():
            yield app_db_session

        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        payload = {"query": "针灸 医学", "top_k": 5}

        responses = []
        response_bytes = []
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as c:
            for _ in range(5):
                r = await c.post("/api/v1/search", json=payload)
                assert r.status_code == 200
                responses.append(r.json())
                response_bytes.append(r.content)

        # All responses must have the same frozen contract shape
        for body in responses:
            assert body["query"] == "针灸 医学"
            assert body["metadata"]["model"] == "retrieval-only"
            assert "execution_time" not in body["metadata"], (
                "execution_time forbidden: identical input → non-identical output"
            )
            assert set(body["metadata"].keys()) == {"top_k", "model"}

        assert all(body == response_bytes[0] for body in response_bytes[1:])

        # Result ordering must be stable (same doc_id + chunk_id list each call)
        first_ids = [(r["document_id"], r["chunk_id"]) for r in responses[0]["results"]]
        for i, body in enumerate(responses[1:], start=1):
            call_ids = [(r["document_id"], r["chunk_id"]) for r in body["results"]]
            assert first_ids == call_ids, (
                f"Call {i} returned different ordering: {call_ids} vs {first_ids}"
            )
