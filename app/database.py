import asyncio
import logging
import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages a single aiosqlite connection with WAL mode and table creation.
    All database operations are serialized through an asyncio Lock.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Create connection, enable WAL mode, and create tables if not exist."""
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT NOT NULL UNIQUE,
                original_url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                clicks INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_links_short_code ON links(short_code)"
        )
        await self._conn.commit()
        logger.info("Database initialized successfully")

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

    async def execute(self, sql: str, params: tuple | None = None) -> aiosqlite.Cursor:
        """Execute a single SQL statement (with lock)."""
        async with self._lock:
            if not self._conn:
                raise RuntimeError("Database connection is not initialized")
            cursor = await self._conn.execute(sql, params or ())
            await self._conn.commit()
            return cursor

    async def fetchone(self, sql: str, params: tuple | None = None) -> dict | None:
        """Fetch a single row and return as dict (with lock)."""
        async with self._lock:
            if not self._conn:
                raise RuntimeError("Database connection is not initialized")
            cursor = await self._conn.execute(sql, params or ())
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple | None = None) -> list[dict]:
        """Fetch all rows and return as list of dicts (with lock)."""
        async with self._lock:
            if not self._conn:
                raise RuntimeError("Database connection is not initialized")
            cursor = await self._conn.execute(sql, params or ())
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
