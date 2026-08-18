"""
Application settings management via Pydantic Settings.

Loads from .env file and environment variables.
"""

from __future__ import annotations

import json

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with env file support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Project ---
    PROJECT_NAME: str = "皇甫谧数字人文平台"
    VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

    # --- Backend ---
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_WORKERS: int = 1
    SECRET_KEY: str = "change-me"
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ORIGINS: str = '["http://localhost:5173"]'

    # --- PostgreSQL ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "hfb"
    POSTGRES_USER: str = "hfb"
    POSTGRES_PASSWORD: str = "change-me"

    # --- Redis ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # --- MinIO ---
    MINIO_HOST: str = "localhost"
    MINIO_PORT: int = 9000
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_BUCKET: str = "hfb-data"

    # --- Elasticsearch ---
    ELASTICSEARCH_HOST: str = "localhost"
    ELASTICSEARCH_PORT: int = 9200

    # --- JWT ---
    JWT_SECRET_KEY: str = "change-me-to-a-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Neo4j --- (deferred to Sprint 4)
    # NEO4J_URI: str = "bolt://localhost:7687"
    # NEO4J_USER: str = "neo4j"
    # NEO4J_PASSWORD: str = "neo4j"
    # NEO4J_DATABASE: str = "neo4j"

    # --- AI / LLM ---
    AI_PROVIDER: str = "openai"  # openai | anthropic | local
    AI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o-mini"  # default model
    AI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    AI_BASE_URL: str | None = None  # proxy/alternative endpoint
    AI_MAX_TOKENS: int = 2000
    AI_TEMPERATURE: float = 0.3
    AI_RATE_LIMIT_PER_MINUTE: int = 20

    # --- Literature Ingestion ---
    CONTACT_EMAIL: str = "dev@huangfumi.org"
    CORE_API_KEY: str = ""  # optional, for higher rate limits

    # --- Source admission (classical full-text upload) ---
    # Fail-closed: upload remains frozen until Research Lead completes the manual
    # source admission checklist (docs/03-data/0306_...). Never opened by client
    # input — this env flag is the only unlock switch.
    SOURCE_ADMISSION_OPEN: bool = False

    # --- Database connection string ---
    @property
    def database_url(self) -> str:
        """Async PostgreSQL connection string."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync PostgreSQL connection string (for Alembic)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        """Redis connection string."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def minio_url(self) -> str:
        """MinIO connection URL."""
        return f"{self.MINIO_HOST}:{self.MINIO_PORT}"

    @property
    def elasticsearch_url(self) -> str:
        """Elasticsearch connection URL."""
        return f"http://{self.ELASTICSEARCH_HOST}:{self.ELASTICSEARCH_PORT}"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS from JSON string to list."""
        try:
            origin_list: list[str] = json.loads(self.CORS_ORIGINS)
            return origin_list
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:5173"]


settings = Settings()
