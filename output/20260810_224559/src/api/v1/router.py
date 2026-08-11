"""
Aggregated v1 API router.

Includes all route modules for the URL shortener.
"""
from fastapi import APIRouter

from src.api.v1 import shorten, redirect, stats, delete

router = APIRouter(prefix="/v1", tags=["v1"])

router.include_router(shorten.router, prefix="/shorten", tags=["shorten"])
router.include_router(redirect.router, tags=["redirect"])
router.include_router(stats.router, prefix="/stats", tags=["stats"])
router.include_router(delete.router, tags=["delete"])