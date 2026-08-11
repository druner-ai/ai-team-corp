"""
Router for URL statistics.
"""

from fastapi import APIRouter, HTTPException, status

from app.database.connection import get_connection
from app.schemas import URLStatsResponse

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats/{short_code}", response_model=URLStatsResponse)
def get_url_stats(short_code: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT short_code, original_url, access_count, created_at FROM urls WHERE short_code = ?",
        (short_code,),
    ).fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    conn.close()
    return URLStatsResponse(
        short_code=row["short_code"],
        original_url=row["original_url"],
        access_count=row["access_count"],
        created_at=row["created_at"],
    )
