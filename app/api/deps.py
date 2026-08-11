from fastapi import Request
import aiosqlite


async def get_db(request: Request) -> aiosqlite.Connection:
    """
    FastAPI dependency that returns the database connection
    stored in application state.
    """
    return request.app.state.db
