# FIX: Added proper database module with init_db and connection management for SQLite.
# This resolves ModuleNotFoundError by providing the app package structure required by tests.
import os
import aiosqlite

DATABASE_URL = os.getenv("DATABASE_URL", "shortener.db")

_db_connection = None


async def get_connection() -> aiosqlite.Connection:
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(DATABASE_URL)
        _db_connection.row_factory = aiosqlite.Row
        await _db_connection.execute("PRAGMA journal_mode=WAL")
    return _db_connection


async def init_db():
    conn = await get_connection()
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS urls (
            short_code TEXT PRIMARY KEY,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0
        )
        """
    )
    await conn.commit()


async def close_db():
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
