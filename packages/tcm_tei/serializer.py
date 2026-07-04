"""TEI serialization — JSON and XML export/import."""

from __future__ import annotations

import json
from typing import Any

from tcm_tei.models import (
    Document,
    TextVersion,
    Paragraph,
    Sentence,
    Token,
    Variant,
)


class TEISerializer:
    """Serialize TEI-structured documents to/from JSON and basic TEI XML."""

    @staticmethod
    def to_json(doc: Document, indent: int | None = 2) -> str:
        """Serialize a Document to JSON string."""
        return json.dumps(_document_to_dict(doc), ensure_ascii=False, indent=indent)

    @staticmethod
    def from_json(data: str) -> Document:
        """Deserialize a Document from JSON string."""
        d = json.loads(data)
        return _document_from_dict(d)

    @staticmethod
    def to_xml(doc: Document, variants: list[Variant] | None = None) -> str:
        """Serialize a Document to TEI XML with critical apparatus.

        Outputs <TEI><teiHeader>...<text><body>... with <app>/<lem>/<rdg>
        for textual variants when variants are provided.
        """
        parts: list[str] = []
        parts.append('<?xml version="1.0" encoding="UTF-8"?>')
        parts.append('<TEI xmlns="http://www.tei-c.org/ns/1.0">')
        parts.append("  <teiHeader>")
        parts.append(f"    <title>{_escape_xml(doc.title)}</title>")
        parts.append("  </teiHeader>")
        parts.append("  <text>")
        parts.append("    <body>")

        for version in doc.versions:
            parts.append(f'      <div type="version" xml:id="{_escape_xml(version.id)}">')
            parts.append(f"        <head>{_escape_xml(version.label)}</head>")
            for para in version.paragraphs:
                parts.append(f'        <p xml:id="{_escape_xml(para.id)}">')
                if para.section:
                    parts.append(f"          <head>{_escape_xml(para.section)}</head>")
                for sent in para.sentences:
                    parts.append(f'          <s xml:id="{_escape_xml(sent.id)}">')
                    parts.append(f"            {_escape_xml(sent.text)}")
                    parts.append("          </s>")
                parts.append("        </p>")
            parts.append("      </div>")

        # Critical apparatus section
        if variants:
            parts.append('      <div type="apparatus">')
            for var in variants:
                parts.append(f'        <app from="{_escape_xml(var.location)}">')
                # First reading is lemma
                readings = list(var.readings.items())
                if readings:
                    first_label, first_text = readings[0]
                    parts.append(f"          <lem>{_escape_xml(first_text)}</lem>")
                for label, text in readings[1:]:
                    parts.append(f'          <rdg wit="{_escape_xml(label)}">{_escape_xml(text)}</rdg>')
                parts.append("        </app>")
            parts.append("      </div>")

        parts.append("    </body>")
        parts.append("  </text>")
        parts.append("</TEI>")
        return "\n".join(parts)

    @staticmethod
    def variants_to_json(variants: list[Variant], indent: int | None = 2) -> str:
        """Serialize variants to JSON string."""
        data = [_variant_to_dict(v) for v in variants]
        return json.dumps(data, ensure_ascii=False, indent=indent)


def _document_to_dict(doc: Document) -> dict[str, Any]:
    return {
        "id": doc.id,
        "title": doc.title,
        "metadata": doc.metadata,
        "versions": [_version_to_dict(v) for v in doc.versions],
    }


def _version_to_dict(ver: TextVersion) -> dict[str, Any]:
    return {
        "id": ver.id,
        "label": ver.label,
        "metadata": ver.metadata,
        "paragraphs": [_paragraph_to_dict(p) for p in ver.paragraphs],
    }


def _paragraph_to_dict(para: Paragraph) -> dict[str, Any]:
    return {
        "id": para.id,
        "section": para.section,
        "sentences": [_sentence_to_dict(s) for s in para.sentences],
    }


def _sentence_to_dict(sent: Sentence) -> dict[str, Any]:
    return {
        "id": sent.id,
        "text": sent.text,
        "tokens": [_token_to_dict(t) for t in sent.tokens],
    }


def _token_to_dict(tok: Token) -> dict[str, Any]:
    return {
        "id": tok.id,
        "text": tok.text,
        "pos": tok.pos,
        "lemma": tok.lemma,
    }


def _variant_to_dict(var: Variant) -> dict[str, Any]:
    return {
        "location": var.location,
        "readings": var.readings,
        "apparatus": var.apparatus,
    }


def _document_from_dict(d: dict[str, Any]) -> Document:
    return Document(
        id=d["id"],
        title=d["title"],
        metadata=d.get("metadata", {}),
        versions=[_version_from_dict(v) for v in d.get("versions", [])],
    )


def _version_from_dict(d: dict[str, Any]) -> TextVersion:
    return TextVersion(
        id=d["id"],
        label=d["label"],
        metadata=d.get("metadata", {}),
        paragraphs=[_paragraph_from_dict(p) for p in d.get("paragraphs", [])],
    )


def _paragraph_from_dict(d: dict[str, Any]) -> Paragraph:
    return Paragraph(
        id=d["id"],
        section=d.get("section"),
        sentences=[_sentence_from_dict(s) for s in d.get("sentences", [])],
    )


def _sentence_from_dict(d: dict[str, Any]) -> Sentence:
    return Sentence(
        id=d["id"],
        tokens=[_token_from_dict(t) for t in d.get("tokens", [])],
        text=d.get("text", ""),
    )


def _token_from_dict(d: dict[str, Any]) -> Token:
    return Token(
        id=d["id"],
        text=d["text"],
        pos=d.get("pos", ""),
        lemma=d.get("lemma"),
    )


def _escape_xml(text: str) -> str:
    """Escape text for XML content."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
