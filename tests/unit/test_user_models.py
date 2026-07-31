"""
Tests for User, Role, Permission models.
"""

from app.db.base import BaseModel
from app.models.user import Permission, Role, User


class TestUserModel:
    """Test User model."""

    def test_user_tablename(self):
        assert User.__tablename__ == "users"

    def test_user_inherits_base_model(self):
        assert issubclass(User, BaseModel)

    def test_user_has_expected_columns(self):
        cols = {c.name for c in User.__table__.columns}
        expected = {
            "id",
            "created_at",
            "updated_at",
            "deleted_at",
            "is_deleted",
            "username",
            "email",
            "hashed_password",
            "display_name",
            "affiliation",
            "is_active",
            "is_superuser",
        }
        assert expected.issubset(cols)

    def test_user_repr(self):
        u = User(username="testuser", email="test@example.com", hashed_password="x")
        assert "testuser" in repr(u)

    def test_user_defaults(self):
        u = User(
            username="u",
            email="u@x.com",
            hashed_password="x",
            is_active=True,
            is_superuser=False,
        )
        assert u.is_active is True
        assert u.is_superuser is False


class TestRoleModel:
    """Test Role model."""

    def test_role_tablename(self):
        assert Role.__tablename__ == "roles"

    def test_role_has_expected_columns(self):
        cols = {c.name for c in Role.__table__.columns}
        expected = {
            "id",
            "created_at",
            "updated_at",
            "deleted_at",
            "is_deleted",
            "name",
            "description",
            "is_system",
        }
        assert expected.issubset(cols)

    def test_role_default_is_system(self):
        r = Role(name="Test", is_system=False)
        assert r.is_system is False


class TestPermissionModel:
    """Test Permission model."""

    def test_permission_tablename(self):
        assert Permission.__tablename__ == "permissions"

    def test_permission_code(self):
        p = Permission(resource="person", action="read")
        assert p.code == "person.read"

    def test_permission_has_expected_columns(self):
        cols = {c.name for c in Permission.__table__.columns}
        expected = {
            "id",
            "created_at",
            "updated_at",
            "deleted_at",
            "is_deleted",
            "resource",
            "action",
            "description",
        }
        assert expected.issubset(cols)


class TestAssociationTables:
    """Test M2M association tables exist."""

    def test_user_role_table_exists(self):
        from app.models.user import user_role

        assert user_role.name == "user_role"

    def test_role_permission_table_exists(self):
        from app.models.user import role_permission

        assert role_permission.name == "role_permission"
