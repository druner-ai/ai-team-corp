import aiosqlite
from pathlib import Path
from typing import AsyncGenerator
from app.config import settings

SQL_SCHEMA_FILE = Path(__file__).parent.parent / "migrations" / "001_init.sql"


async def get_connection() -> aiosqlite.Connection:
    """Create a new async connection to SQLite and enable WAL mode."""
    conn = await aiosqlite.connect(settings.database_path)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA foreign_keys=ON;")
    return conn


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """FastAPI dependency that provides a database connection per request."""
    conn = await get_connection()
    try:
        yield conn
    finally:
        await conn.close()


async def init_db() -> None:
    """Initialize database schema if tables do not exist."""
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = await get_connection()
    try:
        with open(SQL_SCHEMA_FILE, 'r') as f:
            schema_sql = f.read()
        await conn.executescript(schema_sql)
    finally:
        await conn.close()
