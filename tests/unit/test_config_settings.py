"""
Unit tests for app.core.config — Settings class.
"""

from __future__ import annotations

import pytest


class TestSettings:
    def test_default_values(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert s.PROJECT_NAME == "皇甫谧数字人文平台"
        assert s.AI_PROVIDER == "deepseek" or s.AI_PROVIDER in ("openai", "local")
        assert s.AI_MAX_TOKENS == 2000
        assert isinstance(s.AI_TEMPERATURE, float)
        assert s.AI_RATE_LIMIT_PER_MINUTE > 0

    def test_database_url(self) -> None:
        from app.core.config import Settings

        s = Settings()
        url = s.database_url
        assert url.startswith("postgresql+asyncpg://")
        assert "hfb:change-me" in url

    def test_database_url_sync(self) -> None:
        from app.core.config import Settings

        s = Settings()
        url = s.database_url_sync
        assert url.startswith("postgresql+psycopg2://")
        assert "hfb:change-me" in url

    def test_redis_url_without_password(self) -> None:
        from app.core.config import Settings

        s = Settings(REDIS_PASSWORD=None)
        url = s.redis_url
        assert "redis://" in url
        assert "@" not in url

    def test_redis_url_with_password(self) -> None:
        from app.core.config import Settings

        s = Settings(REDIS_PASSWORD="secret")
        url = s.redis_url
        assert "redis://:secret@" in url

    def test_minio_url(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert s.minio_url == "localhost:9000"

    def test_elasticsearch_url(self) -> None:
        from app.core.config import Settings

        s = Settings()
        assert s.elasticsearch_url == "http://localhost:9200"

    def test_cors_origins_list_valid_json(self) -> None:
        from app.core.config import Settings

        s = Settings(CORS_ORIGINS='["http://a.com","http://b.com"]')
        origins = s.cors_origins_list
        assert origins == ["http://a.com", "http://b.com"]

    def test_cors_origins_list_invalid_json_fallback(self) -> None:
        from app.core.config import Settings

        s = Settings(CORS_ORIGINS="not-json")
        origins = s.cors_origins_list
        assert origins == ["http://localhost:5173"]

    def test_environment(self) -> None:
        from app.core.config import Settings

        s = Settings(ENVIRONMENT="production")
        assert s.ENVIRONMENT == "production"
