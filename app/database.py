import aiosqlite
import asyncio
import logging
from app.config import DB_PATH

logger = logging.getLogger(__name__)


class DatabasePool:
    """A simple async connection pool for aiosqlite."""

    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self.pool = asyncio.Queue(maxsize=pool_size)
        self._connections = []

    async def _create_connection(self):
        conn = await aiosqlite.connect(self.db_path)
        if not conn:
            raise RuntimeError("Failed to create database connection")
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = aiosqlite.Row
        return conn

    async def init_pool(self):
        for _ in range(self.pool_size):
            conn = await self._create_connection()
            if not conn:
                raise RuntimeError("Failed to create connection for pool")
            self._connections.append(conn)
            await self.pool.put(conn)
        # Create tables using one connection
        async with self.acquire() as conn:
            if not conn:
                raise RuntimeError("Failed to acquire connection for table creation")
            await self._create_tables(conn)

    async def _create_tables(self, conn):
        try:
            await conn.executescript("""
                CREATE TABLE IF NOT EXISTS links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    original_url TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_id INTEGER NOT NULL,
                    clicked_at TEXT NOT NULL DEFAULT (datetime('now')),
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_links_slug ON links(slug);
                CREATE INDEX IF NOT EXISTS idx_clicks_link_id ON clicks(link_id);
                CREATE INDEX IF NOT EXISTS idx_clicks_clicked_at ON clicks(clicked_at);
            """)
            await conn.commit()
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise RuntimeError("Failed to create database tables") from e

    async def acquire(self):
        conn = await self.pool.get()
        if not conn:
            raise RuntimeError("Failed to acquire connection from pool")
        return _ConnectionContextManager(conn, self)

    async def release(self, conn):
        if conn:
            await self.pool.put(conn)
        else:
            logger.warning("Attempted to release null connection")

    async def close(self):
        while not self.pool.empty():
            conn = await self.pool.get()
            if conn:
                try:
                    await conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
        for conn in self._connections:
            if conn:
                try:
                    await conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")


class _ConnectionContextManager:
    def __init__(self, conn, pool: DatabasePool):
        self.conn = conn
        self.pool = pool

    async def __aenter__(self):
        if not self.conn:
            raise RuntimeError("Connection is null")
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        if self.conn:
            await self.pool.release(self.conn)
