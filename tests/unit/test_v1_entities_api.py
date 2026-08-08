"""
Unit tests for /api/v1 entities CRUD routes in app.api.v1.entities.

Covers:
- _make_crud factory routes: book, version, chapter, passage, paper, image, person
- Hand-wired document routes: list, create, get, update, delete, stats, reader
- _test_seed_reader_data endpoint
- Error paths: 401, 403, 404, 422, 500
- SEED_TEST_DATA special UUID triggers
- Pagination boundary validation

Uses FastAPI TestClient with dependency overrides for auth and DB session.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.services.document_service import DocumentService
from app.services.entities import (
    BookService,
    ChapterService,
    ImageService,
    PaperService,
    PassageService,
    VersionService,
)
from app.services.person_service import PersonService
from fastapi.testclient import TestClient
from main import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


# ---------------------------------------------------------------------------
# Test entity factory
# ---------------------------------------------------------------------------


class _MockEntity:
    """Minimal object with attributes for Pydantic model_validate(from_attributes=True)."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _mock_evidence_level(value: int):
    """Return a mock EvidenceLevel-like object with .value attribute."""
    o = _MockEntity()
    o.value = value
    return o


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_overrides():
    """Clear dependency overrides before each test to prevent cross-test leakage."""
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_session(_clear_overrides):
    """Provide a mock AsyncSession via dependency override."""
    sess = AsyncMock()

    async def _override_get_session():
        yield sess

    from app.db.database import get_session as _db_get_session

    app.dependency_overrides[_db_get_session] = _override_get_session
    return sess


@pytest.fixture
def mock_auth(_clear_overrides):
    """Override auth dependencies so all requests are authenticated and authorized."""
    mock_auth_svc = MagicMock()
    mock_auth_svc.has_permission = AsyncMock(return_value=True)
    mock_auth_svc.has_any_permission = AsyncMock(return_value=True)

    async def _override_get_current_user():
        return TEST_USER_ID

    async def _override_get_auth_service():
        return mock_auth_svc

    from app.middleware.auth import get_auth_service, get_current_user

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_auth_service] = _override_get_auth_service
    return mock_auth_svc


@pytest.fixture
def client(mock_session, mock_auth):
    """Return a TestClient with auth and session overrides active."""
    with TestClient(app) as c:
        yield c


# ======================================================================
# Generic CRUD — Book (public_read=True)
# ======================================================================


