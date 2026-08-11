from fastapi import FastAPI
from app.routers import urls, redirect, stats
from app.database import init_db

app = FastAPI()


@app.on_event("startup")
async def startup():
    await init_db()


app.include_router(urls.router)
app.include_router(redirect.router)
app.include_router(stats.router)
