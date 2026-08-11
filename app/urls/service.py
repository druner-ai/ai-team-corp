import secrets
import string
from sqlite3 import Connection
from typing import Optional

from app.config import CODE_LENGTH
from app.urls.repository import insert_url, get_url_by_code, increment_clicks


def generate_short_code(length: int = CODE_LENGTH) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_short_url(db: Connection, original_url: str, base_url: str) -> dict:
    # Ensure base_url ends with exactly one slash for correct short_url construction
    clean_base = base_url.rstrip("/") + "/"
    for _ in range(5):
        code = generate_short_code()
        if not get_url_by_code(db, code):
            insert_url(db, code, original_url)
            return {
                "short_code": code,
                "short_url": f"{clean_base}{code}",
                "original_url": original_url,
            }
    raise RuntimeError("Could not generate unique short code")


def resolve_url(db: Connection, short_code: str) -> Optional[str]:
    url_data = get_url_by_code(db, short_code)
    if url_data:
        increment_clicks(db, short_code)
        return url_data["original_url"]
    return None


def get_stats(db: Connection, short_code: str) -> Optional[dict]:
    return get_url_by_code(db, short_code)
