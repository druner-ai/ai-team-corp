"""
Application configuration using Pydantic Settings.
All settings are loaded from environment variables with sensible defaults.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://shortener:shortener_pass@localhost:5432/shortener_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Application
    short_code_length: int = 6
    cache_ttl_seconds: int = 86400  # 24 hours
    base_url: str = "http://localhost:8000"

    # Rate Limiting
    rate_limit_shorten: str = "30/minute"
    rate_limit_default: str = "100/minute"

    # Security
    block_private_ips: bool = True
    allowed_origins: str = ""

    # Logging
    log_level: str = "INFO"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated origins into a list."""
        if not self.allowed_origins:
            return []
        return [origin.strip() for origin in self.allowed_origins.split(",")]


settings = Settings()