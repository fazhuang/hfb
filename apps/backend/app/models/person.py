"""
Person (人物) domain model.
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class Person(BaseModel):
    """A historical figure — author, physician, or scholar.

    Represents a 人物 such as 皇甫谧, 张仲景, or 李时珍.
    """

    __tablename__ = "persons"

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="姓名")
    name_pinyin: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="姓名拼音"
    )
    name_zh: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="中文名 (繁体)"
    )
    courtesy_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="字"
    )
    pseudonym: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="号"
    )
    dynasty: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="朝代"
    )
    birth_year: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="出生年份 (负数=公元前)"
    )
    death_year: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="逝世年份"
    )
    birth_place: Mapped[str | None] = mapped_column(
        String(300), nullable=True, comment="出生地"
    )
    biography: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="生平简介"
    )
    biography_source: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="生平资料来源"
    )
    notable_works: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="代表著作 (逗号分隔)"
    )
    expertise: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="专长领域"
    )
    external_ref: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="外部参考 (Wikidata/百度百科)"
    )

    def __repr__(self) -> str:
        return f"<Person id={self.id} name={self.name!r}>"
