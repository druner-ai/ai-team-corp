from contextlib import asynccontextmanager
from fastapi import FastAPI
import aiosqlite
from app.database import DATABASE_URL
from app.models import CREATE_TABLE_URLS, CREATE_TABLE_CLICKS
from app.routers import shorten, redirect, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database connection and tables
    db = await aiosqlite.connect(DATABASE_URL)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute(CREATE_TABLE_URLS)
    await db.execute(CREATE_TABLE_CLICKS)
    await db.commit()
    app.state.db = db
    yield
    # Shutdown: close database
    await db.close()


app = FastAPI(lifespan=lifespan)

app.include_router(shorten.router)
app.include_router(redirect.router)
app.include_router(stats.router)
