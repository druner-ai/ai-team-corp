from fastapi import APIRouter, Depends, HTTPException
from app.repositories.url_repository import URLRepository
from app.schemas.url import StatsResponse
from app.database import get_db

router = APIRouter()


async def get_url_repository(db=Depends(get_db)) -> URLRepository:
    return URLRepository(db)


@router.get("/stats/{slug}", response_model=StatsResponse)
async def get_stats(slug: str, repo: URLRepository = Depends(get_url_repository)):
    stats = await repo.get_stats(slug)
    if not stats:
        raise HTTPException(status_code=404, detail="URL not found")
    return stats
