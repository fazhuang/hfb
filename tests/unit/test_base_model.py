"""
Tests for the base database model.
"""

from app.db.base import BaseModel


class DummyModel(BaseModel):
    """Minimal model for testing the base."""
    __tablename__ = "test_dummy"
    __table_args__ = {"extend_existing": True}


class TestBaseModel:
    """Test BaseModel functionality."""

    def test_base_model_has_id(self) -> None:
        """BaseModel should have a primary key."""
        assert hasattr(DummyModel, "id")
        assert "id" in {c.name for c in DummyModel.__table__.columns}

    def test_base_model_has_timestamps(self) -> None:
        """BaseModel should have created_at and updated_at."""
        assert "created_at" in {c.name for c in DummyModel.__table__.columns}
        assert "updated_at" in {c.name for c in DummyModel.__table__.columns}

    def test_base_model_has_soft_delete(self) -> None:
        """BaseModel should have soft delete fields."""
        assert "deleted_at" in {c.name for c in DummyModel.__table__.columns}
        assert "is_deleted" in {c.name for c in DummyModel.__table__.columns}
