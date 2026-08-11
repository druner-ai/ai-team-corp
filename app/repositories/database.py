"""
Database manager for SQLite connection handling and migrations.

Manages connection lifecycle, WAL mode, and schema initialization.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite database connections and schema.

    Handles initialization (WAL mode, table creation) and provides
    connection context managers for safe usage.
    """

    def __init__(self, database_path: str) -> None:
        """
        Initialize the database manager.

        Args:
            database_path: Path to the SQLite database file.
        """
        self._database_path = database_path

    async def init(self) -> None:
        """
        Initialize the database: create directory, enable WAL, create tables.

        This method is idempotent and safe to call multiple times.
        """
        # Ensure the directory exists
        db_dir = os.path.dirname(self._database_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        async with aiosqlite.connect(self._database_path) as db:
            # Enable WAL mode for better concurrent read performance
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            await db.execute("PRAGMA foreign_keys=OFF")  # As per architecture doc

            # Create tables
            await db.executescript(self._get_schema_sql())
            await db.commit()

        logger.info(f"Database initialized at {self._database_path}")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """
        Async context manager for database connections.

        Yields an aiosqlite.Connection with row_factory set to aiosqlite.Row.

        Yields:
            An aiosqlite.Connection instance.
        """
        async with aiosqlite.connect(self._database_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn

    @staticmethod
    def _get_schema_sql() -> str:
        """
        Return the DDL SQL for creating tables and indexes.

        Returns:
            SQL string with CREATE TABLE IF NOT EXISTS statements.
        """
        return """
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT NOT NULL UNIQUE,
            original_url TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT,
            expires_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INTEGER NOT NULL,
            clicked_at TEXT NOT NULL DEFAULT (datetime('now')),
            ip_address TEXT,
            user_agent TEXT,
            referer TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code);
        CREATE INDEX IF NOT EXISTS idx_urls_created_at ON urls(created_at);
        CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id);
        CREATE INDEX IF NOT EXISTS idx_clicks_clicked_at ON clicks(clicked_at);
        """
