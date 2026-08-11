from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_path: str = "./data/urls.db"
    slug_length: int = 7
    max_recent_clicks: int = 50
    base_url: str = "http://localhost:8000"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
