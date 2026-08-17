"""
HFB Domain Models — SQLAlchemy 2.0 async ORM models.

Core entities:
  - Document (文献), Person (人物)           [Phase 1]
  - User, Role, Permission                     [Phase 2]
  - Book, Version, Chapter, Passage, Paper, Image  [Phase 3]
  - EntityRelation                             [Phase 6] Knowledge Graph
  - TCMEntity                                  [Phase 3] TCM ontology
  - TextSentence, TextToken, TextualVariant    [Phase 4] TEI persistence
  - ResearchSession, ResearchNote              [Phase 8] AI Workspace
  - Institution                                [Sprint 1 Day 1]
  - Sentence, Token, Variant, VariantType      [Phase 2] Version criticism
  - SourceRef, Evidence, Citation, EvidenceLevel  [Phase 2] Academic evidence
  - AcademicEntity, AcademicRelation, RelationConfidence, AcademicEntityType  [Phase 2] Academic relations
"""

from __future__ import annotations

from app.models.academic_evidence import Citation, Evidence, EvidenceLevel, SourceRef
from app.models.academic_relation import (
    AcademicEntity,
    AcademicEntityType,
    AcademicRelation,
    RelationConfidence,
)
from app.models.book import Book
from app.models.candidate_audit_log import CandidateAuditLog
from app.models.candidate_extraction import CandidateExtraction, CandidateStatus
from app.models.chapter import Chapter
from app.models.classical_version import ClassicalVersion
from app.models.commentary import Commentary
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.fulltext_ingestion_audit import FulltextIngestionAudit
from app.models.graph import EntityRelation
from app.models.image import Image
from app.models.institution import Institution
from app.models.paper import Paper
from app.models.passage import Passage
from app.models.person import Person
from app.models.source_policy import SourcePolicy
from app.models.tcm_entity import TCMEntity  # noqa: F401 — Phase 3 TCM ontology
from app.models.tei import (  # noqa: F401 — Phase 4 TEI
    TextSentence,
    TextToken,
    TextualVariant,
)
from app.models.user import Permission, Role, User
from app.models.version import Version
from app.models.version_criticism import Sentence, Token, Variant, VariantType
from app.models.workspace import (
    CitationCollection,
    QueryHistory,
    ResearchNote,
    ResearchSession,
)

__all__ = [
    "AcademicEntity",
    "AcademicEntityType",
    "AcademicRelation",
    "Book",
    "CandidateAuditLog",
    "CandidateExtraction",
    "CandidateStatus",
    "Chapter",
    "Citation",
    "CitationCollection",
    "ClassicalVersion",
    "Commentary",
    "Document",
    "DocumentChunk",
    "EntityRelation",
    "Evidence",
    "EvidenceLevel",
    "FulltextIngestionAudit",
    "Image",
    "Institution",
    "Paper",
    "Passage",
    "Permission",
    "Person",
    "QueryHistory",
    "RelationConfidence",
    "ResearchNote",
    "ResearchSession",
    "Role",
    "Sentence",
    "SourcePolicy",
    "SourceRef",
    "Token",
    "User",
    "Variant",
    "VariantType",
    "Version",
]
