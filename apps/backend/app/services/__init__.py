"""
Service layer — business logic orchestration.

Current services (Sprint 3 scope):
  - DocumentService
  - PersonService
"""
from __future__ import annotations

from app.services.document_service import DocumentService
from app.services.person_service import PersonService

__all__ = [
    "DocumentService",
    "PersonService",
]
