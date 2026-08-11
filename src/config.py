"""
Application configuration using Pydantic Settings.

Reads configuration from environment variables and .env file.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_path: str = Field(
        default="./urls.db",
        description="Path to SQLite database file",
    )
    base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for generating short URLs",
    )
    code_length: int = Field(
        default=6,
        ge=4,
        le=10,
        description="Length of generated short codes (4-10 characters)",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries for code generation on collision",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """
        Validate that base_url doesn't end with a trailing slash.

        Args:
            v: The base URL string.

        Returns:
            The validated base URL without trailing slash.
        """
        return v.rstrip("/")


settings = Settings()
