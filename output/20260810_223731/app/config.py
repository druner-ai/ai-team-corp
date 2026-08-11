"""
Application settings loaded from environment variables using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the URL shortener service."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Base URL for constructing short URLs (no trailing slash)
    BASE_URL: str = "http://localhost:8000"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    # Cache TTL for redirects (seconds)
    CACHE_TTL_SECONDS: int = 3600

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Singleton instance
settings = Settings()