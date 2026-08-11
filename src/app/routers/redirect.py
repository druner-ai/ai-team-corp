from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
import aiosqlite

from ..database import get_db
from ..repositories import urls_repo, clicks_repo

router = APIRouter()


@router.get("/{code}", status_code=302)
async def redirect_to_url(
    code: str,
    request: Request,
    conn: aiosqlite.Connection = Depends(get_db),
):
    url = await urls_repo.get_by_code(conn, code)
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Check if the link has expired
    expires = url.get("expires_at")
    if expires:
        try:
            if datetime.fromisoformat(expires) < datetime.now(timezone.utc):
                raise HTTPException(status_code=410, detail="Short URL has expired")
        except ValueError:
            # If expires_at is malformed, treat as expired
            raise HTTPException(status_code=410, detail="Short URL has expired")

    # Log the click
    await clicks_repo.insert_click(
        conn,
        url_id=url["id"],
        clicked_at=datetime.now(timezone.utc).isoformat(),
        referer=request.headers.get("Referer"),
        user_agent=request.headers.get("User-Agent"),
        ip=request.client.host if request.client else None,
    )

    return RedirectResponse(url=url["original_url"], status_code=302)
