from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_path: str = "data/shortener.db"
    base_url: str = "http://localhost:8000"
    short_code_length: int = 6
    allowed_origins: str = ""  # comma-separated
    rate_limit_per_minute: int = 60
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
