from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""
    base_url: str = "http://localhost:8000"
    db_path: str = "urls.db"
    code_length: int = 6

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
