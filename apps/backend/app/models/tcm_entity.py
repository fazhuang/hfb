"""
TCMEntity — generic entity model for ontology types without dedicated tables.

Covers: herb, prescription, meridian, symptom, and any future types.
Each instance is typed by entity_type and carries structured properties as JSON.
"""

from __future__ import annotations

from sqlalchemy import JSON, CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class TCMEntity(BaseModel):
    """Generic ontology entity for TCM types (herb, prescription, meridian, symptom, etc.).

    For types with dedicated models (person, book, version, passage), use those models.
    This table covers everything else in the canonical ontology.
    """

    __tablename__ = "tcm_entities"

    __table_args__ = (
        CheckConstraint(
            "entity_type IN ("
            "'person','book','version','passage','text',"
            "'herb','prescription','meridian','symptom','syndrome')",
            name="ck_tcm_entities_entity_type",
        ),
    )

    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="Entity type from canonical ontology"
    )
    name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="Display name"
    )
    name_zh: Mapped[str | None] = mapped_column(
        String(300), nullable=True, comment="Chinese name"
    )
    properties: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Type-specific properties as JSON"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Description / biography / notes"
    )
    external_ref: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="External reference (Wikidata etc.)"
    )

    def __repr__(self) -> str:
        return f"<TCMEntity type={self.entity_type} name={self.name!r}>"
