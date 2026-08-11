from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_PATH: str = "./urls.db"
    BASE_URL: str = "http://localhost:8000"
    CODE_LENGTH: int = 6
    MAX_CUSTOM_CODE_LENGTH: int = 16
    DB_JOURNAL_MODE: str = "WAL"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
