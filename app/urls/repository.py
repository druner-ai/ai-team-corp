# FIX: Removed trailing slash enforcement on original_url and replaced deprecated utcnow() with timezone-aware call.
import sqlite3
import datetime
import random
import string
from app.database import get_db

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def create_short_url(db: sqlite3.Connection, original_url: str) -> dict:
    # Store the URL exactly as provided, no normalization.
    short_code = generate_short_code()
    created_at = datetime.datetime.now(datetime.UTC).isoformat()
    db.execute(
        "INSERT INTO urls (short_code, original_url, created_at) VALUES (?, ?, ?)",
        (short_code, original_url, created_at)
    )
    db.commit()
    return {
        "short_code": short_code,
        "original_url": original_url,
        "created_at": created_at
    }

def get_url_by_code(db: sqlite3.Connection, short_code: str) -> dict | None:
    row = db.execute(
        "SELECT short_code, original_url, clicks, created_at FROM urls WHERE short_code = ?",
        (short_code,)
    ).fetchone()
    if row is None:
        return None
    return {
        "short_code": row["short_code"],
        "original_url": row["original_url"],
        "clicks": row["clicks"],
        "created_at": row["created_at"]
    }

def increment_clicks(db: sqlite3.Connection, short_code: str):
    db.execute("UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (short_code,))
    db.commit()
