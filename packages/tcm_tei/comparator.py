"""Version comparison engine for TEI documents.

Compares sentences across two versions of the same text,
identifying variants, insertions, and deletions.
"""

from __future__ import annotations

from tcm_tei.models import (
    TextVersion,
    Paragraph,
    Sentence,
    Variant,
    Token,
)


class VersionComparator:
    """Compare two text versions to identify 异文 (variants).

    >>> v1 = TextVersion(id="song_ben", label="宋本")
    >>> v2 = TextVersion(id="ming_ben", label="明本")
    >>> comp = VersionComparator()
    >>> variants = comp.diff(v1, v2)
    """

    @staticmethod
    def diff(
        version_a: TextVersion,
        version_b: TextVersion,
        ignore_whitespace: bool = True,
    ) -> list[Variant]:
        """Compute all variants between two versions.

        Aligns paragraphs and sentences, then compares text at the
        sentence level. Returns a list of Variant objects for positions
        where the text differs.
        """
        variants: list[Variant] = []
        max_paras = max(version_a.paragraph_count, version_b.paragraph_count)

        for i in range(max_paras):
            para_a = version_a.paragraphs[i] if i < version_a.paragraph_count else None
            para_b = version_b.paragraphs[i] if i < version_b.paragraph_count else None

            if para_a is None and para_b is not None:
                # Entire paragraph inserted in version B
                variants.append(
                    Variant(
                        location=f"para_{i}",
                        readings={
                            version_a.id: "(absent)",
                            version_b.id: para_b.text,
                        },
                        apparatus="Paragraph present only in " + version_b.id,
                    )
                )
                continue

            if para_b is None and para_a is not None:
                # Entire paragraph deleted in version B
                variants.append(
                    Variant(
                        location=f"para_{i}",
                        readings={
                            version_a.id: para_a.text,
                            version_b.id: "(absent)",
                        },
                        apparatus="Paragraph present only in " + version_a.id,
                    )
                )
                continue

            # Both paragraphs exist — compare sentences
            if para_a is None or para_b is None:
                continue  # Unreachable, but type-safe

            sent_variants = _compare_paragraph(
                para_a, para_b, version_a.id, version_b.id, ignore_whitespace
            )
            variants.extend(sent_variants)

        return variants

    @staticmethod
    def align(
        version_a: TextVersion,
        version_b: TextVersion,
    ) -> list[tuple[Sentence | None, Sentence | None]]:
        """Align sentences between two versions.

        Returns a list of (sentence_a, sentence_b) pairs. Where a sentence
        exists in only one version, the other side is None.

        ponytail: simple position-based alignment. Full sequence alignment
        with Smith-Waterman if needed for serious scholarship.
        """
        aligned: list[tuple[Sentence | None, Sentence | None]] = []
        max_paras = max(version_a.paragraph_count, version_b.paragraph_count)

        for i in range(max_paras):
            para_a = version_a.paragraphs[i] if i < version_a.paragraph_count else None
            para_b = version_b.paragraphs[i] if i < version_b.paragraph_count else None

            sents_a = para_a.sentences if para_a else []
            sents_b = para_b.sentences if para_b else []
            max_sents = max(len(sents_a), len(sents_b))

            for j in range(max_sents):
                s_a = sents_a[j] if j < len(sents_a) else None
                s_b = sents_b[j] if j < len(sents_b) else None
                aligned.append((s_a, s_b))

        return aligned


def _compare_paragraph(
    para_a: Paragraph,
    para_b: Paragraph,
    version_a_id: str,
    version_b_id: str,
    ignore_whitespace: bool,
) -> list[Variant]:
    """Compare two paragraphs sentence-by-sentence, returning variants."""
    variants: list[Variant] = []
    max_sents = max(len(para_a.sentences), len(para_b.sentences))
    para_id = para_a.id

    for j in range(max_sents):
        s_a = para_a.sentences[j] if j < len(para_a.sentences) else None
        s_b = para_b.sentences[j] if j < len(para_b.sentences) else None
        text_a = _clean(s_a.text, ignore_whitespace) if s_a else ""
        text_b = _clean(s_b.text, ignore_whitespace) if s_b else ""

        if text_a != text_b:
            variants.append(
                Variant(
                    location=f"{para_id}.sent_{j}",
                    readings={
                        version_a_id: s_a.text if s_a else "(absent)",
                        version_b_id: s_b.text if s_b else "(absent)",
                    },
                    apparatus=f"差异: [{version_a_id}] vs [{version_b_id}]",
                )
            )

    return variants


def _clean(text: str, ignore_whitespace: bool) -> str:
    if ignore_whitespace:
        return text.replace(" ", "").replace("\n", "").replace("\t", "")
    return text
