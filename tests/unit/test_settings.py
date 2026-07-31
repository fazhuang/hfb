"""
Tests for core configuration settings.
"""

from app.core.config import Settings


class TestSettings:
    """Test application settings."""

    def test_default_settings(self) -> None:
        """Settings should load with defaults."""
        settings = Settings()
        assert settings.PROJECT_NAME == "皇甫谧数字人文平台"
        assert settings.VERSION == "0.2.0"
        assert settings.ENVIRONMENT == "development"
        assert settings.BACKEND_PORT == 8000

    def test_database_url_property(self) -> None:
        """database_url should build correct asyncpg URL."""
        settings = Settings(
            POSTGRES_USER="test_user",
            POSTGRES_PASSWORD="secret",
            POSTGRES_HOST="db.example.com",
            POSTGRES_PORT=5432,
            POSTGRES_DB="testdb",
        )
        url = settings.database_url
        assert url.startswith("postgresql+asyncpg://")
        assert "test_user:secret@db.example.com:5432/testdb" in url

    def test_redis_url_property(self) -> None:
        """redis_url should build correct URL."""
        s1 = Settings(REDIS_HOST="redis.local", REDIS_PORT=6379, REDIS_DB=0)
        assert s1.redis_url == "redis://redis.local:6379/0"

        s2 = Settings(
            REDIS_HOST="redis.local", REDIS_PORT=6380, REDIS_DB=1, REDIS_PASSWORD="abc"
        )
        assert "redis://:abc@redis.local:6380/1" in s2.redis_url

    def test_minio_url(self) -> None:
        """minio_url should build correctly."""
        s1 = Settings(MINIO_HOST="minio.local", MINIO_PORT=9000)
        assert s1.minio_url == "minio.local:9000"

    def test_cors_origins_list(self) -> None:
        """cors_origins_list should parse JSON array."""
        s1 = Settings()
        assert "http://localhost:5173" in s1.cors_origins_list

        s2 = Settings(CORS_ORIGINS='["http://a.com","http://b.com"]')
        assert s2.cors_origins_list == ["http://a.com", "http://b.com"]
