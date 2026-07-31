"""
Tests for user/role/permission Pydantic schemas.
"""

import pytest
from app.schemas.user import (
    LoginRequest,
    RegisterRequest,
    RoleCreate,
    UserCreate,
    UserUpdate,
)
from pydantic import ValidationError


class TestLoginSchema:
    def test_valid(self):
        r = LoginRequest(username="admin", password="secret")
        assert r.username == "admin"

    def test_empty_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="secret")

    def test_empty_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="admin", password="")


class TestRegisterSchema:
    def test_valid(self):
        r = RegisterRequest(
            username="newuser", email="new@test.com", password="secret123"
        )
        assert r.email == "new@test.com"

    def test_short_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="newuser", email="new@test.com", password="short")

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="newuser", email="not-an-email", password="secret123"
            )

    def test_short_username(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="x", email="x@test.com", password="secret123")


class TestUserSchema:
    def test_create_valid(self):
        u = UserCreate(username="admin", email="admin@test.com", password="admin123456")
        assert u.is_active is True
        assert u.is_superuser is False

    def test_update_partial(self):
        u = UserUpdate(display_name="New Name")
        assert u.display_name == "New Name"
        assert u.email is None
        assert u.password is None


class TestRoleSchema:
    def test_create_valid(self):
        r = RoleCreate(name="Test Role", description="A test role")
        assert r.name == "Test Role"

    def test_create_empty_name(self):
        with pytest.raises(ValidationError):
            RoleCreate(name="")
