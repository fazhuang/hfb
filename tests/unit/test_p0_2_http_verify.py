"""P0-2: HTTP verify_relation tests — reviewer identity through real auth.

Tests:
  - No token → 401
  - Normal user token → 403
  - Reviewer token → 200, verified_by == token user ID in DB
  - Admin token → 200
  - Spoofed verified_by in body → 422
  - Reviewer deactivated → existing edges excluded at query time
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app as fastapi_app
from app.models.book import Book
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.graph import EntityRelation
from app.models.passage import Passage
from app.models.person import Person
from app.models.version import Version
from app.models.user import User, Role, Permission
from app.schemas.graph import GraphEvidence
from app.services.auth_service import create_access_token
from app.services.graph_service import GraphService
from tests.conftest_db import db_session  # noqa: F401


async def _make_corpus(session: AsyncSession) -> dict:
    """Minimal corpus for verify_relation HTTP tests."""
    person = Person(name="皇甫谧", name_zh="皇甫谧")
    session.add(person)
    await session.flush()

    book = Book(title="针灸甲乙经")
    session.add(book)
    await session.flush()

    # Passage requires Chapter FK — seed a minimal chapter first
    from app.models.chapter import Chapter

    chapter = Chapter(id="chap-verify", book_id=book.id, title="卷一", order=1)
    session.add(chapter)
    await session.flush()

    version = Version(
        id="ver-verify",
        book_id=book.id,
        version_name="宋本",
        era="宋",
    )
    session.add(version)
    await session.flush()

    passage = Passage(
        id="passage-verify",
        chapter_id=chapter.id,
        version_id=version.id,
        order=1,
        content_text="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
    )
    session.add(passage)
    await session.flush()

    doc = Document(title="晋书", content_text="皇甫谧，字士安。撰《针灸甲乙经》。")
    session.add(doc)
    await session.flush()

    chunk = DocumentChunk(
        id="chunk-verify",
        document_id=doc.id,
        content="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        chunk_index=0,
        passage_id=passage.id,
    )
    session.add(chunk)
    await session.flush()

    return {
        "person": person,
        "book": book,
        "doc": doc,
        "chunk": chunk,
        "version": version,
        "passage": passage,
    }


async def _make_relation(session: AsyncSession, seed: dict) -> str:
    svc = GraphService(session)
    ev = GraphEvidence(
        document_id=seed["doc"].id,
        chunk_id=seed["chunk"].id,
        exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
    )
    rel = await svc.create_relation(
        source_entity_type="person",
        source_entity_id=seed["person"].id,
        target_entity_type="book",
        target_entity_id=seed["book"].id,
        relation_type="compiled",
        description="皇甫谧编撰《针灸甲乙经》",
        evidence=ev,
    )
    return rel.id


async def _seed_user(
    session: AsyncSession,
    user_id: str,
    username: str,
    *,
    is_active: bool = True,
    is_superuser: bool = False,
    permissions: list[tuple[str, str]] | None = None,
) -> str:
    """Seed a user with optional permissions. Returns the user ID."""
    user = User(
        id=user_id,
        username=username,
        email=f"{username}@{uuid.uuid4().hex[:8]}.test",
        hashed_password="test",
        is_active=is_active,
        is_superuser=is_superuser,
    )
    session.add(user)
    await session.flush()

    if permissions and not is_superuser:
        role = Role(
            id=f"role-{user_id}",
            name=f"Role-{username}",
            is_system=True,
        )
        session.add(role)
        await session.flush()

        from app.models.user import user_role as ur_table, role_permission as rp_table

        await session.execute(
            ur_table.insert().values(user_id=user.id, role_id=role.id)
        )

        for resource, action in permissions:
            perm = Permission(
                id=f"perm-{user_id}-{resource}-{action}",
                resource=resource,
                action=action,
            )
            session.add(perm)
            await session.flush()
            await session.execute(
                rp_table.insert().values(role_id=role.id, permission_id=perm.id)
            )

    await session.flush()
    return user.id


def _setup_overrides(session: AsyncSession, token: str | None = None) -> None:
    """Wire FastAPI dependency overrides. token=None = no auth (401)."""
    from app.db.database import get_session
    from app.middleware import auth as auth_mod

    async def override_get_session():
        yield session

    fastapi_app.dependency_overrides[get_session] = override_get_session

    if token is not None:

        async def override_get_current_user(request=None):
            from app.services.auth_service import decode_token

            payload = decode_token(token)
            return payload["sub"]

        async def override_get_auth_service():
            from app.services.auth_service import AuthService

            svc = AuthService(session)

            class _A:
                async def has_permission(self, uid, r, a):
                    return await svc.has_permission(uid, r, a)

                async def has_any_permission(self, uid, *p):
                    return await svc.has_any_permission(uid, *p)

            return _A()

        fastapi_app.dependency_overrides[auth_mod.get_current_user] = (
            override_get_current_user
        )
        fastapi_app.dependency_overrides[auth_mod.get_auth_service] = (
            override_get_auth_service
        )


def _cleanup_overrides() -> None:
    fastapi_app.dependency_overrides.clear()


VERIFY_BODY: dict[str, str] = {
    "claim_text": "皇甫谧编撰《针灸甲乙经》",
}


@pytest.mark.asyncio
class TestHTTPVerifyRelation:
    """P0-2: HTTP verify_relation security boundary."""

    async def test_no_token_returns_401(self, db_session: AsyncSession) -> None:
        """Request without token must return 401."""
        seed = await _make_corpus(db_session)
        rel_id = await _make_relation(db_session, seed)

        body = {**VERIFY_BODY}
        body.update(
            {
                "evidence_document_id": seed["doc"].id,
                "evidence_version_id": seed["version"].id,
                "evidence_passage_id": seed["passage"].id,
                "evidence_chunk_id": seed["chunk"].id,
                "evidence_quote": seed["chunk"].content,
                "evidence_source_uri": "https://ctext.org/jinshu/huangfu-mi-zhuan",
            }
        )

        _setup_overrides(db_session, token=None)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/api/v1/graph/relations/{rel_id}/verify",
                    json=body,
                )
                assert resp.status_code == 401, (
                    f"Expected 401, got {resp.status_code}: {resp.text}"
                )
        finally:
            _cleanup_overrides()

    async def test_normal_user_returns_403(self, db_session: AsyncSession) -> None:
        """User without graph.review or graph.approve must get 403."""
        uid = f"normal-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid)
        seed = await _make_corpus(db_session)
        rel_id = await _make_relation(db_session, seed)

        body = {**VERIFY_BODY}
        body.update(
            {
                "evidence_document_id": seed["doc"].id,
                "evidence_version_id": seed["version"].id,
                "evidence_passage_id": seed["passage"].id,
                "evidence_chunk_id": seed["chunk"].id,
                "evidence_quote": seed["chunk"].content,
                "evidence_source_uri": "https://ctext.org/jinshu/huangfu-mi-zhuan",
            }
        )

        token = create_access_token(uid)
        _setup_overrides(db_session, token=token)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/api/v1/graph/relations/{rel_id}/verify",
                    json=body,
                )
                assert resp.status_code == 403, (
                    f"Expected 403, got {resp.status_code}: {resp.text}"
                )
        finally:
            _cleanup_overrides()

    async def test_reviewer_token_succeeds(self, db_session: AsyncSession) -> None:
        """Reviewer user with graph.review permission gets 200."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)
        rel_id = await _make_relation(db_session, seed)

        body = {**VERIFY_BODY}
        body.update(
            {
                "evidence_document_id": seed["doc"].id,
                "evidence_version_id": seed["version"].id,
                "evidence_passage_id": seed["passage"].id,
                "evidence_chunk_id": seed["chunk"].id,
                "evidence_quote": seed["chunk"].content,
                "evidence_source_uri": "https://ctext.org/jinshu/huangfu-mi-zhuan",
            }
        )

        token = create_access_token(uid)
        _setup_overrides(db_session, token=token)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/api/v1/graph/relations/{rel_id}/verify",
                    json=body,
                )
                assert resp.status_code == 200, (
                    f"Expected 200, got {resp.status_code}: {resp.text}"
                )
                payload = resp.json()
                assert payload["success"] is True
                assert (
                    payload["data"]["evidence"]["claim_text"]
                    == "皇甫谧编撰《针灸甲乙经》"
                )
        finally:
            _cleanup_overrides()

        # Verify DB: verified_by must equal the JWT user ID
        rel = await db_session.get(EntityRelation, rel_id)
        assert rel.evidence_status == "verified"
        assert rel.verified_by == uid, (
            f"Expected verified_by='{uid}', got '{rel.verified_by}'"
        )

    async def test_admin_token_succeeds(self, db_session: AsyncSession) -> None:
        """Admin superuser gets 200."""
        uid = f"adm-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, is_superuser=True)
        seed = await _make_corpus(db_session)
        rel_id = await _make_relation(db_session, seed)

        body = {**VERIFY_BODY}
        body.update(
            {
                "evidence_document_id": seed["doc"].id,
                "evidence_version_id": seed["version"].id,
                "evidence_passage_id": seed["passage"].id,
                "evidence_chunk_id": seed["chunk"].id,
                "evidence_quote": seed["chunk"].content,
                "evidence_source_uri": "https://ctext.org/jinshu/huangfu-mi-zhuan",
            }
        )

        token = create_access_token(uid)
        _setup_overrides(db_session, token=token)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/api/v1/graph/relations/{rel_id}/verify",
                    json=body,
                )
                assert resp.status_code == 200, (
                    f"Expected 200, got {resp.status_code}: {resp.text}"
                )
        finally:
            _cleanup_overrides()

        rel = await db_session.get(EntityRelation, rel_id)
        assert rel.evidence_status == "verified"
        assert rel.verified_by == uid

    async def test_spoofed_verified_by_returns_422(
        self, db_session: AsyncSession
    ) -> None:
        """Request body with verified_by field must be rejected with 422."""
        uid = f"rv2-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)
        rel_id = await _make_relation(db_session, seed)

        body = {**VERIFY_BODY}
        body.update(
            {
                "evidence_document_id": seed["doc"].id,
                "evidence_version_id": seed["version"].id,
                "evidence_passage_id": seed["passage"].id,
                "evidence_chunk_id": seed["chunk"].id,
                "evidence_quote": seed["chunk"].content,
                "evidence_source_uri": "https://ctext.org/jinshu/huangfu-mi-zhuan",
                "verified_by": "attacker-id",
            }
        )

        token = create_access_token(uid)
        _setup_overrides(db_session, token=token)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/api/v1/graph/relations/{rel_id}/verify",
                    json=body,
                )
                assert resp.status_code == 422, (
                    f"Expected 422 for spoofed verified_by, got {resp.status_code}: {resp.text}"
                )
        finally:
            _cleanup_overrides()

    async def test_deactivated_reviewer_edges_excluded(
        self, db_session: AsyncSession
    ) -> None:
        """After reviewer is deactivated, existing verified edges excluded from queries."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)
        rel_id = await _make_relation(db_session, seed)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        verified = await svc.verify_relation(
            relation_id=rel_id,
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_document_id=ev.document_id,
            evidence_version_id=seed["version"].id,
            evidence_passage_id=seed["passage"].id,
            evidence_chunk_id=ev.chunk_id,
            evidence_quote=ev.exact_quote,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
            verified_by=uid,
        )
        assert verified.evidence_status == "verified"

        # Deactivate the reviewer
        user = await db_session.get(User, uid)
        user.is_active = False
        await db_session.flush()

        # Query-time: find_paths must exclude this edge
        paths = await svc.find_paths(
            source_type="person",
            source_id=seed["person"].id,
            target_type="book",
            target_id=seed["book"].id,
            max_depth=3,
            max_paths=10,
        )
        assert len(paths) == 0, (
            f"Deactivated reviewer's edges must be excluded. Got {len(paths)} paths."
        )

        # get_validated_relations_for_entity must also exclude
        validated = await svc.get_validated_relations_for_entity(
            "person", seed["person"].id
        )
        assert len(validated) == 0, (
            f"Deactivated reviewer's edges must be excluded. Got {len(validated)}."
        )

    async def test_mismatched_chunk_passage_rejected(
        self, db_session: AsyncSession
    ) -> None:
        """Chunk → Passage mismatch: verify_relation must reject."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)

        # Create a second passage linked to a different version
        v2 = Version(
            id="ver-v2",
            book_id=seed["book"].id,
            version_name="明本",
            era="明",
        )
        db_session.add(v2)
        await db_session.flush()

        from app.models.passage import Passage as P
        from app.models.chapter import Chapter

        ch2 = Chapter(
            id="chap-mismatch", book_id=seed["book"].id, title="卷二", order=2
        )
        db_session.add(ch2)
        await db_session.flush()

        bad_passage = P(
            id="passage-mismatch",
            chapter_id=ch2.id,
            version_id=v2.id,
            order=2,
            content_text="不同段落",
        )
        db_session.add(bad_passage)
        await db_session.flush()

        rel_id = await _make_relation(db_session, seed)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        # bad_passage linked to v2 but seed["chunk"].passage_id == seed["passage"].id
        # Default-deny catches Chunk→Passage mismatch FIRST
        with pytest.raises(ValueError, match="not claimed passage"):
            await svc.verify_relation(
                relation_id=rel_id,
                claim_text="皇甫谧编撰《针灸甲乙经》",
                evidence_document_id=ev.document_id,
                evidence_version_id=seed["version"].id,
                evidence_passage_id=bad_passage.id,
                evidence_chunk_id=ev.chunk_id,
                evidence_quote=ev.exact_quote,
                evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
                verified_by=uid,
            )

    async def test_mismatched_passage_version_rejected(
        self, db_session: AsyncSession
    ) -> None:
        """Passage → Version mismatch: verify_relation must reject."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)

        # Create a second version
        v2 = Version(
            id="ver-mismatch",
            book_id=seed["book"].id,
            version_name="明本",
            era="明",
        )
        db_session.add(v2)
        await db_session.flush()

        rel_id = await _make_relation(db_session, seed)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        with pytest.raises(ValueError, match="linked to version"):
            await svc.verify_relation(
                relation_id=rel_id,
                claim_text="皇甫谧编撰《针灸甲乙经》",
                evidence_document_id=ev.document_id,
                evidence_version_id=v2.id,
                evidence_passage_id=seed["passage"].id,
                evidence_chunk_id=ev.chunk_id,
                evidence_quote=ev.exact_quote,
                evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
                verified_by=uid,
            )


# ======================================================================
# P0-4: Provenance hierarchy isolation tests
# ======================================================================


@pytest.mark.asyncio
class TestProvenanceHierarchyIsolation:
    """P0-4: Each test triggers exactly ONE failure reason in the chain."""

    async def test_null_chunk_passage_rejected(self, db_session: AsyncSession) -> None:
        """chunk.passage_id=NULL, valid Passage and Version → reject."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)

        # Nullify chunk.passage_id to trigger default-deny
        seed["chunk"].passage_id = None
        await db_session.flush()

        rel_id = await _make_relation(db_session, seed)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        with pytest.raises(ValueError, match="no passage_id"):
            await svc.verify_relation(
                relation_id=rel_id,
                claim_text="皇甫谧编撰《针灸甲乙经》",
                evidence_document_id=ev.document_id,
                evidence_version_id=seed["version"].id,
                evidence_passage_id=seed["passage"].id,
                evidence_chunk_id=ev.chunk_id,
                evidence_quote=ev.exact_quote,
                evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
                verified_by=uid,
            )

    async def test_mismatched_chunk_passage_rejected(
        self, db_session: AsyncSession
    ) -> None:
        """Chunk belongs to Passage A, submit Passage B. Passage B→Version matches → reject on Chunk→Passage only."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)

        # Create Passage B belonging to same Version A (so Passage→Version is fine)
        from app.models.passage import Passage as P

        passage_b = P(
            id="passage-b-isolation",
            chapter_id="chap-verify",
            version_id=seed["version"].id,
            order=99,
            content_text="Different passage for Chunk→Passage mismatch test.",
        )
        db_session.add(passage_b)
        await db_session.flush()

        rel_id = await _make_relation(db_session, seed)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        # chunk.passage_id == seed["passage"].id, but we submit passage_b.id
        with pytest.raises(ValueError, match="not claimed passage"):
            await svc.verify_relation(
                relation_id=rel_id,
                claim_text="皇甫谧编撰《针灸甲乙经》",
                evidence_document_id=ev.document_id,
                evidence_version_id=seed["version"].id,
                evidence_passage_id=passage_b.id,
                evidence_chunk_id=ev.chunk_id,
                evidence_quote=ev.exact_quote,
                evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
                verified_by=uid,
            )

    async def test_mismatched_passage_version_rejected(
        self, db_session: AsyncSession
    ) -> None:
        """Chunk→Passage matches, Passage→Version mismatches → reject."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)

        # Create Version B (different from Passage's version)
        v2 = Version(
            id="ver-isolation-mismatch",
            book_id=seed["book"].id,
            version_name="明本",
            era="明",
        )
        db_session.add(v2)
        await db_session.flush()

        rel_id = await _make_relation(db_session, seed)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        with pytest.raises(ValueError, match="not claimed version"):
            await svc.verify_relation(
                relation_id=rel_id,
                claim_text="皇甫谧编撰《针灸甲乙经》",
                evidence_document_id=ev.document_id,
                evidence_version_id=v2.id,
                evidence_passage_id=seed["passage"].id,
                evidence_chunk_id=ev.chunk_id,
                evidence_quote=ev.exact_quote,
                evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
                verified_by=uid,
            )

    async def test_valid_chunk_passage_version_chain_succeeds(
        self, db_session: AsyncSession
    ) -> None:
        """Chunk→Passage→Version fully consistent → verify succeeds."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)
        rel_id = await _make_relation(db_session, seed)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        verified = await svc.verify_relation(
            relation_id=rel_id,
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_document_id=ev.document_id,
            evidence_version_id=seed["version"].id,
            evidence_passage_id=seed["passage"].id,
            evidence_chunk_id=ev.chunk_id,
            evidence_quote=ev.exact_quote,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
            verified_by=uid,
        )
        assert verified.evidence_status == "verified"

    async def test_tampered_provenance_excluded_at_query_time(
        self, db_session: AsyncSession
    ) -> None:
        """Create verified relation, then DB-tamper evidence_passage_id → excluded from all queries."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)
        rel_id = await _make_relation(db_session, seed)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        verified = await svc.verify_relation(
            relation_id=rel_id,
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_document_id=ev.document_id,
            evidence_version_id=seed["version"].id,
            evidence_passage_id=seed["passage"].id,
            evidence_chunk_id=ev.chunk_id,
            evidence_quote=ev.exact_quote,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
            verified_by=uid,
        )
        assert verified.evidence_status == "verified"

        # Direct DB tamper: overwrite evidence_passage_id to garbage
        from app.models.graph import EntityRelation

        rel = await db_session.get(EntityRelation, rel_id)
        rel.evidence_passage_id = "tampered-passage-id"
        await db_session.flush()

        # find_paths must exclude
        paths = await svc.find_paths(
            source_type="person",
            source_id=seed["person"].id,
            target_type="book",
            target_id=seed["book"].id,
            max_depth=3,
            max_paths=10,
        )
        assert len(paths) == 0, (
            f"Tampered provenance must be excluded from find_paths. Got {len(paths)} paths."
        )

        # neighbors must exclude
        neighbors = await svc.get_neighbors("person", seed["person"].id)
        person_edges = [e for e in neighbors.edges if e.source_id.startswith("person:")]
        assert len(person_edges) == 0, (
            "Tampered provenance must be excluded from neighbors."
        )

        # get_validated_relations_for_entity must exclude
        validated = await svc.get_validated_relations_for_entity(
            "person", seed["person"].id
        )
        assert len(validated) == 0, (
            f"Tampered provenance must be excluded from validated relations. Got {len(validated)}."
        )

    async def test_tampered_both_provenance_ids_null_excluded(
        self, db_session: AsyncSession
    ) -> None:
        """Blocking-1: verified relation with both provenance IDs set to NULL → excluded.

        Steps:
        1. Create legal Chunk→Passage→Version chain
        2. Verify through verify_relation() — keeps evidence_status='verified'
        3. Set evidence_passage_id=NULL, evidence_version_id=NULL in DB
        4. Provenance fields become empty strings → _validate_provenance_hierarchy rejects
        5. find_paths, neighbors, get_validated_relations_for_entity all exclude
        """
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        seed = await _make_corpus(db_session)
        rel_id = await _make_relation(db_session, seed)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        verified = await svc.verify_relation(
            relation_id=rel_id,
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_document_id=ev.document_id,
            evidence_version_id=seed["version"].id,
            evidence_passage_id=seed["passage"].id,
            evidence_chunk_id=ev.chunk_id,
            evidence_quote=ev.exact_quote,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
            verified_by=uid,
        )
        assert verified.evidence_status == "verified"

        # Direct DB tamper: set BOTH provenance IDs to None
        # Keep evidence_status='verified', verified_by, verified_at, claim_text, source_uri unchanged
        from app.models.graph import EntityRelation

        rel = await db_session.get(EntityRelation, rel_id)
        rel.evidence_passage_id = None
        rel.evidence_version_id = None
        await db_session.flush()

        # find_paths must exclude
        paths = await svc.find_paths(
            source_type="person",
            source_id=seed["person"].id,
            target_type="book",
            target_id=seed["book"].id,
            max_depth=3,
            max_paths=10,
        )
        assert len(paths) == 0, (
            f"Double-NULL provenance must be excluded from find_paths. Got {len(paths)} paths."
        )

        # neighbors must exclude
        neighbors = await svc.get_neighbors("person", seed["person"].id)
        person_edges = [e for e in neighbors.edges if e.source_id.startswith("person:")]
        assert len(person_edges) == 0, (
            "Double-NULL provenance must be excluded from neighbors."
        )

        # get_validated_relations_for_entity must exclude
        validated = await svc.get_validated_relations_for_entity(
            "person", seed["person"].id
        )
        assert len(validated) == 0, (
            f"Double-NULL provenance must be excluded from validated relations. Got {len(validated)}."
        )


