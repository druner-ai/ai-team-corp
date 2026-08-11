"""
Application configuration using Pydantic Settings.

Reads configuration from environment variables and .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_path: str = "./data/shortener.db"
    base_url: str = "http://localhost:8000"
    cache_ttl_seconds: int = 300
    short_code_length: int = 6
    allowed_origins: str = ""
    log_level: str = "INFO"


settings = Settings()
