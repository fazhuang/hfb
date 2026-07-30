"""Version comparison engine for TEI documents.

Compares sentences across two versions of the same text,
identifying variants, insertions, and deletions.
"""

from __future__ import annotations

from tcm_tei.models import (
    Paragraph,
    Sentence,
    TextVersion,
    Variant,
)


def _lcs_align_sentences(
    sents_a: list[Sentence],
    sents_b: list[Sentence],
    ignore_whitespace: bool = False,
) -> list[tuple[Sentence | None, Sentence | None]]:
    """Align sentences using longest common subsequence on text.

    Builds a DP table over sentence texts, then backtracks to produce
    (s_a, s_b) pairs. Unmatched sentences get None on the other side.
    This tolerates insertions, deletions, and transpositions that
    position-based alignment would misalign.

    When ignore_whitespace is True, whitespace differences are ignored
    when comparing sentence texts for alignment purposes.
    """
    m, n = len(sents_a), len(sents_b)
    # DP table: dp[i][j] = LCS length for sents_a[:i], sents_b[:j]
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            ta = _clean(sents_a[i - 1].text, ignore_whitespace)
            tb = _clean(sents_b[j - 1].text, ignore_whitespace)
            if ta == tb:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Backtrack
    aligned: list[tuple[Sentence | None, Sentence | None]] = []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            ta = _clean(sents_a[i - 1].text, ignore_whitespace)
            tb = _clean(sents_b[j - 1].text, ignore_whitespace)
            if ta == tb:
                aligned.append((sents_a[i - 1], sents_b[j - 1]))
                i -= 1
                j -= 1
                continue
        if j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
            aligned.append((None, sents_b[j - 1]))
            j -= 1
        else:
            aligned.append((sents_a[i - 1], None))
            i -= 1

    aligned.reverse()
    return aligned


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
        algorithm: str = "lcs",
    ) -> list[Variant]:
        """Compute all variants between two versions using LCS alignment.

        Uses LCS alignment so that inserted/deleted sentences don't cause
        every subsequent pair to be misaligned and reported as false variants.
        """
        variants: list[Variant] = []
        max_paras = max(version_a.paragraph_count, version_b.paragraph_count)

        for i in range(max_paras):
            para_a = version_a.paragraphs[i] if i < version_a.paragraph_count else None
            para_b = version_b.paragraphs[i] if i < version_b.paragraph_count else None

            if para_a is None and para_b is not None:
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

            assert para_a is not None and para_b is not None
            # LCS-align sentences, then compare aligned pairs
            aligned = _lcs_align_sentences(para_a.sentences, para_b.sentences, ignore_whitespace)
            for idx, (s_a, s_b) in enumerate(aligned):
                text_a = _clean(s_a.text, ignore_whitespace) if s_a else ""
                text_b = _clean(s_b.text, ignore_whitespace) if s_b else ""

                if text_a != text_b:
                    variants.append(
                        Variant(
                            location=f"{para_a.id}.sent_{idx}",
                            readings={
                                version_a.id: s_a.text if s_a else "(absent)",
                                version_b.id: s_b.text if s_b else "(absent)",
                            },
                            apparatus=f"差异: [{version_a.id}] vs [{version_b.id}]",
                        )
                    )

        return variants

    @staticmethod
    def align(
        version_a: TextVersion,
        version_b: TextVersion,
        algorithm: str = "lcs",
    ) -> list[tuple[Sentence | None, Sentence | None]]:
        """Align sentences between two versions using LCS sequence alignment.

        Returns a list of (sentence_a, sentence_b) pairs. Where a sentence
        exists in only one version, the other side is None.

        The LCS algorithm tolerates insertions and deletions — a single added
        sentence no longer misaligns every subsequent sentence pair.
        """
        aligned: list[tuple[Sentence | None, Sentence | None]] = []
        max_paras = max(version_a.paragraph_count, version_b.paragraph_count)

        for i in range(max_paras):
            para_a = version_a.paragraphs[i] if i < version_a.paragraph_count else None
            para_b = version_b.paragraphs[i] if i < version_b.paragraph_count else None
            sents_a = para_a.sentences if para_a else []
            sents_b = para_b.sentences if para_b else []

            if algorithm == "lcs":
                aligned.extend(_lcs_align_sentences(sents_a, sents_b))
            else:
                # fallback: original position-based
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
