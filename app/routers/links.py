"""Router for link creation and statistics endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from app.schemas import UrlCreateRequest, UrlCreateResponse, UrlStatsResponse
from app.services import encode_base62
from app.database import get_db
import sqlite3

router = APIRouter(tags=["links"])


@router.post("/links/shorten", status_code=201, response_model=UrlCreateResponse)
async def create_short_url(
    request: UrlCreateRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """Create a shortened URL.
    
    Inserts the original URL, generates a short code from the row ID,
    and updates the record with the generated code.
    """
    original_url = str(request.original_url)
    
    # Insert with a temporary placeholder short_code
    cursor = db.execute(
        "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
        ("__temp__", original_url)
    )
    db.commit()
    
    # Get the generated ID
    url_id = cursor.lastrowid
    
    # Generate short code from ID
    short_code = encode_base62(url_id)
    
    # Update the record with the real short_code
    db.execute(
        "UPDATE urls SET short_code = ? WHERE id = ?",
        (short_code, url_id)
    )
    db.commit()
    
    # Build short URL (using localhost:8000 as base)
    short_url = f"http://localhost:8000/{short_code}"
    
    return UrlCreateResponse(
        short_code=short_code,
        original_url=original_url,
        short_url=short_url
    )


@router.get("/links/{short_code}/stats", response_model=UrlStatsResponse)
async def get_link_stats(
    short_code: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """Get statistics for a shortened URL.
    
    Returns the original URL, creation date, and total click count.
    """
    # Fetch URL record
    row = db.execute(
        "SELECT id, short_code, original_url, created_at FROM urls WHERE short_code = ?",
        (short_code,)
    ).fetchone()
    
    if row is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    
    # Count clicks
    clicks_row = db.execute(
        "SELECT COUNT(*) as count FROM clicks WHERE url_id = ?",
        (row["id"],)
    ).fetchone()
    
    clicks_count = clicks_row["count"] if clicks_row else 0
    
    return UrlStatsResponse(
        short_code=row["short_code"],
        original_url=row["original_url"],
        created_at=str(row["created_at"]),
        clicks_count=clicks_count
    )