# ======================================================================
# P0-5: Source URI and treats regression tests
# ======================================================================


@pytest.mark.asyncio
class TestSourceURIValidation:
    """P0-5: Source URI acceptance/rejection policy."""

    async def _make_verified_relation(self, db_session, uid, source_uri):
        """Helper: create + verify with given source_uri. Returns relation or raises."""
        seed = await _make_corpus(db_session)
        rel_id = await _make_relation(db_session, seed)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        return await svc.verify_relation(
            relation_id=rel_id,
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_document_id=ev.document_id,
            evidence_version_id=seed["version"].id,
            evidence_passage_id=seed["passage"].id,
            evidence_chunk_id=ev.chunk_id,
            evidence_quote=ev.exact_quote,
            evidence_source_uri=source_uri,
            verified_by=uid,
        )

    async def test_attacker_invalid_rejected(self, db_session: AsyncSession) -> None:
        """https://attacker.invalid/fake-source → reject."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        with pytest.raises(ValueError, match="not in the allowed"):
            await self._make_verified_relation(
                db_session, uid, "https://attacker.invalid/fake-source"
            )

    async def test_ctext_org_accepted(self, db_session: AsyncSession) -> None:
        """https://ctext.org/x → pass."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        rel = await self._make_verified_relation(db_session, uid, "https://ctext.org/x")
        assert rel.evidence_status == "verified"

    async def test_evilctext_org_rejected(self, db_session: AsyncSession) -> None:
        """https://evilctext.org/x → reject."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        with pytest.raises(ValueError, match="not in the allowed"):
            await self._make_verified_relation(
                db_session, uid, "https://evilctext.org/x"
            )

    async def test_sub_ctext_org_accepted(self, db_session: AsyncSession) -> None:
        """https://sub.ctext.org/x → pass (legitimate subdomain)."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        rel = await self._make_verified_relation(
            db_session, uid, "https://sub.ctext.org/x"
        )
        assert rel.evidence_status == "verified"

    async def test_userinfo_rejected(self, db_session: AsyncSession) -> None:
        """https://user@ctext.org/x → reject."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        with pytest.raises(ValueError, match="userinfo"):
            await self._make_verified_relation(
                db_session, uid, "https://user@ctext.org/x"
            )

    async def test_http_rejected(self, db_session: AsyncSession) -> None:
        """http://ctext.org/x → reject (must be https)."""
        uid = f"rev-{uuid.uuid4().hex[:8]}"
        await _seed_user(db_session, uid, uid, permissions=[("graph", "review")])
        with pytest.raises(ValueError, match="https"):
            await self._make_verified_relation(db_session, uid, "http://ctext.org/x")


