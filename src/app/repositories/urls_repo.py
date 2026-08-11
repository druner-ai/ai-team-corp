from typing import Optional

import aiosqlite


async def insert_url(
    conn: aiosqlite.Connection,
    code: str,
    original_url: str,
    created_at: str,
    expires_at: Optional[str] = None,
) -> int:
    """Insert a new URL mapping and return its id."""
    cursor = await conn.execute(
        "INSERT INTO urls (code, original_url, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (code, original_url, created_at, expires_at),
    )
    await conn.commit()
    return cursor.lastrowid


async def get_by_code(conn: aiosqlite.Connection, code: str) -> Optional[dict]:
    """Return a URL record by its short code."""
    cursor = await conn.execute(
        "SELECT id, code, original_url, created_at, expires_at FROM urls WHERE code = ?",
        (code,),
    )
    row = await cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "code": row[1],
            "original_url": row[2],
            "created_at": row[3],
            "expires_at": row[4],
        }
    return None


async def get_by_url(conn: aiosqlite.Connection, original_url: str) -> Optional[dict]:
    """Return the first matching URL record for the given original URL."""
    cursor = await conn.execute(
        "SELECT id, code, original_url, created_at, expires_at FROM urls WHERE original_url = ? LIMIT 1",
        (original_url,),
    )
    row = await cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "code": row[1],
            "original_url": row[2],
            "created_at": row[3],
            "expires_at": row[4],
        }
    return None
