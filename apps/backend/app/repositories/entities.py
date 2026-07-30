"""
Repositories for Book, Version, Chapter, Passage, Paper, Image entities.
"""
from __future__ import annotations

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.image import Image
from app.models.paper import Paper
from app.models.passage import Passage
from app.models.version import Version
from app.repositories.base import BaseRepository


class BookRepository(BaseRepository[Book]):
    model = Book

    def search_query(self, query: str, page: int = 1, limit: int = 20):
        return self.search(
            search_fields=["title", "title_pinyin", "title_english", "abstract"],
            query=query,
            page=page,
            limit=limit,
        )


class VersionRepository(BaseRepository[Version]):
    model = Version

    def search_query(self, query: str, page: int = 1, limit: int = 20):
        return self.search(
            search_fields=["version_name", "repository", "editor", "description"],
            query=query,
            page=page,
            limit=limit,
        )


class ChapterRepository(BaseRepository[Chapter]):
    model = Chapter

    def search_query(self, query: str, page: int = 1, limit: int = 20):
        return self.search(
            search_fields=["title", "description"],
            query=query,
            page=page,
            limit=limit,
        )


class PassageRepository(BaseRepository[Passage]):
    model = Passage

    def search_query(self, query: str, page: int = 1, limit: int = 20):
        return self.search(
            search_fields=["content_text", "translation", "notes"],
            query=query,
            page=page,
            limit=limit,
        )


class PaperRepository(BaseRepository[Paper]):
    model = Paper

    def search_query(self, query: str, page: int = 1, limit: int = 20):
        return self.search(
            search_fields=["title", "title_english", "authors", "abstract", "keywords"],
            query=query,
            page=page,
            limit=limit,
        )


class ImageRepository(BaseRepository[Image]):
    model = Image

    def search_query(self, query: str, page: int = 1, limit: int = 20):
        return self.search(
            search_fields=["caption", "source"],
            query=query,
            page=page,
            limit=limit,
        )
