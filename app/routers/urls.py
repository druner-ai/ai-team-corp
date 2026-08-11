from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.url_service import URLService

router = APIRouter()


class URLCreateRequest(BaseModel):
    original_url: HttpUrl
    custom_slug: str | None = Field(None, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')


class URLResponse(BaseModel):
    slug: str
    original_url: str
    short_url: str
    created_at: str


@router.post("/urls", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
async def create_url(
    request: URLCreateRequest,
    session: AsyncSession = Depends(get_session),
    svc: URLService = Depends(URLService),
):
    """Создаёт короткую ссылку."""
    try:
        result = await svc.create_url(
            session,
            original_url=str(request.original_url),
            custom_slug=request.custom_slug,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/urls/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    slug: str,
    session: AsyncSession = Depends(get_session),
    svc: URLService = Depends(URLService),
):
    """Деактивирует короткую ссылку."""
    deactivated = await svc.deactivate_url(session, slug)
    if not deactivated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
