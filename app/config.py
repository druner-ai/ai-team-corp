"""
Application configuration using Pydantic Settings.

Reads configuration from environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        DATABASE_URL: SQLAlchemy database connection string.
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        APP_ENV: Application environment (development, production).
    """

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/tasks.db"
    LOG_LEVEL: str = "INFO"
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()