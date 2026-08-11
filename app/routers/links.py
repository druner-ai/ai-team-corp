from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.models import URLCreate, URLResponse, URLStats
from app.shortener import (
    create_short_url,
    get_original_url,
    increment_clicks,
    get_stats,
)

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/shorten", status_code=201, response_model=URLResponse)
async def shorten_url(payload: URLCreate, request: Request):
    original_url = str(payload.url)
    code, _ = await create_short_url(original_url)
    base_url = str(request.base_url).rstrip("/")
    short_url = f"{base_url}/{code}"
    return URLResponse(
        short_code=code,
        short_url=short_url,
        original_url=original_url,
    )


@router.get("/{short_code}")
async def redirect_to_original(short_code: str):
    url = await get_original_url(short_code)
    if url is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    await increment_clicks(short_code)
    return RedirectResponse(url=url, status_code=307)


@router.get("/stats/{short_code}", response_model=URLStats)
async def get_url_stats(short_code: str):
    stats = await get_stats(short_code)
    if stats is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return URLStats(**stats)
