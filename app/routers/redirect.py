from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.repositories.url_repository import URLRepository
from app.database import get_db

router = APIRouter()


async def get_url_repository(db=Depends(get_db)) -> URLRepository:
    return URLRepository(db)


@router.get("/{slug}")
async def redirect_to_url(slug: str, request: Request, repo: URLRepository = Depends(get_url_repository)):
    url = await repo.get_url_by_slug(slug)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    client_ip = request.client.host if request.client else None
    await repo.increment_visit(url["id"], client_ip)
    return RedirectResponse(url=url["original_url"], status_code=302)
