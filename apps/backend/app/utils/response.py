"""
Unified JSON API response helpers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def api_response(
    data: Any = None,
    success: bool = True,
    message: str = "ok",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a standard API response envelope."""
    return {
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "message": message,
        **(meta or {}),
    }
