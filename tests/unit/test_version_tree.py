"""Tests for version tree and distance matrix."""

import pytest
from app.services.version_center import compute_distance_matrix
from tests.conftest_db import db_session  # noqa: F401


@pytest.mark.asyncio
async def test_distance_matrix_empty(db_session):
    """Empty version list -> empty matrix."""
    matrix = await compute_distance_matrix(db_session, [])
    assert matrix == {}


@pytest.mark.asyncio
async def test_distance_matrix_single_version(db_session):
    """Single version -> empty matrix (no pairs)."""
    matrix = await compute_distance_matrix(db_session, ["v1"])
    assert matrix == {}


@pytest.mark.asyncio
async def test_distance_matrix_no_diff_data(db_session):
    """Two versions with no VersionDiff -> max distance."""
    matrix = await compute_distance_matrix(db_session, ["v1", "v2"])
    assert matrix.get("v1-v2", matrix.get("v2-v1")) == 1.0
