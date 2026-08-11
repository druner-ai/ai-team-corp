"""Database connection management."""

import aiosqlite
from fastapi import Request

from app.config import settings

_db_conn: aiosqlite.Connection | None = None


async def init_db() -> None:
    """Initialize the database connection and apply schema."""
    global _db_conn
    _db_conn = await aiosqlite.connect(settings.database_path)
    _db_conn.row_factory = aiosqlite.Row
    await _db_conn.execute("PRAGMA journal_mode=WAL")
    await _db_conn.execute("PRAGMA synchronous=NORMAL")
    await _db_conn.execute("PRAGMA foreign_keys=ON")
    # Apply schema
    with open("app/db/schema.sql") as f:
        schema = f.read()
    await _db_conn.executescript(schema)
    await _db_conn.commit()


async def close_db() -> None:
    """Close the database connection."""
    global _db_conn
    if _db_conn is not None:
        await _db_conn.close()
        _db_conn = None


async def get_db() -> aiosqlite.Connection:
    """Dependency that provides the database connection."""
    if _db_conn is None:
        raise RuntimeError("Database not initialized")
    return _db_conn
