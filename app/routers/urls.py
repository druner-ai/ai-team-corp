from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db
from app.schemas.url import CreateUrlRequest, UrlResponse
from app.services.url_service import (
    UrlService,
    InvalidURLException,
    SlugAlreadyExistsException,
    MaxCollisionRetriesExceeded,
)
from app.repositories.url_repository import UrlRepository
from app.config import settings

router = APIRouter()


@router.post("/urls", response_model=UrlResponse, status_code=201)
async def create_url(req: CreateUrlRequest, conn=Depends(get_db)):
    """Create a new short URL, optionally with a custom slug."""
    svc = UrlService(UrlRepository())
    try:
        url_data = await svc.create_url(conn, req.original_url, req.custom_slug)
    except InvalidURLException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SlugAlreadyExistsException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except MaxCollisionRetriesExceeded:
        raise HTTPException(status_code=500, detail="Internal error generating slug")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error")

    short_url = f"{settings.base_url}/r/{url_data['slug']}"
    return UrlResponse(
        slug=url_data["slug"],
        short_url=short_url,
        original_url=url_data["original_url"],
        created_at=url_data["created_at"],
    )


@router.delete("/urls/{slug}", status_code=204)
async def delete_url(slug: str, conn=Depends(get_db)):
    """Soft-delete (deactivate) a URL by its slug."""
    svc = UrlService(UrlRepository())
    deactivated = await svc.deactivate_url(conn, slug)
    if not deactivated:
        raise HTTPException(status_code=404, detail="Slug not found")
    return None
