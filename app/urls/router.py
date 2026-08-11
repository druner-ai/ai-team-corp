from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
import sqlite3
from app.database import get_db
from app.urls import repository
from app.models import ShortenRequest, ShortenResponse, StatsResponse

router = APIRouter()

@router.post("/shorten", status_code=201, response_model=ShortenResponse)
def create_short_url(request: ShortenRequest, db: sqlite3.Connection = Depends(get_db)):
    result = repository.create_short_url(db, request.url)
    short_url = f"http://localhost:8000/{result['short_code']}"
    return ShortenResponse(
        short_code=result['short_code'],
        short_url=short_url,
        original_url=result['original_url']
    )

@router.get("/{short_code}")
def redirect_to_url(short_code: str, db: sqlite3.Connection = Depends(get_db)):
    url_data = repository.get_url_by_code(db, short_code)
    if url_data is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    repository.increment_clicks(db, short_code)
    return RedirectResponse(url=url_data["original_url"], status_code=302)

@router.get("/stats/{short_code}", response_model=StatsResponse)
def get_url_stats(short_code: str, db: sqlite3.Connection = Depends(get_db)):
    url_data = repository.get_url_by_code(db, short_code)
    if url_data is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    # clicks are already up-to-date at this point
    url_data = repository.get_url_by_code(db, short_code)
    return StatsResponse(
        short_code=url_data["short_code"],
        original_url=url_data["original_url"],
        clicks=url_data["clicks"],
        created_at=url_data["created_at"]
    )
