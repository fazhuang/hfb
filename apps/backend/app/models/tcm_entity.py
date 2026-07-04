"""
TCMEntity — generic entity model for ontology types without dedicated tables.

Covers: herb, prescription, meridian, symptom, and any future types.
Each instance is typed by entity_type and carries structured properties as JSON.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class TCMEntity(BaseModel):
    """Generic ontology entity for TCM types (herb, prescription, meridian, symptom, etc.).

    For types with dedicated models (person, book, version, passage), use those models.
    This table covers everything else in the canonical ontology.
    """

    __tablename__ = "tcm_entities"

    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="Entity type from canonical ontology"
    )
    name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="Display name"
    )
    name_zh: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True, comment="Chinese name"
    )
    properties: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="Type-specific properties as JSON"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Description / biography / notes"
    )
    external_ref: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="External reference (Wikidata etc.)"
    )

    def __repr__(self) -> str:
        return f"<TCMEntity type={self.entity_type} name={self.name!r}>"
