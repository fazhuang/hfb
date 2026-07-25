"""
Contract test: OpenAPI must not expose double-prefixed /api/v1/api/v1/ paths.

This test builds the FastAPI app, extracts the OpenAPI schema, and verifies
no route path contains the substring /api/v1/api/v1/.
"""

from __future__ import annotations

import json
import warnings

import pytest


@pytest.fixture(scope="module")
def openapi_paths():
    """Build app once and return sorted path list."""
    # Suppress pre-existing Pydantic non-serializable-default warnings
    # (BookService et al.) — these are known issues, not regressions.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from main import app
        schema = app.openapi()
    return sorted(schema.get("paths", {}).keys())


def test_no_double_v1_prefix_in_openapi(openapi_paths):
    """Assert zero routes match the double-prefix pattern /api/v1/api/v1/."""
    double_prefix_paths = [p for p in openapi_paths if "/api/v1/api/v1/" in p]

    assert double_prefix_paths == [], (
        f"Double-prefix routes found in OpenAPI:\n"
        + "\n".join(double_prefix_paths)
        + f"\n\nFull path list ({len(openapi_paths)} total):\n"
        + json.dumps(openapi_paths, indent=2, ensure_ascii=False)
    )


def test_admin_routes_have_single_v1_prefix(openapi_paths):
    """Admin routes must be mounted under /api/v1/ (exactly once)."""
    admin_routes = [
        p for p in openapi_paths
        if any(kw in p for kw in [
            "/admin/source-policies",
            "/ingestion/tasks",
            "/documents/{document_id}/review",
            "/documents/{document_id}/withdraw",
            "/versions/{version_id}/withdraw",
            "/versions/{version_id}/restore",
        ])
    ]

    assert admin_routes, "Expected admin routes are missing from OpenAPI"

    for route in admin_routes:
        assert route.startswith("/api/v1/"), (
            f"Admin route {route!r} does not start with /api/v1/"
        )
        assert "/api/v1/api/v1/" not in route, (
            f"Admin route {route!r} has double prefix"
        )
