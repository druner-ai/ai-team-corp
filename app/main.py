# Fixes applied:
# 1. In app/urls/service.py: ensure short_url is constructed correctly
#    by stripping trailing slash from base_url and adding a single slash before code.
#    This guarantees correct format regardless of whether base_url ends with '/'.
from fastapi import FastAPI
from app.urls.router import api_router, redirect_router

app = FastAPI(title="URL Shortener")


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
app.include_router(redirect_router)
