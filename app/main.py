import sqlite3
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database.connection import init_db
from app.routers import health, shorten, redirect, stats

DATABASE_PATH = os.getenv("DATABASE_PATH", "urls.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DATABASE_PATH)
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(health.router)
app.include_router(shorten.router)
app.include_router(redirect.router)
app.include_router(stats.router)
