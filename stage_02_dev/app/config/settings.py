from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Banking Requisites Validator"
    debug: bool = False

settings = Settings()
