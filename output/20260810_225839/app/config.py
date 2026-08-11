"""
Application settings loaded from environment/.env file.
"""
from pydantic_settings import BaseSettings
from pydantic import HttpUrl, Field
from typing import Optional


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    base_url: str = Field(
        default="http://localhost:8000",
        alias="BASE_URL",
    )
    short_code_length: int = Field(
        default=6,
        ge=4,
        le=10,
        alias="SHORT_CODE_LENGTH",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        alias="CACHE_TTL_SECONDS",
    )
    rate_limit_shorten: str = Field(
        default="10/minute",
        alias="RATE_LIMIT_SHORTEN",
    )
    rate_limit_redirect: str = Field(
        default="100/minute",
        alias="RATE_LIMIT_REDIRECT",
    )
    rate_limit_stats: str = Field(
        default="30/minute",
        alias="RATE_LIMIT_STATS",
    )
    rate_limit_delete: str = Field(
        default="10/minute",
        alias="RATE_LIMIT_DELETE",
    )
    # Background sync interval in seconds (for Redis->DB click count sync)
    sync_interval_seconds: int = Field(
        default=300,  # 5 minutes
        alias="SYNC_INTERVAL_SECONDS",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()