@pytest.mark.asyncio
class TestTreatsEvidencePolicy:
    """P0-5: treats relation semantic evidence policy."""

    async def _seed_tcm_entities(self, db_session: AsyncSession) -> dict:
        """Seed herb + symptom entities and supporting graph structure."""
        from app.models.tcm_entity import TCMEntity
        from app.models.user import User, Role, Permission
        from app.models.user import user_role as ur_table
        from app.models.user import role_permission as rp_table

        # Reviewer
        reviewer = User(
            id="reviewer-treats",
            username="reviewer-treats",
            email="reviewer-treats@test.test",
            hashed_password="test",
            is_active=True,
        )
        db_session.add(reviewer)
        await db_session.flush()
        role = Role(id="role-treats", name="ReviewerTreats", is_system=True)
        db_session.add(role)
        await db_session.flush()
        perm = Permission(id="perm-treats", resource="graph", action="review")
        db_session.add(perm)
        await db_session.flush()
        await db_session.execute(
            ur_table.insert().values(user_id=reviewer.id, role_id=role.id)
        )
        await db_session.execute(
            rp_table.insert().values(role_id=role.id, permission_id=perm.id)
        )
        await db_session.flush()

        # Herb: 黄芪 with aliases
        herb = TCMEntity(
            entity_type="herb",
            name="黄芪",
            name_zh="黃芪",
            properties={"aliases": ["绵黄耆", "黄耆"]},
        )
        db_session.add(herb)
        await db_session.flush()

        # Symptom: 头痛 with aliases
        symptom = TCMEntity(
            entity_type="symptom",
            name="头痛",
            name_zh="頭痛",
            properties={"aliases": ["头风", "头疼"]},
        )
        db_session.add(symptom)
        await db_session.flush()

        # Document + passage + version + chunk for evidence
        doc = Document(
            title="本草纲目",
            dynasty="明",
            category="本草",
            content_text="黄芪主治头痛及气虚。",
        )
        db_session.add(doc)
        await db_session.flush()

        book = Book(title="本草纲目", dynasty="明", category="本草")
        db_session.add(book)
        await db_session.flush()

        from app.models.chapter import Chapter

        chapter = Chapter(id="chap-treats", book_id=book.id, title="卷一", order=1)
        db_session.add(chapter)
        await db_session.flush()

        ver = Version(id="ver-treats", book_id=book.id, version_name="金陵本", era="明")
        db_session.add(ver)
        await db_session.flush()

        passage = Passage(
            id="passage-treats",
            chapter_id="chap-treats",
            version_id=ver.id,
            order=1,
            content_text="黄芪主治头痛及气虚。",
        )
        db_session.add(passage)
        await db_session.flush()

        chunk = DocumentChunk(
            id="chunk-treats",
            document_id=doc.id,
            chunk_index=0,
            content="黄芪主治头痛及气虚。",
            token_count=10,
            passage_id=passage.id,
        )
        db_session.add(chunk)
        await db_session.flush()

        return {
            "herb": herb,
            "symptom": symptom,
            "doc": doc,
            "ver": ver,
            "passage": passage,
            "chunk": chunk,
            "reviewer_id": reviewer.id,
        }

    async def test_treats_biography_rejected(self, db_session: AsyncSession) -> None:
        """'本草记载黄芪性温' → reject: no symptom term in quote."""
        seed = await self._seed_tcm_entities(db_session)

        # Use quote from chunk that mentions source but NOT target symptom
        seed["chunk"].content = "本草记载黄芪性温。"
        await db_session.flush()

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="本草记载黄芪性温。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        rel = await svc.create_relation(
            source_entity_type="herb",
            source_entity_id=seed["herb"].id,
            target_entity_type="symptom",
            target_entity_id=seed["symptom"].id,
            relation_type="treats",
            description="黄芪治疗头痛",
            evidence=ev,
        )
        with pytest.raises(ValueError, match="Semantic evidence policy violation"):
            await svc.verify_relation(
                relation_id=rel.id,
                claim_text="黄芪治疗头痛",
                evidence_document_id=ev.document_id,
                evidence_version_id=seed["ver"].id,
                evidence_passage_id=seed["passage"].id,
                evidence_chunk_id=ev.chunk_id,
                evidence_quote=ev.exact_quote,
                evidence_source_uri="https://ctext.org/bencao-gangmu/huangqi",
                verified_by=seed["reviewer_id"],
            )

    async def test_treats_valid_passes(self, db_session: AsyncSession) -> None:
        """'黄芪主治头痛' → pass: both terms in quote."""
        seed = await self._seed_tcm_entities(db_session)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="黄芪主治头痛及气虚。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        rel = await svc.create_relation(
            source_entity_type="herb",
            source_entity_id=seed["herb"].id,
            target_entity_type="symptom",
            target_entity_id=seed["symptom"].id,
            relation_type="treats",
            description="黄芪治疗头痛",
            evidence=ev,
        )
        verified = await svc.verify_relation(
            relation_id=rel.id,
            claim_text="黄芪主治头痛",
            evidence_document_id=ev.document_id,
            evidence_version_id=seed["ver"].id,
            evidence_passage_id=seed["passage"].id,
            evidence_chunk_id=ev.chunk_id,
            evidence_quote=ev.exact_quote,
            evidence_source_uri="https://ctext.org/bencao-gangmu/huangqi",
            verified_by=seed["reviewer_id"],
        )
        assert verified.evidence_status == "verified"

    async def test_treats_generic_term_rejected(self, db_session: AsyncSession) -> None:
        """'可治之' → reject: no specific entity terms."""
        seed = await self._seed_tcm_entities(db_session)

        # Quote mentions source (黄芪) but not target (头痛) — generic "之"
        seed["chunk"].content = "黄芪可治之。"
        await db_session.flush()

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="黄芪可治之。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        rel = await svc.create_relation(
            source_entity_type="herb",
            source_entity_id=seed["herb"].id,
            target_entity_type="symptom",
            target_entity_id=seed["symptom"].id,
            relation_type="treats",
            description="黄芪治疗头痛",
            evidence=ev,
        )
        with pytest.raises(ValueError, match="must mention the target symptom"):
            await svc.verify_relation(
                relation_id=rel.id,
                claim_text="黄芪可治之",
                evidence_document_id=ev.document_id,
                evidence_version_id=seed["ver"].id,
                evidence_passage_id=seed["passage"].id,
                evidence_chunk_id=ev.chunk_id,
                evidence_quote=ev.exact_quote,
                evidence_source_uri="https://ctext.org/bencao-gangmu/huangqi",
                verified_by=seed["reviewer_id"],
            )

    async def test_treats_alias_match_passes(self, db_session: AsyncSession) -> None:
        """Register alias '绵黄耆/头风', quote uses aliases → pass."""
        seed = await self._seed_tcm_entities(db_session)

        # Use alias terms in quote
        seed["chunk"].content = "绵黄耆治头风甚效。"
        await db_session.flush()

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="绵黄耆治头风甚效。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        rel = await svc.create_relation(
            source_entity_type="herb",
            source_entity_id=seed["herb"].id,
            target_entity_type="symptom",
            target_entity_id=seed["symptom"].id,
            relation_type="treats",
            description="黄芪治疗头痛",
            evidence=ev,
        )
        verified = await svc.verify_relation(
            relation_id=rel.id,
            claim_text="绵黄耆治头风",
            evidence_document_id=ev.document_id,
            evidence_version_id=seed["ver"].id,
            evidence_passage_id=seed["passage"].id,
            evidence_chunk_id=ev.chunk_id,
            evidence_quote=ev.exact_quote,
            evidence_source_uri="https://ctext.org/bencao-gangmu/huangqi",
            verified_by=seed["reviewer_id"],
        )
        assert verified.evidence_status == "verified"

    async def test_tampered_treats_excluded_at_query(
        self, db_session: AsyncSession
    ) -> None:
        """Blocking-2: re-validate treats semantic policy at query time.

        Quote is changed so it no longer contains target symptom '头痛',
        but evidence_status, provenance, citation, reviewer all stay valid.
        Exclusion must come from RelationEvidencePolicy, not from status/provenance/citation.
        """
        seed = await self._seed_tcm_entities(db_session)

        svc = GraphService(db_session)
        ev = GraphEvidence(
            document_id=seed["doc"].id,
            chunk_id=seed["chunk"].id,
            exact_quote="黄芪主治头痛及气虚。",
            citation=f"[{seed['doc'].id}:{seed['chunk'].id}]",
        )
        rel = await svc.create_relation(
            source_entity_type="herb",
            source_entity_id=seed["herb"].id,
            target_entity_type="symptom",
            target_entity_id=seed["symptom"].id,
            relation_type="treats",
            description="黄芪治疗头痛",
            evidence=ev,
        )
        verified = await svc.verify_relation(
            relation_id=rel.id,
            claim_text="黄芪主治头痛",
            evidence_document_id=ev.document_id,
            evidence_version_id=seed["ver"].id,
            evidence_passage_id=seed["passage"].id,
            evidence_chunk_id=ev.chunk_id,
            evidence_quote=ev.exact_quote,
            evidence_source_uri="https://ctext.org/bencao-gangmu/huangqi",
            verified_by=seed["reviewer_id"],
        )
        assert verified.evidence_status == "verified"

        # Verify it's visible before tampering
        paths_before = await svc.find_paths(
            source_type="herb",
            source_id=seed["herb"].id,
            target_type="symptom",
            target_id=seed["symptom"].id,
            max_depth=3,
            max_paths=10,
        )
        assert len(paths_before) == 1

        # Tamper: change chunk content + evidence_quote so the quote no longer
        # contains target symptom "头痛".  Keep evidence_status, verified_by,
        # verified_at, provenance chain, source_uri, and citation all valid.
        # Exclusion must come from RelationEvidencePolicy (target term missing).
        seed["chunk"].content = "本草记载黄芪性温。"
        await db_session.flush()

        from app.models.graph import EntityRelation

        rel_db = await db_session.get(EntityRelation, rel.id)
        rel_db.evidence_quote = "本草记载黄芪性温。"
        await db_session.flush()

        # Now must be excluded — because query-time semantic re-validation fails
        paths_after = await svc.find_paths(
            source_type="herb",
            source_id=seed["herb"].id,
            target_type="symptom",
            target_id=seed["symptom"].id,
            max_depth=3,
            max_paths=10,
        )
        assert len(paths_after) == 0, (
            "Tampered treats quote must be excluded from find_paths."
        )

        # neighbors must also exclude
        neighbors = await svc.get_neighbors("herb", seed["herb"].id)
        assert len(neighbors.edges) == 0, (
            "Tampered treats quote must be excluded from neighbors."
        )

        # get_validated_relations_for_entity must exclude
        validated = await svc.get_validated_relations_for_entity(
            "herb", seed["herb"].id
        )
        assert len(validated) == 0, (
            "Tampered treats quote must be excluded from validated relations."
        )
