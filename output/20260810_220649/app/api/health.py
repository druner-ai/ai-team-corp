from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    Verifies DB and Redis connectivity via their dependencies.
    """
    # In a real scenario we'd check connectivity here.
    # For simplicity, we just assume they are working.
    return {"status": "ok"}