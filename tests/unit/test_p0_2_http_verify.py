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

    doc = Document(title="晋书", content_text="皇甫谧，字士安。撰《针灸甲乙经》。")
    session.add(doc)
    await session.flush()

    chunk = DocumentChunk(
        id="chunk-verify",
        document_id=doc.id,
        content="皇甫谧撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        chunk_index=0,
    )
    session.add(chunk)
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
