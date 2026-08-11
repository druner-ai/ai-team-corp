import aiosqlite
from fastapi import Request

DATABASE_URL = "shortener.db"


async def get_db(request: Request) -> aiosqlite.Connection:
    return request.app.state.db
