"""
    Application settings using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    BASE_URL: str = "https://sho.rt"
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 100
    CACHE_TTL_SECONDS: int = 3600
    SHUTDOWN_TIMEOUT_SECONDS: int = 30
    LOG_LEVEL: str = "INFO"

    BLOCKED_HOSTS: str = "localhost,127.0.0.1,10.,192.168."

    @property
    def blocked_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.BLOCKED_HOSTS.split(",") if h.strip()]

settings = Settings()