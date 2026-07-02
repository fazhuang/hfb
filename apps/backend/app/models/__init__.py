"""
HFB Domain Models — SQLAlchemy 2.0 async ORM models.

Core entities:
  - Document (文献), Person (人物)           [Phase 1]
  - User, Role, Permission                     [Phase 2]
  - Book, Version, Chapter, Passage, Paper, Image  [Phase 3]
  - EntityRelation                             [Phase 6] Knowledge Graph
  - ResearchSession, ResearchNote              [Phase 8] AI Workspace
  - Institution                                [Sprint 1 Day 1]
"""
from __future__ import annotations

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.graph import EntityRelation
from app.models.image import Image
from app.models.institution import Institution
from app.models.paper import Paper
from app.models.passage import Passage
from app.models.person import Person
from app.models.user import User, Role, Permission
from app.models.version import Version
from app.models.workspace import ResearchSession, ResearchNote, QueryHistory, CitationCollection

__all__ = [
    "Book",
    "Chapter",
    "CitationCollection",
    "Document",
    "DocumentChunk",
    "EntityRelation",
    "Image",
    "Institution",
    "Paper",
    "Passage",
    "Person",
    "Permission",
    "QueryHistory",
    "ResearchNote",
    "ResearchSession",
    "Role",
    "User",
    "Version",
]
