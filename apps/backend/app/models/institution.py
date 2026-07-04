"""
Institution (机构) domain model.

Represents universities, research institutes, archives and other organizations
relevant to Huangfu Mi studies.

Fields restricted per Day 1 spec:
  - id, name, type, location, description, status
  - created_at, updated_at (inherited from BaseModel)
"""
from __future__ import annotations

import enum

from sqlalchemy import String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.exceptions import ValidationException
from app.core.status_machine import is_valid_state, validate_transition
from app.db.base import BaseModel


class InstitutionType(str, enum.Enum):
    """Valid institution types per Day 1 spec."""
    research = "research"
    university = "university"
    archive = "archive"
    institution = "institution"


class InstitutionStatus(str, enum.Enum):
    """Day 1 status machine states."""
    draft = "draft"
    active = "active"
    archived = "archived"
    deleted = "deleted"


class Institution(BaseModel):
    """An organization relevant to Huangfu Mi studies.

    Examples: 复旦大学, 人民卫生出版社, 中国中医科学院, 甘肃博物馆.
    """

    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="机构名称"
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="类型: research / university / archive / institution"
    )
    location: Mapped[str | None] = mapped_column(
        String(300), nullable=True, comment="所在地"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="机构简介"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InstitutionStatus.draft.value,
        server_default="draft",
        comment="状态: draft / active / archived / deleted",
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('research', 'university', 'archive', 'institution')",
            name="ck_institutions_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived', 'deleted')",
            name="ck_institutions_status",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_institutions_name_not_blank",
        ),
    )

    @validates("status")
    def validate_status(self, key, value):
        """Enforce the status machine on every ORM status assignment.

        Bypass vectors blocked:
          1. instance.status = "archived"  → @validates rejects
          2. repo.update(id, status="archived") → setattr → @validates rejects
          3. transition_status → internal setattr → @validates allows legal transitions

        ORM loads from DB pass through safely (current == None on first set).
        """
        if not is_valid_state(value):
            raise ValidationException(
                f"Unknown institution status: '{value}'. "
                f"Valid: draft, active, archived, deleted"
            )
        current = getattr(self, key, None)
        if current is not None:
            validate_transition(current, value)
        return value

    @validates("name")
    def validate_name(self, key, value):
        """Strip whitespace and reject blank/overlong names."""
        if value is None:
            raise ValidationException("Institution name must not be null")
        stripped = value.strip()
        if not stripped:
            raise ValidationException("Institution name must not be empty or whitespace-only")
        if len(stripped) > 300:
            raise ValidationException("Institution name exceeds maximum length of 300")
        return stripped

    @validates("type")
    def validate_type(self, key, value):
        """Reject institution types outside the allowed set."""
        if value not in frozenset({"research", "university", "archive", "institution"}):
            raise ValidationException(
                f"Invalid institution type '{value}'. "
                f"Must be one of: research, university, archive, institution"
            )
        return value

    def __repr__(self) -> str:
        return f"<Institution id={self.id} name={self.name!r} type={self.type}>"
