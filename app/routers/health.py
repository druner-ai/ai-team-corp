from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health-check для DevOps."""
    return {"status": "ok"}
