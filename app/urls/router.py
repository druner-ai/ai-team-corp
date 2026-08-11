from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlite3 import Connection

from app.database.connection import get_db
from app.urls.schemas import ShortenRequest, ShortenResponse, StatsResponse
from app.urls.service import create_short_url, resolve_url, get_stats

api_router = APIRouter()
redirect_router = APIRouter()


@api_router.post("/shorten", response_model=ShortenResponse, status_code=201)
def shorten_url(
    request: Request,
    payload: ShortenRequest,
    db: Connection = Depends(get_db),
):
    try:
        # pass the string representation of base_url; service will handle slash
        result = create_short_url(db, str(payload.url), str(request.base_url))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Could not generate unique code")
    return ShortenResponse(**result)


@api_router.get("/stats/{short_code}", response_model=StatsResponse)
def url_stats(short_code: str, db: Connection = Depends(get_db)):
    data = get_stats(db, short_code)
    if not data:
        raise HTTPException(status_code=404, detail="Short link not found")
    return StatsResponse(
        short_code=data["short_code"],
        original_url=data["original_url"],
        clicks=data["clicks"],
        created_at=data["created_at"],
    )


@redirect_router.get("/{short_code}")
def redirect_to_url(short_code: str, db: Connection = Depends(get_db)):
    original_url = resolve_url(db, short_code)
    if not original_url:
        raise HTTPException(status_code=404, detail="Short link not found")
    return RedirectResponse(url=original_url, status_code=302)
