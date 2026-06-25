"""
Pydantic schemas for API request/response validation.

Schemas follow the pattern:
  - {Entity}Base — shared fields
  - {Entity}Create — fields for POST/PUT
  - {Entity}Response — fields returned by API
  - {Entity}Brief — minimal representation for lists

Current entities (Sprint 3 scope):
  - Document, Person

Future entities (Sprint 4+):
  - Book, Version, Chapter, Passage, Paper, Image, Place, Event, Concept
"""
from __future__ import annotations

from app.schemas.document import DocumentBase, DocumentCreate, DocumentResponse, DocumentBrief
from app.schemas.person import PersonBase, PersonCreate, PersonResponse, PersonBrief
from app.schemas.common import PaginationParams, PaginatedResponse

__all__ = [
    "DocumentBase",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentBrief",
    "PersonBase",
    "PersonCreate",
    "PersonResponse",
    "PersonBrief",
    "PaginationParams",
    "PaginatedResponse",
]
