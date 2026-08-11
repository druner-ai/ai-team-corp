import sqlite3
import secrets
import string
from app.schemas import URLInfo, URLStats


def generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_short_url(db: sqlite3.Connection, original_url: str) -> URLInfo:
    """Insert a new short URL and return its info."""
    while True:
        code = generate_short_code()
        try:
            db.execute(
                "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
                (code, original_url),
            )
            db.commit()
            break
        except sqlite3.IntegrityError:
            continue  # collision, try again

    return URLInfo(
        short_code=code,
        short_url=f"http://testserver/{code}",  # testserver is FastAPI's default
    )


def get_url_by_code(db: sqlite3.Connection, code: str) -> dict | None:
    row = db.execute(
        "SELECT original_url, clicks FROM urls WHERE short_code = ?", (code,)
    ).fetchone()
    return dict(row) if row else None


def increment_clicks(db: sqlite3.Connection, code: str) -> None:
    db.execute("UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (code,))
    db.commit()


def get_stats(db: sqlite3.Connection, code: str) -> URLStats | None:
    row = db.execute(
        "SELECT original_url, clicks, created_at FROM urls WHERE short_code = ?",
        (code,),
    ).fetchone()
    if row is None:
        return None
    return URLStats(
        url=row["original_url"],
        clicks=row["clicks"],
        created_at=row["created_at"],
    )
