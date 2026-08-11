import datetime
from sqlite3 import Connection
from typing import Optional


def insert_url(db: Connection, short_code: str, original_url: str) -> int:
    created_at = datetime.datetime.utcnow().isoformat()
    cursor = db.execute(
        "INSERT INTO urls (short_code, original_url, created_at) VALUES (?, ?, ?)",
        (short_code, original_url, created_at),
    )
    db.commit()
    return cursor.lastrowid


def get_url_by_code(db: Connection, short_code: str) -> Optional[dict]:
    row = db.execute(
        "SELECT * FROM urls WHERE short_code = ?", (short_code,)
    ).fetchone()
    return dict(row) if row else None


def increment_clicks(db: Connection, short_code: str):
    db.execute(
        "UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (short_code,)
    )
    db.commit()
