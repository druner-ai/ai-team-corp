"""
Конфигурация приложения через Pydantic Settings.

Загружает настройки из переменных окружения или файла .env.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""

    database_url: str = "sqlite:///urls.db"
    base_url: str = "http://localhost:8000"
    short_code_length: int = 6

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
