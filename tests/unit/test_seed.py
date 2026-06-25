"""
Tests for seed data fixtures structure (Sprint 3 scope).
"""

from app.db.seed import SEED_PERSONS, SEED_DOCUMENTS


class TestSeedData:
    """Test that seed data is well-formed."""

    def test_persons_have_names(self):
        for p in SEED_PERSONS:
            assert "name" in p
            assert len(p["name"]) > 0

    def test_persons_have_dynasty(self):
        for p in SEED_PERSONS:
            assert "dynasty" in p

    def test_documents_have_titles(self):
        for d in SEED_DOCUMENTS:
            assert "title" in d
            assert len(d["title"]) > 0

    def test_documents_have_category(self):
        for d in SEED_DOCUMENTS:
            assert "category" in d

    def test_seed_counts(self):
        assert len(SEED_PERSONS) == 3
        assert len(SEED_DOCUMENTS) == 3
