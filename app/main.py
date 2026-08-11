from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db, close_db
from app.routers.links import router as links_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)
app.include_router(links_router)
