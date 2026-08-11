"""Router for redirect endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.database import get_db
import sqlite3

router = APIRouter(tags=["redirect"])


@router.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    db: sqlite3.Connection = Depends(get_db)
):
    """Redirect to the original URL and record the click.
    
    Returns a 307 Temporary Redirect to the original URL.
    Records the click in the clicks table for statistics.
    """
    # Fetch URL record
    row = db.execute(
        "SELECT id, original_url FROM urls WHERE short_code = ?",
        (short_code,)
    ).fetchone()
    
    if row is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    
    # Record the click
    db.execute(
        "INSERT INTO clicks (url_id) VALUES (?)",
        (row["id"],)
    )
    db.commit()
    
    # Return 307 redirect
    return RedirectResponse(
        url=row["original_url"],
        status_code=307
    )
