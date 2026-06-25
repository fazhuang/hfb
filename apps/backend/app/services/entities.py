"""
Services for Book, Version, Chapter, Passage, Paper, Image entities.
"""
from __future__ import annotations

from typing import Any

from app.repositories.entities import (
    BookRepository,
    VersionRepository,
    ChapterRepository,
    PassageRepository,
    PaperRepository,
    ImageRepository,
)
from app.schemas.entities import (
    BookCreate,
    BookResponse,
    VersionCreate,
    VersionResponse,
    ChapterCreate,
    ChapterResponse,
    PassageCreate,
    PassageResponse,
    PaperCreate,
    PaperResponse,
    ImageCreate,
    ImageResponse,
)
from app.services.base import BaseService


class BookService(BaseService[BookRepository, BookCreate, BookResponse]):
    repository_class = BookRepository

    async def _validate_create(self, data: dict[str, Any]) -> None:
        if not data.get("title", "").strip():
            raise ValueError("Book title is required")

    async def search(self, query: str, page: int = 1, limit: int = 20):
        return await self.repo.search_query(query, page=page, limit=limit)


class VersionService(BaseService[VersionRepository, VersionCreate, VersionResponse]):
    repository_class = VersionRepository

    async def _validate_create(self, data: dict[str, Any]) -> None:
        if not data.get("version_name", "").strip():
            raise ValueError("Version name is required")
        if not data.get("book_id", ""):
            raise ValueError("book_id is required")

    async def search(self, query: str, page: int = 1, limit: int = 20):
        return await self.repo.search_query(query, page=page, limit=limit)


class ChapterService(BaseService[ChapterRepository, ChapterCreate, ChapterResponse]):
    repository_class = ChapterRepository

    async def _validate_create(self, data: dict[str, Any]) -> None:
        if not data.get("title", "").strip():
            raise ValueError("Chapter title is required")
        if not data.get("book_id", ""):
            raise ValueError("book_id is required")

    async def search(self, query: str, page: int = 1, limit: int = 20):
        return await self.repo.search_query(query, page=page, limit=limit)


class PassageService(BaseService[PassageRepository, PassageCreate, PassageResponse]):
    repository_class = PassageRepository

    async def _validate_create(self, data: dict[str, Any]) -> None:
        if not data.get("content_text", "").strip():
            raise ValueError("Passage content_text is required")
        if not data.get("chapter_id", ""):
            raise ValueError("chapter_id is required")

    async def search(self, query: str, page: int = 1, limit: int = 20):
        return await self.repo.search_query(query, page=page, limit=limit)


class PaperService(BaseService[PaperRepository, PaperCreate, PaperResponse]):
    repository_class = PaperRepository

    async def _validate_create(self, data: dict[str, Any]) -> None:
        if not data.get("title", "").strip():
            raise ValueError("Paper title is required")

    async def search(self, query: str, page: int = 1, limit: int = 20):
        return await self.repo.search_query(query, page=page, limit=limit)


class ImageService(BaseService[ImageRepository, ImageCreate, ImageResponse]):
    repository_class = ImageRepository

    async def _validate_create(self, data: dict[str, Any]) -> None:
        if not data.get("url", "").strip():
            raise ValueError("Image URL is required")
        if not data.get("related_entity_type", ""):
            raise ValueError("related_entity_type is required")
        if not data.get("related_entity_id", ""):
            raise ValueError("related_entity_id is required")
