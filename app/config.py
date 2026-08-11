from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_path: str = "shortener.db"
    base_url: str = "http://localhost:8000"
    short_code_length: int = 6
    max_url_length: int = 2048
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
