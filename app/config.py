import os

DB_PATH = os.getenv("DB_PATH", "./links.db")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
