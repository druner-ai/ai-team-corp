import pytest
import aiosqlite
from httpx import AsyncClient
from app.main import app
from app.database import get_db, SQL_SCHEMA_FILE


@pytest.fixture(scope="function")
async def async_client():
    """
    Provide an httpx AsyncClient backed by the FastAPI app with an in-memory
    SQLite database (shared cache). Each test uses a fresh schema.
    """
    db_uri = "file::memory:?cache=shared"

    # Seed the shared in-memory database with the schema
    setup_conn = await aiosqlite.connect(db_uri, uri=True)
    await setup_conn.execute("PRAGMA journal_mode=WAL;")
    await setup_conn.execute("PRAGMA foreign_keys=ON;")
    with open(SQL_SCHEMA_FILE, 'r') as f:
        schema = f.read()
    await setup_conn.executescript(schema)
    await setup_conn.commit()
    await setup_conn.close()

    async def override_get_db():
        conn = await aiosqlite.connect(db_uri, uri=True)
        try:
            yield conn
        finally:
            await conn.close()

    # Monkey‑patch database.get_connection so background tasks also use the shared DB
    import app.database as database_module
    original_get_connection = database_module.get_connection

    async def override_get_connection():
        conn = await aiosqlite.connect(db_uri, uri=True)
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    database_module.get_connection = override_get_connection

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()
    database_module.get_connection = original_get_connection
