"""
Database initialization and connection pool.
Uses aiosqlite with a simple async connection pool.
"""
import asyncio
import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)


async def init_db(conn: aiosqlite.Connection) -> None:
    """
    Initialize database: enable WAL mode and run DDL.
    """
    await conn.execute("PRAGMA journal_mode=WAL")
    # Read and execute init.sql
    sql_path = Path(__file__).parent.parent / "sql" / "init.sql"
    if not sql_path.exists():
        logger.warning("init.sql not found at %s", sql_path)
        return
    with open(sql_path, "r", encoding="utf-8") as f:
        ddl = f.read()
    await conn.executescript(ddl)
    await conn.commit()


class DatabasePool:
    """
    Simple async connection pool for aiosqlite.
    Maintains a fixed number of connections and provides acquire/release.
    """

    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue(maxsize=pool_size)
        self._connections: list[aiosqlite.Connection] = []

    async def initialize(self) -> None:
        """Create initial connections and put them into the pool."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(self.db_path)
            # Enable WAL mode on each connection (persistent setting, but safe)
            await conn.execute("PRAGMA journal_mode=WAL")
            # Enable foreign keys (optional, we don't use FK but good practice)
            await conn.execute("PRAGMA foreign_keys=ON")
            self._connections.append(conn)
            await self._pool.put(conn)

    async def acquire(self) -> aiosqlite.Connection:
        """Acquire a connection from the pool."""
        return await self._pool.get()

    async def release(self, conn: aiosqlite.Connection) -> None:
        """Return a connection to the pool."""
        await self._pool.put(conn)

    async def close(self) -> None:
        """Close all connections."""
        while not self._pool.empty():
            conn = await self._pool.get()
            await conn.close()
        # Also close any connections that might not be in the pool (shouldn't happen)
        for conn in self._connections:
            try:
                await conn.close()
            except Exception:
                pass
