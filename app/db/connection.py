import aiosqlite
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


async def init_db() -> aiosqlite.Connection:
    """
    Initialize the database: create connection, enable WAL mode,
    and execute schema DDL. Returns the connection object.
    """
    db_path = settings.db_path
    # Ensure directory exists for file-based databases
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")

    # Load and execute schema
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    await conn.executescript(schema_sql)
    await conn.commit()

    logger.info("Database initialized successfully")
    return conn


async def close_db(conn: aiosqlite.Connection):
    """Close the database connection."""
    await conn.close()
    logger.info("Database connection closed")
