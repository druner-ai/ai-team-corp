from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.urls.router import router as urls_router
from app.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(health_router, tags=["health"])
app.include_router(urls_router, tags=["urls"])
