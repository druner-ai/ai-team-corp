import os

DB_PATH = os.getenv("DB_PATH", "urls.db")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
CODE_LENGTH = int(os.getenv("CODE_LENGTH", "6"))
