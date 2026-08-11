"""
Router for DELETE /{id} endpoint.
Soft deletes a short URL.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.url_service import UrlService
from app.dependencies import get_url_service, get_db_session

router = APIRouter(tags=["delete"])


@router.delete(
    "/{short_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Short URL not found"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Delete short URL",
    description="Soft deletes a short URL. Subsequent redirects will return 404."
)
async def delete_short_url(
    short_id: str,
    url_service: UrlService = Depends(get_url_service),
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Delete (deactivate) a short URL.
    
    Args:
        short_id: Short identifier from URL path
        url_service: URL service instance
        db_session: Database session
        
    Returns:
        Response: Empty 204 No Content response
        
    Raises:
        HTTPException: 404 if short ID not found or already deleted
    """
    deleted = await url_service.delete_url(short_id, db_session)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found or already deleted"
        )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)