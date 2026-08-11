from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import init_db
from app.routers import health, shorten, stats, redirect

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(health.router)
app.include_router(stats.router)
app.include_router(shorten.router)
app.include_router(redirect.router)
