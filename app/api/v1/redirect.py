from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
import aiosqlite

from app.api.deps import get_db
from app.repositories.url_repository import get_url_by_code, increment_clicks

router = APIRouter()


@router.get(
    "/{code}",
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
)
async def redirect_to_original(
    code: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Redirect to the original URL and increment click count."""
    url_data = await get_url_by_code(db, code)
    if url_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found",
        )
    await increment_clicks(db, code)
    return RedirectResponse(
        url=url_data["original_url"],
        status_code=status.HTTP_302_FOUND,
    )
