"""
Application configuration using pydantic-settings.
Loads configuration from environment variables and .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        DATABASE_URL: PostgreSQL connection string with asyncpg driver
        REDIS_URL: Redis connection string
        RATE_LIMIT_PER_MINUTE: Maximum requests per minute per IP
        SHORT_ID_LENGTH: Length of generated short IDs
        CACHE_TTL_SECONDS: TTL for Redis cache entries
        BASE_URL: Base URL for constructing short URLs
        MAX_URL_LENGTH: Maximum allowed length for original URLs
        STATS_SYNC_THRESHOLD: Number of clicks before syncing to PostgreSQL
        SHUTDOWN_TIMEOUT_SECONDS: Graceful shutdown timeout
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 100
    SHORT_ID_LENGTH: int = 7
    CACHE_TTL_SECONDS: int = 3600
    BASE_URL: str = "http://localhost:8000"
    MAX_URL_LENGTH: int = 2048
    STATS_SYNC_THRESHOLD: int = 10
    SHUTDOWN_TIMEOUT_SECONDS: int = 30
    
    # Optional: Redis password if needed
    REDIS_PASSWORD: Optional[str] = None


# Singleton settings instance
settings = Settings()