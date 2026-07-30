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

from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.document import (
    DocumentBase,
    DocumentBrief,
    DocumentCreate,
    DocumentResponse,
)
from app.schemas.person import PersonBase, PersonBrief, PersonCreate, PersonResponse

__all__ = [
    "DocumentBase",
    "DocumentBrief",
    "DocumentCreate",
    "DocumentResponse",
    "PaginatedResponse",
    "PaginationParams",
    "PersonBase",
    "PersonBrief",
    "PersonCreate",
    "PersonResponse",
]
