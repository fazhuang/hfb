"""
Repository layer — re-export all repositories.

Current repositories (Sprint 3 scope):
  - BaseRepository (generic CRUD)
  - DocumentRepository
  - PersonRepository
"""

from __future__ import annotations

from app.repositories.base import BaseRepository
from app.repositories.document import DocumentRepository
from app.repositories.person import PersonRepository

__all__ = [
    "BaseRepository",
    "DocumentRepository",
    "PersonRepository",
]
