"""
Domain admission service — verification logic for domain status and anchor paths.
"""

from __future__ import annotations

import json
from typing import Sequence

VALID_START_NODES = {"person:huangfu_mi", "ENTITY-PER-0001"}
KNOWN_RELATIONS = {
    "authored",
    "compiled",
    "compiled_from",
    "commented_on",
    "cited_in",
    "studied",
    "compared",
    "referenced",
    "related_to",
    "contains",
    "treats",
    "corresponds_to",
    "indicates",
}


def _calculate_path_steps(path: list[str]) -> int:
    """Calculate step count N (hop count between nodes) for anchor path."""
    if len(path) <= 1:
        return 0
    # Check if alternating relations are present (e.g. node, rel, node, rel...)
    if path[1] in KNOWN_RELATIONS or any(
        item in KNOWN_RELATIONS for item in path[1::2]
    ):
        return (len(path) - 1) // 2
    return len(path) - 1


def verify_domain_anchor_path(
    anchor_path: list[str] | str | None,
    status: str,
) -> bool:
    """Verify domain anchor backtrace path.

    When status is 'verified':
    - anchor_path cannot be empty or None
    - anchor_path start node must be 'person:huangfu_mi' or 'ENTITY-PER-0001'
    - path step count N must be <= 3

    Otherwise raises ValueError.
    For non-'verified' statuses, returns True.
    """
    if status != "verified":
        return True

    parsed_path: list[str] | None = None
    if isinstance(anchor_path, str):
        try:
            parsed = json.loads(anchor_path)
            if isinstance(parsed, list):
                parsed_path = [str(item) for item in parsed]
            else:
                raise ValueError("Parsed JSON is not a list")
        except Exception as err:
            raise ValueError(f"Invalid JSON string for anchor_path: {err}") from err
    elif isinstance(anchor_path, Sequence) and not isinstance(anchor_path, (str, bytes)):
        parsed_path = [str(item) for item in anchor_path]

    if not parsed_path:
        raise ValueError("anchor_path cannot be empty when domain status is 'verified'")

    start_node = parsed_path[0]
    if start_node not in VALID_START_NODES:
        raise ValueError(
            f"Invalid start node '{start_node}' in anchor_path. "
            f"Must start with 'person:huangfu_mi' or 'ENTITY-PER-0001'."
        )

    steps = _calculate_path_steps(parsed_path)
    if steps > 3:
        raise ValueError(
            f"Anchor path step length N={steps} exceeds maximum allowed limit of 3."
        )

    return True
