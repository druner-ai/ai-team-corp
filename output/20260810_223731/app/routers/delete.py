"""
Router for DELETE /{id} – soft-delete a short URL.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.delete_service import soft_delete

router = APIRouter()
logger = logging.getLogger(__name__)


@router.delete("/{short_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_short_url(
    short_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft-delete a short URL. It will no longer be available for redirection.
    """
    deleted = await soft_delete(db_session, short_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return None  # FastAPI will return 204