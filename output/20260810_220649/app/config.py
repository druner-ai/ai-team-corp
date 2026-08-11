"""
Application configuration via pydantic-settings.
Reads environment variables with .env support.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    redis_url: str = "redis://localhost:6379/0"
    base_url: str = "https://short.example.com"
    rate_limit_per_minute: int = 100
    cache_ttl_seconds: int = 3600
    short_id_length: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()