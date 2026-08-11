"""
Router for URL redirection.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse

from app.database.connection import get_connection

router = APIRouter(tags=["redirect"])


@router.get("/{short_code}")
def redirect_to_original(short_code: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT original_url FROM urls WHERE short_code = ?", (short_code,)
    ).fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    original_url = row["original_url"]
    conn.execute(
        "UPDATE urls SET access_count = access_count + 1 WHERE short_code = ?",
        (short_code,),
    )
    conn.commit()
    conn.close()

    return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)
