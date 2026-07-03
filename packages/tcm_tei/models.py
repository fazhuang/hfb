"""TEI data models for structured classical text."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Token:
    """A single token (character or word) in the text.

    For classical Chinese, a token is typically one character.
    Punctuation and whitespace are included as tokens.
    """

    id: str  # "tok_N"
    text: str
    pos: str = ""  # part-of-speech tag (optional)
    lemma: str | None = None  # normalized form


@dataclass
class Sentence:
    """A sentence composed of tokens.

    For classical Chinese, a 'sentence' is a 句 — a complete semantic unit
    delimited by 。！？ or natural clause boundaries.
    """

    id: str  # "sent_N"
    tokens: list[Token] = field(default_factory=list)
    text: str = ""  # ponytail: recomputed from tokens when tokens change

    def __post_init__(self) -> None:
        if not self.text:
            self.text = "".join(t.text for t in self.tokens)


@dataclass
class Paragraph:
    """A paragraph (段) — a logical unit of content.

    Contains one or more sentences. May have a section annotation
    (e.g. "卷一·序", "针灸禁忌").
    """

    id: str  # "para_N"
    sentences: list[Sentence] = field(default_factory=list)
    section: str | None = None  # section heading or annotation

    @property
    def text(self) -> str:
        return "".join(s.text for s in self.sentences)


@dataclass
class Variant:
    """An 异文 (textual variant) — different readings across versions.

    Attributes:
        location: Reference to the paragraph + sentence where the variant occurs
        readings: Map of version_id → text for this position
        apparatus: 校勘记 (critical apparatus annotation)
    """

    location: str  # "para_N.sent_M" or "para_N"
    readings: dict[str, str] = field(default_factory=dict)  # {version_id: text}
    apparatus: str | None = None  # scholarly annotation


@dataclass
class TextVersion:
    """A specific version (版本) of a text.

    Each version represents a distinct edition or manuscript.
    Examples: "宋本", "明赵府居敬堂刊本", "现代标点本"
    """

    id: str
    label: str  # human-readable label
    paragraphs: list[Paragraph] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Typical metadata: dynasty, year, editor, publisher, format, notes

    @property
    def paragraph_count(self) -> int:
        return len(self.paragraphs)

    @property
    def sentence_count(self) -> int:
        return sum(len(p.sentences) for p in self.paragraphs)

    @property
    def full_text(self) -> str:
        return "".join(p.text for p in self.paragraphs)


@dataclass
class Document:
    """A document (文献) — the abstract identity of a text.

    A document has one or more TextVersions.
    Example: 《针灸甲乙经》 has versions: 宋本, 明刊本, 现代标点本.
    """

    id: str
    title: str
    versions: list[TextVersion] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_version(self, version_id: str) -> TextVersion | None:
        """Find a version by ID."""
        for v in self.versions:
            if v.id == version_id:
                return v
        return None
