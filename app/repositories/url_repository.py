import aiosqlite
from datetime import datetime, timezone
from typing import Optional, Dict, Any


async def create_url(
    conn: aiosqlite.Connection, code: str, original_url: str
) -> Dict[str, Any]:
    """Insert a new short URL record and return it."""
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "INSERT INTO urls (code, original_url, created_at) VALUES (?, ?, ?)",
        (code, original_url, now),
    )
    await conn.commit()
    cursor = await conn.execute("SELECT * FROM urls WHERE code = ?", (code,))
    row = await cursor.fetchone()
    return dict(row) if row else {}


async def get_url_by_code(
    conn: aiosqlite.Connection, code: str
) -> Optional[Dict[str, Any]]:
    """Retrieve a URL record by its short code."""
    cursor = await conn.execute("SELECT * FROM urls WHERE code = ?", (code,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def increment_clicks(conn: aiosqlite.Connection, code: str) -> None:
    """Increment click count and update last_clicked_at for a given code."""
    now = datetime.now(timezone.utc).isoformat()
    await conn.execute(
        "UPDATE urls SET clicks = clicks + 1, last_clicked_at = ? WHERE code = ?",
        (now, code),
    )
    await conn.commit()


async def get_stats_by_code(
    conn: aiosqlite.Connection, code: str
) -> Optional[Dict[str, Any]]:
    """Get full statistics for a short URL."""
    cursor = await conn.execute("SELECT * FROM urls WHERE code = ?", (code,))
    row = await cursor.fetchone()
    return dict(row) if row else None
