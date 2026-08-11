"""
Database connection management and initialization.

Handles SQLite database setup with WAL mode, connection lifecycle,
and provides a FastAPI dependency for injecting database connections.
"""

import logging
from typing import AsyncGenerator

import aiosqlite

logger = logging.getLogger(__name__)

# Module-level connection reference (managed by lifespan)
_connection: aiosqlite.Connection | None = None


async def init_db(db_path: str) -> None:
    """
    Initialize the database connection and create tables.

    Enables WAL journal mode for better concurrent read performance
    and creates the urls table if it doesn't exist.

    Args:
        db_path: Path to the SQLite database file.

    Raises:
        RuntimeError: If database initialization fails.
    """
    global _connection

    try:
        _connection = await aiosqlite.connect(db_path)
        _connection.row_factory = aiosqlite.Row

        # Enable WAL mode for better concurrent read performance
        await _connection.execute("PRAGMA journal_mode=WAL")
        await _connection.execute("PRAGMA foreign_keys=ON")

        # Create the urls table if it doesn't exist
        await _connection.execute(
            """
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT NOT NULL UNIQUE,
                original_url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                clicks INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        # Create unique index on short_code for fast lookups
        await _connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code)"
        )

        await _connection.commit()
        logger.info("Database initialized at %s", db_path)
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise RuntimeError(f"Database initialization failed: {e}") from e


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    FastAPI dependency that yields the database connection.

    This is a generator function that yields the connection for use
    in request handlers. The connection is managed by the application
    lifespan and should not be closed here.

    Yields:
        The active aiosqlite database connection.

    Raises:
        RuntimeError: If the database has not been initialized.
    """
    if _connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    yield _connection


async def close_db() -> None:
    """
    Close the database connection gracefully.

    Should be called during application shutdown.
    """
    global _connection
    if _connection is not None:
        try:
            await _connection.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error("Error closing database connection: %s", e)
        finally:
            _connection = None
