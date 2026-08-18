"""Shared grounding-anchor helpers for candidate create and publish flows.

Both the create-time validation (anchors must match the chunk at extraction
time) and the publish-time re-validation (anchors must still match at review
time, catching drift) share the exact same hash and span math. Keeping them in
one module guarantees the two can never drift apart.
"""

from __future__ import annotations

import hashlib
import unicodedata


def chunk_sha256(content: str) -> str:
    """SHA-256 of the raw chunk bytes (UTF-8)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def nfc_sha256(content: str) -> str:
    """SHA-256 of the NFC-normalized chunk bytes (UTF-8)."""
    return hashlib.sha256(
        unicodedata.normalize("NFC", content).encode("utf-8")
    ).hexdigest()


def is_grounding_valid(
    chunk_content: str,
    expected_chunk_sha256: str,
    expected_nfc_sha256: str,
    start_char: int,
    end_char: int,
    exact_text: str,
) -> bool:
    """True when the candidate's anchors exactly pin the live chunk content.

    Validates (1) both hashes, (2) the char span is in-range and ordered, and
    (3) the exact span of the NFC-normalized chunk equals the NFC-normalized
    ``exact_text``.
    """
    normalized_chunk = unicodedata.normalize("NFC", chunk_content)
    normalized_exact = unicodedata.normalize("NFC", exact_text)
    return (
        chunk_sha256(chunk_content) == expected_chunk_sha256
        and nfc_sha256(chunk_content) == expected_nfc_sha256
        and 0 <= start_char < end_char <= len(normalized_chunk)
        and (end_char - start_char) == len(normalized_exact)
        and normalized_chunk[start_char:end_char] == normalized_exact
    )
