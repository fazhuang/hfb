"""
Paragraph-based text chunking — deterministic, no ML required.

Produces contiguous, non-overlapping chunks split on paragraph boundaries.
If a single paragraph exceeds max_chars, falls back to fixed-size splitting.
"""
from __future__ import annotations


def chunk_text(
    text: str,
    max_chars: int = 1000,
    overlap_chars: int = 0,
    return_indices: bool = False,
) -> list[str] | list[tuple[str, int]]:
    """Split text into chunks on paragraph boundaries.

    Deterministic algorithm:
      1. Split on double-newline (paragraph boundary).
      2. Greedily merge paragraphs until chunk exceeds max_chars.
      3. If a single paragraph exceeds max_chars, split at sentence
         boundaries within it (fallback: character split).

    If return_indices=True, returns list of (chunk, first_paragraph_index).
    Otherwise returns list of chunk strings.
    """
    if not text or not text.strip():
        return []

    paragraphs = _split_paragraphs(text)
    return _build_chunks(paragraphs, max_chars, return_indices=return_indices)


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraph units, preserving structure."""
    raw = text.split("\n\n")
    result: list[str] = []
    for p in raw:
        p = p.strip()
        if p:
            result.append(p)
    return result


def _build_chunks(
    paragraphs: list[str],
    max_chars: int,
    return_indices: bool = False,
) -> list[str] | list[tuple[str, int]]:
    """Greedy paragraph merging into chunks.

    If return_indices=True, each result is (chunk_text, first_paragraph_index).
    """
    chunks: list[str] = []
    indices: list[int] = []
    current: list[str] = []
    current_first_idx: int = 0
    current_len = 0

    for i, para in enumerate(paragraphs):
        para_len = len(para)

        # If a single paragraph is too large, split it
        if para_len > max_chars:
            # Flush current chunk
            if current:
                chunks.append("\n\n".join(current))
                indices.append(current_first_idx)
                current = []
                current_len = 0
            # Split oversized paragraph
            chunks.extend(_split_long_paragraph(para, max_chars))
            indices.extend([i] * len(_split_long_paragraph(para, max_chars)))
            continue

        # Would adding this paragraph overflow?
        separator_len = 2 if current else 0
        if current_len + separator_len + para_len > max_chars:
            # Flush current chunk and start a new one
            chunks.append("\n\n".join(current))
            indices.append(current_first_idx)
            current = [para]
            current_first_idx = i
            current_len = para_len
        else:
            if not current:
                current_first_idx = i
            current.append(para)
            current_len += separator_len + para_len

    if current:
        chunks.append("\n\n".join(current))
        indices.append(current_first_idx)

    if return_indices:
        return list(zip(chunks, indices))
    return chunks


def _split_long_paragraph(text: str, max_chars: int) -> list[str]:
    """Split a single paragraph that exceeds max_chars.

    Tries sentence boundaries first, falls back to character split.
    """
    # Try sentence boundaries (。！？!? followed by optional newline)
    sentences: list[str] = []
    buf = ""
    for ch in text:
        buf += ch
        if ch in "。！？!?":
            sentences.append(buf)
            buf = ""
    if buf.strip():
        sentences.append(buf)

    # If no sentence boundaries found (e.g. pure ASCII, no punctuation),
    # fall back to character split.
    if len(sentences) <= 1:
        return _char_split(text, max_chars)

    # Merge sentences into chunks
    result: list[str] = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) > max_chars and current:
            result.append(current)
            current = sent
            # If this single sentence still too long, character split
            if len(current) > max_chars:
                result.append(current)
                result.extend(_char_split(current, max_chars))
                current = ""
        else:
            current += sent

    if current:
        result.append(current)

    return result


def _char_split(text: str, max_chars: int) -> list[str]:
    """Last resort: split by fixed character count."""
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]
