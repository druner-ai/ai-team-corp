from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.urls.router import router as url_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(url_router)
