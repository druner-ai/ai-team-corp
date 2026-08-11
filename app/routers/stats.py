from fastapi import APIRouter, Depends, HTTPException
from app.schemas import StatsResponse
from app.services.link_service import LinkService
from app.dependencies import get_link_service

router = APIRouter()


@router.get("/stats/{slug}", response_model=StatsResponse)
async def get_stats(slug: str, service: LinkService = Depends(get_link_service)):
    stats = await service.get_stats(slug)
    if not stats:
        raise HTTPException(status_code=404, detail="Short link not found")
    return stats
