"""
Application configuration.

Uses a simple class-based configuration. Could be replaced with pydantic-settings
for environment variable support in the future.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings."""

    DATABASE_PATH: str = "shortener.db"
    BASE_URL: str = "http://localhost:8000"
    CODE_LENGTH: int = 6
    MAX_URL_LENGTH: int = 2048
    MAX_CODE_GENERATION_ATTEMPTS: int = 5


settings = Settings()