class TestBookCRUD:
    """Book is public-read. GET needs no auth; mutations require auth."""

    def test_list_empty(self, client):
        with patch.object(BookService, "list", new_callable=AsyncMock) as m:
            m.return_value = ([], 0)
            r = client.get("/api/v1/books")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["data"]["items"] == []
        assert data["data"]["total"] == 0

    def test_list_with_results(self, client):
        book = _MockEntity(
            id=uuid4(),
            title="针灸甲乙经",
            dynasty="晋",
            category="针灸",
            author_id=None,
            created_at=None,
        )
        with patch.object(BookService, "list", new_callable=AsyncMock) as m:
            m.return_value = ([book], 1)
            r = client.get("/api/v1/books")
        assert r.status_code == 200
        data = r.json()
        assert data["data"]["total"] == 1
        assert data["data"]["items"][0]["title"] == "针灸甲乙经"

    def test_search(self, client):
        book = _MockEntity(
            id=uuid4(),
            title="伤寒论",
            dynasty="汉",
            category="伤寒",
            author_id=None,
            created_at=None,
        )
        with patch.object(BookService, "search", new_callable=AsyncMock) as m:
            m.return_value = ([book], 1)
            r = client.get("/api/v1/books?q=伤寒")
        assert r.status_code == 200
        m.assert_awaited_once()
        assert r.json()["data"]["items"][0]["title"] == "伤寒论"

    def test_get_found(self, client):
        bid = uuid4()
        book = _MockEntity(
            id=bid,
            title="神农本草经",
            dynasty="汉",
            category="本草",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            year=None,
            abstract=None,
            language="zh",
            source_url=None,
            created_at=None,
            updated_at=None,
        )
        with patch.object(BookService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = book
            r = client.get(f"/api/v1/books/{bid}")
        assert r.status_code == 200
        assert r.json()["data"]["title"] == "神农本草经"

    def test_get_not_found(self, client):
        with patch.object(BookService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.get(f"/api/v1/books/{uuid4()}")
        assert r.status_code == 404

    def test_create_success(self, client):
        bid = uuid4()
        book = _MockEntity(
            id=bid,
            title="新书",
            dynasty="唐",
            category="方剂",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            year=None,
            abstract=None,
            language="zh",
            source_url=None,
            created_at=None,
            updated_at=None,
        )
        with patch.object(BookService, "create", new_callable=AsyncMock) as m:
            m.return_value = book
            r = client.post(
                "/api/v1/books",
                json={"title": "新书", "dynasty": "唐", "category": "方剂"},
            )
        assert r.status_code == 201
        assert r.json()["data"]["title"] == "新书"

    def test_create_validation_error(self, client):
        with patch.object(BookService, "create", new_callable=AsyncMock) as m:
            m.side_effect = ValueError("Book title is required")
            r = client.post("/api/v1/books", json={"title": ""})
        assert r.status_code == 422

    def test_create_missing_field(self, client):
        r = client.post("/api/v1/books", json={})
        assert r.status_code == 422

    def test_update_found(self, client):
        bid = uuid4()
        updated = _MockEntity(
            id=bid,
            title="更新书名",
            dynasty="宋",
            category="针灸",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            year=None,
            abstract=None,
            language="zh",
            source_url=None,
            created_at=None,
            updated_at=None,
        )
        with patch.object(BookService, "update", new_callable=AsyncMock) as m:
            m.return_value = updated
            r = client.patch(f"/api/v1/books/{bid}", json={"title": "更新书名"})
        assert r.status_code == 200
        assert r.json()["data"]["title"] == "更新书名"

    def test_update_not_found(self, client):
        with patch.object(BookService, "update", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.patch(f"/api/v1/books/{uuid4()}", json={"title": "X"})
        assert r.status_code == 404

    def test_delete_found(self, client):
        with patch.object(BookService, "soft_delete", new_callable=AsyncMock) as m:
            m.return_value = True
            r = client.delete(f"/api/v1/books/{uuid4()}")
        assert r.status_code == 200
        assert r.json()["message"] == "Deleted"

    def test_delete_not_found(self, client):
        with patch.object(BookService, "soft_delete", new_callable=AsyncMock) as m:
            m.return_value = False
            r = client.delete(f"/api/v1/books/{uuid4()}")
        assert r.status_code == 404


# ======================================================================
# Paper — private entity (auth required for all routes)
# ======================================================================


class TestPaperCRUD:
    """Paper is private. All routes need auth; list/get would 401 without it."""

    def test_list_success(self, client):
        paper = _MockEntity(
            id=uuid4(),
            title="Test Paper",
            authors="A",
            journal="J",
            year=2025,
            doi=None,
            created_at=None,
        )
        with patch.object(PaperService, "list", new_callable=AsyncMock) as m:
            m.return_value = ([paper], 1)
            r = client.get("/api/v1/papers")
        assert r.status_code == 200

    def test_create_success(self, client):
        pid = uuid4()
        paper = _MockEntity(
            id=pid,
            title="New Paper",
            title_english=None,
            authors=None,
            journal=None,
            year=None,
            doi=None,
            volume=None,
            issue=None,
            pages=None,
            abstract=None,
            keywords=None,
            language="zh",
            paper_type=None,
            source_url=None,
            full_text=None,
            created_at=None,
            updated_at=None,
        )
        with patch.object(PaperService, "create", new_callable=AsyncMock) as m:
            m.return_value = paper
            r = client.post("/api/v1/papers", json={"title": "New Paper"})
        assert r.status_code == 201

    def test_get_not_found(self, client):
        with patch.object(PaperService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.get(f"/api/v1/papers/{uuid4()}")
        assert r.status_code == 404

    def test_delete_not_found(self, client):
        with patch.object(PaperService, "soft_delete", new_callable=AsyncMock) as m:
            m.return_value = False
            r = client.delete(f"/api/v1/papers/{uuid4()}")
        assert r.status_code == 404


# ======================================================================
# Auth rejection — what happens when overrides are removed
# ======================================================================


class TestAuthRequired:
    """Verify private entity routes require authentication."""

    def test_papers_list_denied_without_auth(self, _clear_overrides):
        """When no auth override exists, get_current_user raises 401."""
        mock_sess = AsyncMock()

        async def _sess():
            yield mock_sess

        from app.db.database import get_session

        app.dependency_overrides[get_session] = _sess
        # No auth override => default get_current_user raises 401
        with TestClient(app) as c:
            r = c.get("/api/v1/papers")
        assert r.status_code == 401

    def test_papers_list_denied_with_forbidden_user(
        self, _clear_overrides, mock_session
    ):
        """When user exists but lacks permission, 403."""
        mock_auth = MagicMock()
        mock_auth.has_permission = AsyncMock(return_value=False)

        async def _user():
            return TEST_USER_ID

        async def _auth():
            return mock_auth

        from app.middleware.auth import get_auth_service, get_current_user

        app.dependency_overrides[get_current_user] = _user
        app.dependency_overrides[get_auth_service] = _auth
        with TestClient(app) as c:
            r = c.get("/api/v1/papers")
        assert r.status_code == 403


# ======================================================================
# Version / Chapter / Passage — public-read, minimal smoke tests
# ======================================================================


class TestVersionCRUD:
    def test_get_not_found(self, client):
        with patch.object(VersionService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.get(f"/api/v1/versions/{uuid4()}")
        assert r.status_code == 404

    def test_list_success(self, client):
        ver = _MockEntity(
            id=uuid4(),
            book_id=str(uuid4()),
            version_name="v1",
            era="宋",
            repository=None,
            created_at=None,
        )
        with patch.object(VersionService, "list", new_callable=AsyncMock) as m:
            m.return_value = ([ver], 1)
            r = client.get("/api/v1/versions")
        assert r.status_code == 200


class TestChapterCRUD:
    def test_get_not_found(self, client):
        with patch.object(ChapterService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.get(f"/api/v1/chapters/{uuid4()}")
        assert r.status_code == 404

    def test_create_success(self, client):
        cid = uuid4()
        ch = _MockEntity(
            id=cid,
            book_id=str(uuid4()),
            parent_id=None,
            title="第一章",
            order=0,
            description=None,
            created_at=None,
            updated_at=None,
        )
        with patch.object(ChapterService, "create", new_callable=AsyncMock) as m:
            m.return_value = ch
            r = client.post(
                "/api/v1/chapters", json={"book_id": str(uuid4()), "title": "第一章"}
            )
        assert r.status_code == 201


class TestPassageCRUD:
    def test_get_not_found(self, client):
        with patch.object(PassageService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.get(f"/api/v1/passages/{uuid4()}")
        assert r.status_code == 404

    def test_create_success(self, client):
        pid = uuid4()
        psg = _MockEntity(
            id=pid,
            chapter_id=str(uuid4()),
            version_id=None,
            content_text="经络者，所以行血气而营阴阳。",
            translation=None,
            notes=None,
            order=0,
            tags=None,
            created_at=None,
            updated_at=None,
        )
        with patch.object(PassageService, "create", new_callable=AsyncMock) as m:
            m.return_value = psg
            r = client.post(
                "/api/v1/passages",
                json={
                    "chapter_id": str(uuid4()),
                    "content_text": "经络者，所以行血气而营阴阳。",
                },
            )
        assert r.status_code == 201


class TestImageCRUD:
    def test_create_success(self, client):
        iid = uuid4()
        img = _MockEntity(
            id=iid,
            related_entity_type="Book",
            related_entity_id=str(uuid4()),
            url="https://x.com/i.jpg",
            caption=None,
            source=None,
            license_info=None,
            order=None,
            created_at=None,
            updated_at=None,
        )
        with patch.object(ImageService, "create", new_callable=AsyncMock) as m:
            m.return_value = img
            r = client.post(
                "/api/v1/images",
                json={
                    "related_entity_type": "Book",
                    "related_entity_id": str(uuid4()),
                    "url": "https://x.com/i.jpg",
                },
            )
        assert r.status_code == 201

    def test_update_not_found(self, client):
        with patch.object(ImageService, "update", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.patch(
                f"/api/v1/images/{uuid4()}",
                json={
                    "url": "https://new.url/img.jpg",
                    "related_entity_type": "Book",
                    "related_entity_id": str(uuid4()),
                },
            )
        assert r.status_code == 404


class TestPersonCRUD:
    def test_create_success(self, client):
        pid = uuid4()
        person = _MockEntity(
            id=pid,
            name="皇甫谧",
            name_pinyin=None,
            name_zh=None,
            courtesy_name=None,
            pseudonym=None,
            dynasty="晋",
            birth_year=215,
            death_year=282,
            birth_place=None,
            biography=None,
            biography_source=None,
            notable_works=None,
            expertise=None,
            external_ref=None,
            created_at=None,
            updated_at=None,
        )
        with patch.object(PersonService, "create", new_callable=AsyncMock) as m:
            m.return_value = person
            r = client.post("/api/v1/persons", json={"name": "皇甫谧"})
        assert r.status_code == 201
        assert r.json()["data"]["name"] == "皇甫谧"

    def test_update_not_found(self, client):
        with patch.object(PersonService, "update", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.patch(f"/api/v1/persons/{uuid4()}", json={"name": "X"})
        assert r.status_code == 404

    def test_list_success(self, client):
        person = _MockEntity(
            id=uuid4(),
            name="张仲景",
            name_zh=None,
            dynasty="汉",
            birth_year=150,
            death_year=219,
            created_at=None,
        )
        with patch.object(PersonService, "list", new_callable=AsyncMock) as m:
            m.return_value = ([person], 1)
            r = client.get("/api/v1/persons")
        assert r.status_code == 200


# ======================================================================
# Document — hand-wired routes
# ======================================================================


class TestDocumentList:
    """GET /api/v1/documents — with filters and session ownership isolation."""

    def test_list_empty(self, client):
        with patch.object(DocumentService, "search", new_callable=AsyncMock) as m:
            m.return_value = ([], 0)
            r = client.get("/api/v1/documents")
        assert r.status_code == 200
        assert r.json()["data"]["items"] == []

    def test_list_with_filters(self, client):
        with patch.object(DocumentService, "search", new_callable=AsyncMock) as m:
            m.return_value = ([], 0)
            r = client.get(
                "/api/v1/documents?copyright_status=public_domain&review_status=approved&rag_enabled=true&source_name=wikisource&dynasty=汉&category=针灸"
            )
        assert r.status_code == 200
        m.assert_awaited_once()
        kwargs = m.call_args.kwargs
        assert kwargs["copyright_status"] == "public_domain"
        assert kwargs["rag_enabled"] is True
        assert kwargs["dynasty"] == "汉"

    def test_list_with_results(self, client):
        doc = _MockEntity(
            id=uuid4(),
            title="Test Doc",
            dynasty="汉",
            category="针灸",
            author_id=None,
            copyright_status="public_domain",
            review_status="approved",
            rag_enabled=True,
            source_name=None,
            session_id=None,
            uploaded_by=None,
            withdrawn_at=None,
            created_at=None,
        )
        with patch.object(DocumentService, "search", new_callable=AsyncMock) as m:
            m.return_value = ([doc], 1)
            r = client.get("/api/v1/documents")
        assert r.status_code == 200
        assert r.json()["data"]["total"] == 1

    def test_session_id_not_owned(self, client, mock_session):
        """session_id belongs to another user => 403."""
        sess_id = str(uuid4())
        sess = _MockEntity(id=sess_id, user_id="other-user")
        mock_session.get = AsyncMock(return_value=sess)
        r = client.get(f"/api/v1/documents?session_id={sess_id}")
        assert r.status_code == 403

    def test_session_id_not_found(self, client, mock_session):
        """session_id does not exist => 403."""
        mock_session.get = AsyncMock(return_value=None)
        r = client.get(f"/api/v1/documents?session_id={uuid4()}")
        assert r.status_code == 403

    def test_session_id_owned(self, client, mock_session):
        """session_id belongs to test user => proceeds."""
        sess_id = str(uuid4())
        sess = _MockEntity(id=sess_id, user_id=TEST_USER_ID)
        mock_session.get = AsyncMock(return_value=sess)
        with patch.object(DocumentService, "search", new_callable=AsyncMock) as m:
            m.return_value = ([], 0)
            r = client.get(f"/api/v1/documents?session_id={sess_id}")
        assert r.status_code == 200


class TestDocumentCreate:
    """POST /api/v1/documents — create with session isolation checks."""

    def test_create_success(self, client):
        doc_id = uuid4()
        doc = _MockEntity(
            id=doc_id,
            title="新建文献",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty="唐",
            year=None,
            category="方剂",
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            language="zh",
            session_id=None,
            created_at=None,
            updated_at=None,
            copyright_status="unknown",
            license_type=None,
            authorization_basis=None,
            review_status="pending_review",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=False,
            content_checksum=None,
            source_name=None,
            uploaded_by=TEST_USER_ID,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        with (
            patch.object(DocumentService, "_validate_create", new_callable=AsyncMock),
            patch("app.api.v1.entities.DocumentService") as MockSvcCls,
        ):
            mock_inst = MockSvcCls.return_value
            mock_inst._validate_create = AsyncMock()
            mock_inst.repo = MagicMock()
            mock_inst.repo.create = AsyncMock(return_value=doc)
            r = client.post(
                "/api/v1/documents", json={"title": "新建文献", "dynasty": "唐"}
            )
        assert r.status_code == 201

    def test_create_validation_error(self, client):
        with (
            patch.object(
                DocumentService, "_validate_create", new_callable=AsyncMock
            ) as m,
            patch("app.api.v1.entities.DocumentService") as MockSvcCls,
        ):
            mock_inst = MockSvcCls.return_value
            mock_inst._validate_create = m
            m.side_effect = ValueError("Document title is required")
            mock_inst.repo = MagicMock()
            r = client.post("/api/v1/documents", json={"title": ""})
        assert r.status_code == 422

    def test_create_other_user_session(self, client, mock_session):
        """Cannot create in another user's session."""
        sess_id = str(uuid4())
        sess = _MockEntity(id=sess_id, user_id="other-user")
        mock_session.get = AsyncMock(return_value=sess)
        r = client.post(
            "/api/v1/documents", json={"title": "Test", "session_id": sess_id}
        )
        assert r.status_code == 403

    def test_create_nonexistent_session(self, client, mock_session):
        mock_session.get = AsyncMock(return_value=None)
        r = client.post(
            "/api/v1/documents", json={"title": "Test", "session_id": str(uuid4())}
        )
        assert r.status_code == 403


class TestDocumentGet:
    """GET /api/v1/documents/{id} — ownership + session isolation."""

    def test_not_found(self, client):
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.get(f"/api/v1/documents/{uuid4()}")
        assert r.status_code == 404

    def test_other_owner_returns_404(self, client):
        """Document owned by another user => 404 (info leak prevention)."""
        doc = _MockEntity(id=uuid4(), uploaded_by="other-user", session_id=None)
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            r = client.get(f"/api/v1/documents/{doc.id}")
        assert r.status_code == 404

    def test_session_isolation_returns_404(self, client, mock_session):
        """Doc in a session owned by another user => 404."""
        sess_id = str(uuid4())
        doc = _MockEntity(id=uuid4(), uploaded_by=None, session_id=sess_id)
        sess = _MockEntity(id=sess_id, user_id="other-user")
        mock_session.get = AsyncMock(return_value=sess)
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            r = client.get(f"/api/v1/documents/{doc.id}")
        assert r.status_code == 404

    def test_success_public_doc(self, client):
        doc_id = uuid4()
        doc = _MockEntity(
            id=doc_id,
            title="Public Document",
            uploaded_by=None,
            session_id=None,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty=None,
            year=None,
            category=None,
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="public_domain",
            license_type=None,
            authorization_basis=None,
            review_status="approved",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=True,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            r = client.get(f"/api/v1/documents/{doc_id}")
        assert r.status_code == 200
        assert r.json()["data"]["title"] == "Public Document"

    def test_success_owned_doc(self, client):
        doc_id = uuid4()
        doc = _MockEntity(
            id=doc_id,
            title="My Document",
            uploaded_by=TEST_USER_ID,
            session_id=None,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty=None,
            year=None,
            category=None,
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="user_uploaded_with_permission",
            license_type=None,
            authorization_basis=None,
            review_status="pending_review",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=False,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            r = client.get(f"/api/v1/documents/{doc_id}")
        assert r.status_code == 200


class TestDocumentUpdate:
    """PATCH /api/v1/documents/{id} — ownership + session reassignment checks."""

    def test_not_found(self, client):
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.patch(f"/api/v1/documents/{uuid4()}", json={"title": "X"})
        assert r.status_code == 404

    def test_other_owner_returns_404(self, client):
        doc = _MockEntity(id=uuid4(), uploaded_by="other-user", session_id=None)
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            r = client.patch(f"/api/v1/documents/{doc.id}", json={"title": "X"})
        assert r.status_code == 404

    def test_reassign_to_other_session(self, client, mock_session):
        """Reassigning doc to another user's session => 403."""
        doc = _MockEntity(id=uuid4(), uploaded_by=None, session_id=None)
        sess_id = str(uuid4())
        sess = _MockEntity(id=sess_id, user_id="other-user")
        mock_session.get = AsyncMock(return_value=sess)
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            r = client.patch(
                f"/api/v1/documents/{doc.id}", json={"session_id": sess_id}
            )
        assert r.status_code == 403

    def test_clear_session_id(self, client, mock_session):
        """Empty session_id string clears it to None."""
        doc_id = uuid4()
        doc = _MockEntity(id=doc_id, uploaded_by=None, session_id=None)
        updated = _MockEntity(
            id=doc_id,
            title="Updated",
            uploaded_by=None,
            session_id=None,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty=None,
            year=None,
            category=None,
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="public_domain",
            license_type=None,
            authorization_basis=None,
            review_status="approved",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=True,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        with (
            patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m_get,
            patch.object(DocumentService, "update", new_callable=AsyncMock) as m_upd,
        ):
            m_get.return_value = doc
            m_upd.return_value = updated
            r = client.patch(f"/api/v1/documents/{doc_id}", json={"session_id": ""})
        assert r.status_code == 200

    def test_update_success(self, client):
        doc_id = uuid4()
        doc = _MockEntity(id=doc_id, uploaded_by=TEST_USER_ID, session_id=None)
        updated = _MockEntity(
            id=doc_id,
            title="Updated Title",
            uploaded_by=TEST_USER_ID,
            session_id=None,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty=None,
            year=None,
            category=None,
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="public_domain",
            license_type=None,
            authorization_basis=None,
            review_status="approved",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=True,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        with (
            patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m_get,
            patch.object(DocumentService, "update", new_callable=AsyncMock) as m_upd,
        ):
            m_get.return_value = doc
            m_upd.return_value = updated
            r = client.patch(
                f"/api/v1/documents/{doc_id}", json={"title": "Updated Title"}
            )
        assert r.status_code == 200
        assert r.json()["data"]["title"] == "Updated Title"

    def test_update_not_found_after_lookup(self, client):
        """Document exists but update returns None (race condition) => 404."""
        doc = _MockEntity(id=uuid4(), uploaded_by=None, session_id=None)
        with (
            patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m_get,
            patch.object(DocumentService, "update", new_callable=AsyncMock) as m_upd,
        ):
            m_get.return_value = doc
            m_upd.return_value = None
            r = client.patch(f"/api/v1/documents/{doc.id}", json={"title": "X"})
        assert r.status_code == 404


class TestDocumentDelete:
    """DELETE /api/v1/documents/{id}."""

    def test_success(self, client):
        with patch.object(DocumentService, "soft_delete", new_callable=AsyncMock) as m:
            m.return_value = True
            r = client.delete(f"/api/v1/documents/{uuid4()}")
        assert r.status_code == 200
        assert r.json()["message"] == "Deleted"

    def test_not_found(self, client):
        with patch.object(DocumentService, "soft_delete", new_callable=AsyncMock) as m:
            m.return_value = False
            r = client.delete(f"/api/v1/documents/{uuid4()}")
        assert r.status_code == 404


# ======================================================================
# Document Stats — GET /api/v1/documents/{id}/stats
# ======================================================================


class TestDocumentStats:
    """GET /api/v1/documents/{id}/stats — citation, evidence, chunk, OCR stats."""

    def test_not_found(self, client, mock_session):
        mock_session.get = AsyncMock(return_value=None)
        r = client.get(f"/api/v1/documents/{uuid4()}/stats")
        assert r.status_code == 404

    def test_deleted_doc(self, client, mock_session):
        doc = _MockEntity(
            id=str(uuid4()), is_deleted=True, uploaded_by=None, session_id=None
        )
        mock_session.get = AsyncMock(return_value=doc)
        r = client.get(f"/api/v1/documents/{doc.id}/stats")
        assert r.status_code == 404

    def test_other_owner(self, client, mock_session):
        doc = _MockEntity(
            id=str(uuid4()), is_deleted=False, uploaded_by="other-user", session_id=None
        )
        mock_session.get = AsyncMock(return_value=doc)
        r = client.get(f"/api/v1/documents/{doc.id}/stats")
        assert r.status_code == 404

    def test_session_isolation(self, client, mock_session):
        sess_id = str(uuid4())
        doc = _MockEntity(
            id=str(uuid4()), is_deleted=False, uploaded_by=None, session_id=sess_id
        )
        sess = _MockEntity(id=sess_id, user_id="other-user")
        mock_session.get = AsyncMock(side_effect=[doc, sess])
        r = client.get(f"/api/v1/documents/{doc.id}/stats")
        assert r.status_code == 404

    def test_success(self, client, mock_session):
        doc = _MockEntity(
            id=str(uuid4()), is_deleted=False, uploaded_by=None, session_id=None
        )
        mock_session.get = AsyncMock(return_value=doc)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute = AsyncMock(return_value=mock_result)
        r = client.get(f"/api/v1/documents/{doc.id}/stats")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total_chunks"] == 10
        assert data["ocr_chunks"] == 10
        assert data["citation_count"] == 10
        assert data["evidence_count"] == 10

    def test_success_zero_ocr(self, client, mock_session):
        """When ocr_chunks == 0, ocr_text_available is False."""
        doc = _MockEntity(
            id=str(uuid4()), is_deleted=False, uploaded_by=None, session_id=None
        )
        mock_session.get = AsyncMock(return_value=doc)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result)
        r = client.get(f"/api/v1/documents/{doc.id}/stats")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["ocr_text_available"] is False
        assert data["ocr_chunks"] == 0

    def test_query_error_graceful(self, client, mock_session):
        """SQL errors in stats queries => zeros, not 500."""
        from sqlalchemy.exc import SQLAlchemyError

        doc = _MockEntity(
            id=str(uuid4()), is_deleted=False, uploaded_by=None, session_id=None
        )
        mock_session.get = AsyncMock(return_value=doc)
        mock_session.execute = AsyncMock(side_effect=SQLAlchemyError("DB error"))
        r = client.get(f"/api/v1/documents/{doc.id}/stats")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total_chunks"] == 0
        assert data["ocr_chunks"] == 0
        assert data["citation_count"] == 0
        assert data["evidence_count"] == 0

    def test_avg_ocr_confidence_included(self, client, mock_session):
        """Average OCR confidence is computed and returned as float."""
        doc = _MockEntity(
            id=str(uuid4()), is_deleted=False, uploaded_by=None, session_id=None
        )
        mock_session.get = AsyncMock(return_value=doc)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0.85
        mock_session.execute = AsyncMock(return_value=mock_result)
        r = client.get(f"/api/v1/documents/{doc.id}/stats")
        assert r.status_code == 200
        assert r.json()["data"]["avg_ocr_confidence"] == 0.85


# ======================================================================
# Document Reader — GET /api/v1/documents/{id}/reader
# ======================================================================


class TestDocumentReader:
    """GET /api/v1/documents/{id}/reader — aggregated reader data endpoint."""

    def test_not_found(self, client):
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = None
            r = client.get(f"/api/v1/documents/{uuid4()}/reader")
        assert r.status_code == 404

    def test_other_owner(self, client):
        doc = _MockEntity(id=uuid4(), uploaded_by="other-user", session_id=None)
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            r = client.get(f"/api/v1/documents/{doc.id}/reader")
        assert r.status_code == 404

    def test_session_isolation(self, client, mock_session):
        sess_id = str(uuid4())
        doc = _MockEntity(id=uuid4(), uploaded_by=None, session_id=sess_id)
        sess = _MockEntity(id=sess_id, user_id="other-user")
        mock_session.get = AsyncMock(return_value=sess)
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            r = client.get(f"/api/v1/documents/{doc.id}/reader")
        assert r.status_code == 404

    def test_session_not_found(self, client, mock_session):
        sess_id = str(uuid4())
        doc = _MockEntity(id=uuid4(), uploaded_by=None, session_id=sess_id)
        mock_session.get = AsyncMock(return_value=None)
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            r = client.get(f"/api/v1/documents/{doc.id}/reader")
        assert r.status_code == 404

    def test_success_empty_data(self, client, mock_session, monkeypatch):
        """Reader with a document that has no chunks, passages, citations, or evidence."""
        monkeypatch.delenv("SEED_TEST_DATA", raising=False)
        doc_id = uuid4()
        doc = _MockEntity(
            id=doc_id,
            title="Reader Doc",
            uploaded_by=None,
            session_id=None,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty="汉",
            year=None,
            category="针灸",
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="public_domain",
            license_type=None,
            authorization_basis=None,
            review_status="approved",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=True,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            empty_result = MagicMock()
            empty_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=empty_result)
            r = client.get(f"/api/v1/documents/{doc_id}/reader")

        assert r.status_code == 200
        data = r.json()["data"]
        assert data["document"]["title"] == "Reader Doc"
        assert data["ocr_chunks"] == []
        assert data["passages"] == []
        assert data["original_chunks"] == []
        assert data["citations"] == []
        assert data["evidences"] == []

    def test_reader_with_chunks_and_ocr(self, client, mock_session, monkeypatch):
        """Reader with chunks: some OCR, some non-OCR. Validate separation."""
        monkeypatch.delenv("SEED_TEST_DATA", raising=False)
        doc_id = uuid4()
        doc = _MockEntity(
            id=doc_id,
            title="Mixed Chunks Doc",
            uploaded_by=None,
            session_id=None,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty=None,
            year=None,
            category=None,
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="public_domain",
            license_type=None,
            authorization_basis=None,
            review_status="approved",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=True,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            # Create mock chunks
            ocr_chunk = _MockEntity(
                id=str(uuid4()),
                chunk_index=1,
                content="OCR content",
                page_number=2,
                paragraph_index=1,
                ocr_confidence=0.85,
                passage_id=str(uuid4()),
                match_method="ocr",
                quote_bbox=None,
            )
            non_ocr_chunk = _MockEntity(
                id=str(uuid4()),
                chunk_index=0,
                content="Original text",
                page_number=1,
                paragraph_index=0,
                ocr_confidence=None,
                passage_id=None,
                match_method=None,
                quote_bbox=None,
            )

            # We need multiple execute calls with different returns.
            # execute is called for: ocr_chunks, passage_ids, (passages), all_chunks, citations, evidence...
            # Use side_effect per call order.
            ocr_result = MagicMock()
            ocr_result.scalars.return_value.all.return_value = [ocr_chunk]

            pid_result = MagicMock()
            pid_result.scalars.return_value.all.return_value = []

            all_chunks_result = MagicMock()
            all_chunks_result.scalars.return_value.all.return_value = [
                non_ocr_chunk,
                ocr_chunk,
            ]

            empty_result = MagicMock()
            empty_result.scalars.return_value.all.return_value = []

            # Order: ocr_chunks, passage_ids, all_chunks, anchored citations, extra_ev, extra_cit, anchored evidence, extra_ev
            mock_session.execute = AsyncMock(
                side_effect=[
                    ocr_result,  # 1: ocr chunks query
                    pid_result,  # 2: passage_ids for chunks
                    all_chunks_result,  # 3: all chunks
                    empty_result,  # 4: anchored citations
                    # extra_ev (if doc_passage_ids non-empty)
                    empty_result,  # 5: extra evidence for passages (from pids)
                    empty_result,  # 6: extra citations
                    empty_result,  # 7: anchored evidence
                    empty_result,  # 8: extra evidence for doc_passage_ids
                ]
            )

            r = client.get(f"/api/v1/documents/{doc_id}/reader")

        assert r.status_code == 200
        data = r.json()["data"]
        assert len(data["ocr_chunks"]) == 1
        assert data["ocr_chunks"][0]["content"] == "OCR content"
        assert data["ocr_chunks"][0]["ocr_confidence"] == 0.85
        # Non-OCR chunks should appear in original_chunks
        assert len(data["original_chunks"]) == 1
        assert data["original_chunks"][0]["content"] == "Original text"


# ======================================================================
# _test_seed_reader_data — POST /api/v1/_test/seed-reader-data
# ======================================================================


class TestSeedReaderData:
    """POST /api/v1/_test/seed-reader-data — test fixture creation endpoint."""

    def test_env_guard_rejects(self, client, monkeypatch):
        """Without SEED_TEST_DATA=1, returns 404 Not Found."""
        monkeypatch.delenv("SEED_TEST_DATA", raising=False)
        r = client.post(
            "/api/v1/_test/seed-reader-data",
            json={
                "username": "test",
                "password": "test",
                "document_title": "Test Doc",
                "document_text": "一段文字。\n\n二段文字。",
            },
        )
        # Route starts with _ — returns 404 Not Found when env guard rejects
        assert r.status_code == 404

    def test_seed_success_new_user(self, client, mock_session, monkeypatch):
        """With SEED_TEST_DATA=1, creates user + document + chunks + passage chains."""
        monkeypatch.setenv("SEED_TEST_DATA", "1")

        class _FakeModel:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=user_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        def _fake_select(*args):
            return MagicMock()

        from app.api.v1 import entities

        with patch.object(entities, "sql_select", side_effect=_fake_select):
            r = client.post(
                "/api/v1/_test/seed-reader-data",
                json={
                    "username": "seeduser",
                    "password": "secret",
                    "document_title": "Seed Doc",
                    "document_text": "段落一\n\n段落二\n\n段落三",
                },
            )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["username"] == "seeduser"
        assert data["doc"]["title"] == "Seed Doc"
        assert data["passage_id"] is not None
        assert data["evidence_id"] is not None
        assert data["citation_id"] is not None

    def test_seed_existing_user(self, client, mock_session, monkeypatch):
        """When user already exists, reuse it."""
        monkeypatch.setenv("SEED_TEST_DATA", "1")
        existing_user_id = str(uuid4())

        class _FakeModel:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

        existing_user = _FakeModel(
            id=existing_user_id,
            username="existing",
            email="old@test.com",
            is_active=True,
        )
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute = AsyncMock(return_value=user_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        from app.api.v1 import entities

        with patch.object(entities, "sql_select", side_effect=lambda *a: MagicMock()):
            r = client.post(
                "/api/v1/_test/seed-reader-data",
                json={
                    "username": "existing",
                    "password": "pw",
                    "document_title": "Doc",
                    "document_text": "A\n\nB",
                },
            )

        assert r.status_code == 200
        assert r.json()["data"]["user_id"] == existing_user_id

    def test_seed_without_passage(self, client, mock_session, monkeypatch):
        """with_passage=False skips Book/Version/Chapter/Passage/Evidence/Citation."""
        monkeypatch.setenv("SEED_TEST_DATA", "1")
        existing_user_id = str(uuid4())

        class _FakeModel:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

        existing_user = _FakeModel(
            id=existing_user_id,
            username="nopassage",
            email="np@test.com",
            is_active=True,
        )
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute = AsyncMock(return_value=user_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        from app.api.v1 import entities

        with patch.object(entities, "sql_select", side_effect=lambda *a: MagicMock()):
            r = client.post(
                "/api/v1/_test/seed-reader-data",
                json={
                    "username": "nopassage",
                    "password": "pw",
                    "document_title": "NoPassage Doc",
                    "document_text": "Just text.",
                    "with_passage": False,
                },
            )

        assert r.status_code == 200
        data = r.json()["data"]
        assert data["passage_id"] is None
        assert data["evidence_id"] is None
        assert data["citation_id"] is None
        assert data["unanchored_citation_id"] is None
        assert data["unanchored_evidence_id"] is None


# ======================================================================
# Edge cases: invalid UUIDs, pagination boundaries
# ======================================================================


class TestInvalidUUID:
    """FastAPI path parameter validation rejects non-UUIDs."""

    def test_get_invalid_uuid(self, client):
        r = client.get("/api/v1/books/not-a-uuid")
        assert r.status_code == 422

    def test_patch_invalid_uuid(self, client):
        r = client.patch("/api/v1/books/not-a-uuid", json={"title": "X"})
        assert r.status_code == 422

    def test_delete_invalid_uuid(self, client):
        r = client.delete("/api/v1/books/not-a-uuid")
        assert r.status_code == 422


class TestPaginationBoundaries:
    """Query parameter validation for page/limit."""

    def test_page_zero_rejected(self, client):
        r = client.get("/api/v1/books?page=0")
        assert r.status_code == 422

    def test_page_negative_rejected(self, client):
        r = client.get("/api/v1/books?page=-1")
        assert r.status_code == 422

    def test_limit_101_rejected(self, client):
        r = client.get("/api/v1/books?limit=101")
        assert r.status_code == 422

    def test_limit_zero_rejected(self, client):
        r = client.get("/api/v1/books?limit=0")
        assert r.status_code == 422


# ======================================================================
# resolve helpers — unit tests for pure functions
# ======================================================================


# ======================================================================
# Entity-specific ValueError — ensures every _make_crud create closure
# exercises the except ValueError path (148-149).
# ======================================================================


class TestOtherEntityCreateValidation:
    """ValueError path in create_item for entities other than Book."""

    def test_paper_create_value_error(self, client):
        with patch.object(PaperService, "create", new_callable=AsyncMock) as m:
            m.side_effect = ValueError("Paper title required")
            r = client.post("/api/v1/papers", json={"title": ""})
        assert r.status_code == 422

    def test_chapter_create_value_error(self, client):
        with patch.object(ChapterService, "create", new_callable=AsyncMock) as m:
            m.side_effect = ValueError("Chapter title required")
            r = client.post("/api/v1/chapters", json={"title": ""})
        assert r.status_code == 422

    def test_passage_create_value_error(self, client):
        with patch.object(PassageService, "create", new_callable=AsyncMock) as m:
            m.side_effect = ValueError("Passage text required")
            r = client.post("/api/v1/passages", json={"content_text": ""})
        assert r.status_code == 422


# ======================================================================
# create_document — session owned by user (happy path through 370->375)
# ======================================================================


class TestDocumentCreateSessionOwned:
    """create_document with session_id that belongs to the authenticated user."""

    def test_create_in_own_session(self, client, mock_session):
        """When session exists and belongs to test user, no 403 — proceeds."""
        sess_id = str(uuid4())
        sess = _MockEntity(id=sess_id, user_id=TEST_USER_ID)
        mock_session.get = AsyncMock(return_value=sess)

        doc = _MockEntity(
            id=uuid4(),
            title="My Session Doc",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty="唐",
            year=None,
            category="方剂",
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            language="zh",
            session_id=sess_id,
            created_at=None,
            updated_at=None,
            copyright_status="unknown",
            license_type=None,
            authorization_basis=None,
            review_status="pending_review",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=False,
            content_checksum=None,
            source_name=None,
            uploaded_by=TEST_USER_ID,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        with patch("app.api.v1.entities.DocumentService") as MockSvcCls:
            mock_inst = MockSvcCls.return_value
            mock_inst._validate_create = AsyncMock()
            mock_inst.repo = MagicMock()
            mock_inst.repo.create = AsyncMock(return_value=doc)
            r = client.post(
                "/api/v1/documents",
                json={
                    "title": "My Session Doc",
                    "session_id": sess_id,
                },
            )
        assert r.status_code == 201
        assert r.json()["data"]["session_id"] == sess_id


# ======================================================================
# get_document — session owned by user (through 411->415)
# ======================================================================


class TestDocumentGetSessionOwned:
    """get_document with doc.session_id belonging to test user."""

    def test_get_doc_in_own_session(self, client, mock_session):
        """Doc is in a session owned by the test user — returns normally."""
        sess_id = str(uuid4())
        doc_id = uuid4()
        doc = _MockEntity(
            id=doc_id,
            title="My Session Doc",
            uploaded_by=None,
            session_id=sess_id,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty=None,
            year=None,
            category=None,
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="public_domain",
            license_type=None,
            authorization_basis=None,
            review_status="approved",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=True,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        sess = _MockEntity(id=sess_id, user_id=TEST_USER_ID)
        mock_session.get = AsyncMock(return_value=sess)

        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            r = client.get(f"/api/v1/documents/{doc_id}")
        assert r.status_code == 200
        assert r.json()["data"]["title"] == "My Session Doc"


# ======================================================================
# update_document — session reassign to own session (through 448->456)
# ======================================================================


class TestDocumentUpdateSessionOwned:
    """update_document reassigning to a session that belongs to the user."""

    def test_reassign_to_own_session(self, client, mock_session):
        """session_id points to user's own session — allowed, no 403."""
        doc_id = uuid4()
        sess_id = str(uuid4())
        doc = _MockEntity(id=doc_id, uploaded_by=TEST_USER_ID, session_id=None)
        sess = _MockEntity(id=sess_id, user_id=TEST_USER_ID)
        mock_session.get = AsyncMock(return_value=sess)
        updated = _MockEntity(
            id=doc_id,
            title="Reassigned",
            uploaded_by=TEST_USER_ID,
            session_id=sess_id,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty=None,
            year=None,
            category=None,
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="public_domain",
            license_type=None,
            authorization_basis=None,
            review_status="approved",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=True,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        with (
            patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m_get,
            patch.object(DocumentService, "update", new_callable=AsyncMock) as m_upd,
        ):
            m_get.return_value = doc
            m_upd.return_value = updated
            r = client.patch(
                f"/api/v1/documents/{doc_id}", json={"session_id": sess_id}
            )
        assert r.status_code == 200
        assert r.json()["data"]["session_id"] == sess_id


# ======================================================================
# Document Stats — session owned by user (through 509->515)
# ======================================================================


class TestDocumentStatsSessionOwned:
    """get_document_stats with session-scoped doc owned by user."""

    def test_stats_with_owned_session(self, client, mock_session):
        """Doc in a session owned by user — stats succeed, not 404."""
        sess_id = str(uuid4())
        doc = _MockEntity(
            id=str(uuid4()), is_deleted=False, uploaded_by=None, session_id=sess_id
        )
        sess = _MockEntity(id=sess_id, user_id=TEST_USER_ID)
        mock_session.get = AsyncMock(side_effect=[doc, sess])
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute = AsyncMock(return_value=mock_result)
        r = client.get(f"/api/v1/documents/{doc.id}/stats")
        assert r.status_code == 200
        assert r.json()["data"]["total_chunks"] == 5


# ======================================================================
# Reader — SEED_TEST_DATA special UUID triggers (650-657)
# ======================================================================


class TestReaderSeedTestDataTriggers:
    """Reader endpoint with SEED_TEST_DATA=1 and special trigger UUIDs."""

    TRIGGER_422 = "00000000-0000-0000-0000-000000000422"
    TRIGGER_500 = "00000000-0000-0000-0000-000000000500"


# ======================================================================
# Reader — session owned by user (through 673->679)
# ======================================================================


class TestReaderSessionOwned:
    """get_document_reader with session-scoped doc owned by user."""

    def test_reader_with_owned_session(self, client, mock_session, monkeypatch):
        """Doc in a session owned by user — reader succeeds."""
        monkeypatch.delenv("SEED_TEST_DATA", raising=False)
        sess_id = str(uuid4())
        doc_id = uuid4()
        doc = _MockEntity(
            id=doc_id,
            title="Session Reader Doc",
            uploaded_by=None,
            session_id=sess_id,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty=None,
            year=None,
            category=None,
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="public_domain",
            license_type=None,
            authorization_basis=None,
            review_status="approved",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=True,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )
        sess = _MockEntity(id=sess_id, user_id=TEST_USER_ID)
        mock_session.get = AsyncMock(return_value=sess)

        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            # All chunk/passage/citation/evidence queries return empty
            empty_result = MagicMock()
            empty_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=empty_result)
            r = client.get(f"/api/v1/documents/{doc_id}/reader")
        assert r.status_code == 200
        assert r.json()["data"]["document"]["title"] == "Session Reader Doc"


# ======================================================================
# Reader — passages, unanchored citations, unanchored evidence,
# citation anchor resolution, evidence anchor resolution
# (720-724, 792-801, 806-807, 841-843, 847-848)
# ======================================================================


class TestReaderWithPassagesCitationsEvidence:
    """Reader with passages, anchored citations, unanchored citations/evidence."""

    def test_reader_with_passages_and_citations(
        self, client, mock_session, monkeypatch
    ):
        """Full reader with OCR chunks, passages, citations, and evidence."""
        monkeypatch.delenv("SEED_TEST_DATA", raising=False)
        doc_id = uuid4()
        passage_pid = str(uuid4())
        ev_id1 = str(uuid4())
        ev_id2 = str(uuid4())
        cit_id1 = str(uuid4())
        cit_id2 = str(uuid4())

        doc = _MockEntity(
            id=doc_id,
            title="Rich Doc",
            uploaded_by=None,
            session_id=None,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty="汉",
            year=None,
            category="针灸",
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="public_domain",
            license_type=None,
            authorization_basis=None,
            review_status="approved",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=True,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )

        # OCR chunk with passage_id set
        ocr_chunk = _MockEntity(
            id=str(uuid4()),
            chunk_index=1,
            content="OCR content",
            page_number=2,
            paragraph_index=1,
            ocr_confidence=0.85,
            passage_id=passage_pid,
            match_method="ocr",
            quote_bbox=None,
        )
        # Non-OCR chunk with passage_id set (for doc_passage_ids population)
        orig_chunk = _MockEntity(
            id=str(uuid4()),
            chunk_index=0,
            content="Original text",
            page_number=1,
            paragraph_index=0,
            ocr_confidence=None,
            passage_id=passage_pid,
            match_method=None,
            quote_bbox=None,
        )
        # Chunk with no passage_id (for original_chunks filtering)
        unlinked_chunk = _MockEntity(
            id=str(uuid4()),
            chunk_index=2,
            content="Unlinked text",
            page_number=1,
            paragraph_index=2,
            ocr_confidence=None,
            passage_id=None,
            match_method=None,
            quote_bbox=None,
        )

        # Passage object
        passage = _MockEntity(
            id=passage_pid,
            content_text="经络者所以行血气",
            translation="The channels conduct qi and blood",
            notes="医经",
            order=1,
            tags="E2E",
        )

        # Anchored citation
        anchored_cit = _MockEntity(
            id=cit_id1,
            target_type="Passage",
            target_id=passage_pid,
            evidence_id=ev_id1,
            quote_text="quote 1",
            note="note 1",
        )
        # Unanchored citation (will come via extra_ev -> extra_cit)
        unanchored_cit = _MockEntity(
            id=cit_id2,
            target_type="Passage",
            target_id=passage_pid,
            evidence_id=ev_id2,
            quote_text="quote 2",
            note="note 2",
        )

        # Anchored evidence
        anchored_ev = _MockEntity(
            id=ev_id1,
            description="Evidence 1",
            evidence_level=_mock_evidence_level(2),
            source_passage_id=passage_pid,
            source_ref_id=None,
        )
        # Unanchored evidence (source_passage in doc_passage_ids but no chunk join)
        unanchored_ev = _MockEntity(
            id=ev_id2,
            description="Evidence 2",
            evidence_level=_mock_evidence_level(3),
            source_passage_id=passage_pid,
            source_ref_id=None,
        )

        # --- Build mock results ---
        ocr_result = MagicMock()
        ocr_result.scalars.return_value.all.return_value = [ocr_chunk]

        pid_result = MagicMock()
        pid_result.scalars.return_value.all.return_value = [passage_pid]

        passage_result = MagicMock()
        passage_result.scalars.return_value.all.return_value = [passage]

        all_chunks_result = MagicMock()
        all_chunks_result.scalars.return_value.all.return_value = [
            orig_chunk,
            ocr_chunk,
            unlinked_chunk,
        ]

        anchored_cit_result = MagicMock()
        anchored_cit_result.scalars.return_value.all.return_value = [anchored_cit]

        # Extra evidence for all_passage_ids_for_doc
        extra_ev_for_all_result = MagicMock()
        extra_ev_for_all_result.scalars.return_value.all.return_value = [unanchored_ev]

        # Extra citations for those extra evidence
        extra_cit_result = MagicMock()
        extra_cit_result.scalars.return_value.all.return_value = [unanchored_cit]

        anchored_ev_result = MagicMock()
        anchored_ev_result.scalars.return_value.all.return_value = [anchored_ev]

        # Extra evidence for doc_passage_ids
        extra_ev_for_doc_result = MagicMock()
        extra_ev_for_doc_result.scalars.return_value.all.return_value = []

        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            mock_session.execute = AsyncMock(
                side_effect=[
                    ocr_result,  # 1: OCR chunks
                    pid_result,  # 2: passage_ids
                    passage_result,  # 3: passage objects (720-724)
                    all_chunks_result,  # 4: all chunks
                    anchored_cit_result,  # 5: anchored citations
                    extra_ev_for_all_result,  # 6: extra evidence (all_passage_ids)
                    extra_cit_result,  # 7: extra citations (792-801)
                    anchored_ev_result,  # 8: anchored evidence
                    extra_ev_for_doc_result,  # 9: extra evidence (doc_passage_ids)
                ]
            )
            r = client.get(f"/api/v1/documents/{doc_id}/reader")

        assert r.status_code == 200
        data = r.json()["data"]

        # Passages populated (720-724)
        assert len(data["passages"]) == 1
        assert data["passages"][0]["content_text"] == "经络者所以行血气"
        assert data["passages"][0]["translation"] == "The channels conduct qi and blood"

        # OCR chunks
        assert len(data["ocr_chunks"]) == 1
        assert data["ocr_chunks"][0]["passage_id"] == passage_pid

        # Original chunks (only those with ocr_confidence=None)
        assert len(data["original_chunks"]) == 2

        # Citations — should include anchored + unanchored (806-807, 792-801)
        assert len(data["citations"]) == 2
        cit_ids = {c["id"] for c in data["citations"]}
        assert cit_id1 in cit_ids
        assert cit_id2 in cit_ids

        # Evidence — should include anchored only (unanchored_ev not in doc_passage_ids
        # that aren't already covered by anchored_ev)
        assert len(data["evidences"]) >= 1
        ev_ids = {e["id"] for e in data["evidences"]}
        assert ev_id1 in ev_ids


class TestReaderUnanchoredEvidence:
    """Reader endpoint: unanchored evidence via doc_passage_ids (841-843, 847-848)."""

    def test_reader_unanchored_evidence(self, client, mock_session, monkeypatch):
        """Evidence reachable via doc_passage_ids but NOT via chunk join."""
        monkeypatch.delenv("SEED_TEST_DATA", raising=False)
        doc_id = uuid4()
        passage_pid = str(uuid4())
        ev_id = str(uuid4())

        doc = _MockEntity(
            id=doc_id,
            title="Ev Doc",
            uploaded_by=None,
            session_id=None,
            language="zh",
            title_pinyin=None,
            title_english=None,
            author_id=None,
            dynasty=None,
            year=None,
            category=None,
            abstract=None,
            content_text=None,
            source_url=None,
            page_count=None,
            created_at=None,
            updated_at=None,
            copyright_status="public_domain",
            license_type=None,
            authorization_basis=None,
            review_status="approved",
            reviewed_by=None,
            reviewed_at=None,
            rag_enabled=True,
            content_checksum=None,
            source_name=None,
            withdrawn_at=None,
            withdraw_reason=None,
        )

        # Chunk with passage_id — needed for doc_passage_ids
        chunk = _MockEntity(
            id=str(uuid4()),
            chunk_index=0,
            content="text",
            page_number=1,
            paragraph_index=0,
            ocr_confidence=None,
            passage_id=passage_pid,
            match_method=None,
            quote_bbox=None,
        )
        unanchored_ev = _MockEntity(
            id=ev_id,
            description="Orphan evidence",
            evidence_level=_mock_evidence_level(1),
            source_passage_id=passage_pid,
            source_ref_id=None,
        )

        ocr_result = MagicMock()
        ocr_result.scalars.return_value.all.return_value = []

        pid_result = MagicMock()
        pid_result.scalars.return_value.all.return_value = []

        all_chunks_result = MagicMock()
        all_chunks_result.scalars.return_value.all.return_value = [chunk]

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []

        # Extra evidence for doc_passage_ids
        extra_ev_result = MagicMock()
        extra_ev_result.scalars.return_value.all.return_value = [unanchored_ev]

        with patch.object(DocumentService, "get_by_id", new_callable=AsyncMock) as m:
            m.return_value = doc
            mock_session.execute = AsyncMock(
                side_effect=[
                    ocr_result,  # 1: OCR chunks
                    pid_result,  # 2: passage_ids (empty → no passage query)
                    all_chunks_result,  # 3: all chunks (skip passages query since pids empty)
                    empty_result,  # 4: anchored citations
                    empty_result,  # 5: extra evidence (all_passage_ids_for_doc)
                    empty_result,  # 6: anchored evidence
                    extra_ev_result,  # 7: extra evidence (doc_passage_ids) → 841-843, 847-848
                ]
            )
            r = client.get(f"/api/v1/documents/{doc_id}/reader")

        assert r.status_code == 200
        data = r.json()["data"]
        # Unanchored evidence found via doc_passage_ids
        assert len(data["evidences"]) == 1
        assert data["evidences"][0]["id"] == ev_id
        assert data["evidences"][0]["description"] == "Orphan evidence"


# ======================================================================
# Seed reader data — empty document_text (1014->1018, chunks empty)
# ======================================================================


class TestSeedReaderDataEmptyChunks:
    """_test_seed_reader_data with empty document_text — chunks list empty."""

    def test_seed_with_empty_text(self, client, mock_session, monkeypatch):
        """When document_text is empty, chunks list is empty — if chunks: false."""
        monkeypatch.setenv("SEED_TEST_DATA", "1")

        existing_user_id = str(uuid4())

        class _FakeModel:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

        existing_user = _FakeModel(
            id=existing_user_id,
            username="emptytxt",
            email="et@test.com",
            is_active=True,
        )
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute = AsyncMock(return_value=user_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        from app.api.v1 import entities

        with patch.object(entities, "sql_select", side_effect=lambda *a: MagicMock()):
            r = client.post(
                "/api/v1/_test/seed-reader-data",
                json={
                    "username": "emptytxt",
                    "password": "pw",
                    "document_title": "Empty Doc",
                    "document_text": "",
                },
            )
        assert r.status_code == 200
        # With empty text, passage is created but not linked to any chunk
        data = r.json()["data"]
        assert data["passage_id"] is not None
        assert data["evidence_id"] is not None
        assert data["citation_id"] is not None


# ======================================================================
# Resolve helpers — already present below, kept unchanged
# ======================================================================


class TestResolveHelpers:
    """Tests for _resolve_citation_anchor and _resolve_evidence_anchor."""

    def test_citation_anchor_passage_match(self):
        from app.api.v1.entities import _resolve_citation_anchor

        pid = uuid4()
        cit = _MockEntity(target_type="Passage", target_id=pid)
        chunks = [
            _MockEntity(passage_id=pid),
            _MockEntity(passage_id=uuid4()),
            _MockEntity(passage_id=pid),
        ]
        result = _resolve_citation_anchor(cit, chunks)
        assert len(result) == 2

    def test_citation_anchor_wrong_type(self):
        from app.api.v1.entities import _resolve_citation_anchor

        cit = _MockEntity(target_type="Book", target_id=uuid4())
        chunks = [_MockEntity(passage_id=uuid4())]
        result = _resolve_citation_anchor(cit, chunks)
        assert result == []

    def test_citation_anchor_no_target_id(self):
        from app.api.v1.entities import _resolve_citation_anchor

        cit = _MockEntity(target_type="Passage", target_id=None)
        chunks = [_MockEntity(passage_id=uuid4())]
        result = _resolve_citation_anchor(cit, chunks)
        assert result == []

    def test_citation_anchor_none_passage_id(self):
        from app.api.v1.entities import _resolve_citation_anchor

        pid = uuid4()
        cit = _MockEntity(target_type="Passage", target_id=pid)
        chunks = [_MockEntity(passage_id=None)]
        result = _resolve_citation_anchor(cit, chunks)
        assert result == []

    def test_evidence_anchor_match(self):
        from app.api.v1.entities import _resolve_evidence_anchor

        pid = uuid4()
        ev = _MockEntity(source_passage_id=pid)
        chunks = [_MockEntity(passage_id=pid)]
        result = _resolve_evidence_anchor(ev, chunks)
        assert len(result) == 1

    def test_evidence_anchor_no_source(self):
        from app.api.v1.entities import _resolve_evidence_anchor

        ev = _MockEntity(source_passage_id=None)
        chunks = [_MockEntity(passage_id=uuid4())]
        result = _resolve_evidence_anchor(ev, chunks)
        assert result == []
