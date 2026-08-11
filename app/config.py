# Исправлено: обновлён класс Settings для использования ConfigDict вместо устаревшего class-based Config
# Это устраняет предупреждение PydanticDeprecatedSince20 из логов CI

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite+aiosqlite:///./urls.db"
    base_url: str = "http://localhost:8000"
    slug_length: int = 7


settings = Settings()
