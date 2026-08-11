"""
Application configuration using pydantic-settings.
Reads from environment variables and .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = "http://localhost:8000"
    db_path: str = "./data/urls.db"
    code_length: int = 6
    db_pool_size: int = 5


settings = Settings()
