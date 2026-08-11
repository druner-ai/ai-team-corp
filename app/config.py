"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_path: str = "./urls.db"
    base_url: str = "http://localhost:8000"
    short_code_length: int = 6
    max_url_length: int = 2048


settings = Settings()
