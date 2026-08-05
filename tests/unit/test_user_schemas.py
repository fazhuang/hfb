
"""Unit tests for app.schemas.user — mandatory Pydantic model fields."""

from __future__ import annotations

import pytest
from app.schemas.user import UserCreate, UserResponse, LoginRequest, RegisterRequest


class TestLoginRequest:
    def test_basic(self) -> None:
        req = LoginRequest(username="researcher", password="secret")
        assert req.username == "researcher"
        assert req.password == "secret"


class TestRegisterRequest:
    def test_basic(self) -> None:
        req = RegisterRequest(username="researcher", email="r@hfb.org", password="pass123!!")
        assert req.username == "researcher"
        assert req.email == "r@hfb.org"
        assert req.password == "pass123!!"


class TestUserCreate:
    def test_basic(self) -> None:
        u = UserCreate(username="researcher", email="r@hfb.org", password="secret123")
        assert u.username == "researcher"
        assert u.email == "r@hfb.org"
        assert u.password == "secret123"
