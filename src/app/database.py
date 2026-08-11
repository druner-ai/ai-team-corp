import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from .config import settings


class ConnectionPool:
    """Simple async connection pool for aiosqlite."""
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self.pool: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue(maxsize=pool_size)
        self._initialized = False

    async def initialize(self) -> None:
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(self.db_path)
            await conn.execute("PRAGMA journal_mode=WAL;")
            await conn.execute("PRAGMA foreign_keys=ON;")
            self.pool.put_nowait(conn)
        self._initialized = True

    async def acquire(self) -> aiosqlite.Connection:
        if not self._initialized:
            raise RuntimeError("Pool not initialized")
        return await self.pool.get()

    async def release(self, conn: aiosqlite.Connection) -> None:
        await self.pool.put(conn)

    async def close(self) -> None:
        while not self.pool.empty():
            conn = await self.pool.get()
            await conn.close()
        self._initialized = False


pool: ConnectionPool | None = None


async def init_db() -> None:
    """Initialize the database pool and create tables."""
    global pool
    pool = ConnectionPool(settings.DATABASE_PATH, pool_size=3)
    await pool.initialize()
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn = await pool.acquire()
    try:
        await conn.executescript(schema_sql)
        await conn.commit()
    finally:
        await pool.release(conn)


async def close_db() -> None:
    global pool
    if pool:
        await pool.close()
        pool = None


async def get_db() -> aiosqlite.Connection:
    """Dependency that provides a database connection from the pool."""
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        await pool.release(conn)
