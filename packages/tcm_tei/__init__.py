"""TCM TEI — 文献结构化系统.

Structured text model for classical Chinese medical texts.
Hierarchy: Document → TextVersion → Paragraph → Sentence → Token
Supports variant (异文) tracking and version comparison.
"""

from tcm_tei.models import (
    Token,
    Sentence,
    Paragraph,
    Variant,
    TextVersion,
    Document,
)
from tcm_tei.comparator import VersionComparator
from tcm_tei.serializer import TEISerializer

__all__ = [
    "Token",
    "Sentence",
    "Paragraph",
    "Variant",
    "TextVersion",
    "Document",
    "VersionComparator",
    "TEISerializer",
]
