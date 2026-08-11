"""Database repository with raw SQL queries."""

import aiosqlite


async def insert_url(db: aiosqlite.Connection, original_url: str) -> int:
    """Insert a new URL and return its ID."""
    cursor = await db.execute(
        "INSERT INTO urls (original_url) VALUES (?)", (original_url,)
    )
    await db.commit()
    return cursor.lastrowid


async def get_url_by_code(db: aiosqlite.Connection, short_code: str) -> aiosqlite.Row | None:
    """Retrieve a URL row by short code."""
    cursor = await db.execute(
        "SELECT * FROM urls WHERE short_code = ?", (short_code,)
    )
    return await cursor.fetchone()


async def increment_clicks(db: aiosqlite.Connection, short_code: str) -> None:
    """Atomically increment clicks and update last_visited_at."""
    await db.execute(
        "UPDATE urls SET clicks = clicks + 1, last_visited_at = datetime('now') WHERE short_code = ?",
        (short_code,),
    )
    await db.commit()


async def get_stats_by_code(db: aiosqlite.Connection, short_code: str) -> aiosqlite.Row | None:
    """Retrieve statistics for a short code."""
    cursor = await db.execute(
        "SELECT short_code, original_url, clicks, created_at, last_visited_at FROM urls WHERE short_code = ?",
        (short_code,),
    )
    return await cursor.fetchone()
