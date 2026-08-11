"""
Database initialization and connection management.

Uses aiosqlite for async SQLite access. WAL mode is enabled for better
concurrent read performance.
"""

import logging
from pathlib import Path

import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)

_connection: aiosqlite.Connection | None = None


async def get_connection() -> aiosqlite.Connection:
    """
    Return the global database connection.

    Raises:
        RuntimeError: If the database has not been initialized.
    """
    if _connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _connection


async def init_db() -> None:
    """
    Initialize the database: create tables, indexes, and enable WAL mode.

    This function is idempotent and safe to call multiple times.
    """
    global _connection

    db_path = Path(settings.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _connection = await aiosqlite.connect(str(db_path))
    _connection.row_factory = aiosqlite.Row

    # Enable WAL mode for better concurrent read performance
    await _connection.execute("PRAGMA journal_mode=WAL;")

    # Enable foreign keys (SQLite disables them by default)
    await _connection.execute("PRAGMA foreign_keys=ON;")

    # Create tables
    await _connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            original_url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            clicks INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INTEGER NOT NULL,
            clicked_at TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (url_id) REFERENCES urls(id)
        );

        CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id);
        """
    )
    await _connection.commit()
    logger.info("Database initialized successfully at %s", db_path)


async def close_db() -> None:
    """Close the database connection gracefully."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        logger.info("Database connection closed.")
