from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from app.database import get_db
from app.urls.schemas import URLCreate, URLResponse, StatsResponse
from app.urls.service import create_short_url, delete_short_url, get_redirect_url, get_stats

router = APIRouter()


@router.post("/api/shorten", response_model=URLResponse, status_code=201)
def shorten_url(payload: URLCreate, request: Request, db=Depends(get_db)):
    try:
        return create_short_url(db, payload.url, payload.custom_code, payload.expires_at, request)
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise


@router.delete("/api/shorten/{short_code}", status_code=204)
def delete_url(short_code: str, db=Depends(get_db)):
    if not delete_short_url(db, short_code):
        raise HTTPException(status_code=404, detail="Short code not found")


@router.get("/api/stats/{short_code}", response_model=StatsResponse)
def get_url_stats(short_code: str, db=Depends(get_db)):
    stats = get_stats(db, short_code)
    if stats is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    return stats


@router.get("/{short_code}")
def redirect_to_url(short_code: str, request: Request, db=Depends(get_db)):
    result = get_redirect_url(db, short_code, request)
    if result is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    if result == "expired":
        raise HTTPException(status_code=410, detail="Link expired")
    return RedirectResponse(url=result, status_code=302)
