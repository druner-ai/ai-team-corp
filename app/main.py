import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import DB_PATH, CORS_ORIGINS, LOG_LEVEL, CACHE_TTL
from app.database import DatabasePool
from app.cache import TTLCache
from app.dependencies import _db_pool, _cache, _rate_limiter
from app.routers import links, redirect, stats
from app.utils import mask_ip

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global _db_pool, _cache
    try:
        _db_pool = DatabasePool(DB_PATH)
        await _db_pool.init_pool()
        _cache = TTLCache(ttl=CACHE_TTL)
        logger.info("Application started")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise RuntimeError("Application startup failed") from e
    yield
    # Shutdown
    try:
        await _db_pool.close()
        logger.info("Application shut down")
    except Exception as e:
        logger.error(f"Failed to shut down application: {e}")


app = FastAPI(title="URL Shortener", lifespan=lifespan)

# CORS
if CORS_ORIGINS:
    origins = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Middleware for logging with masked IP
@app.middleware("http")
async def log_requests(request: Request, call_next):
    client_ip = request.client.host
    masked_ip = mask_ip(client_ip)
    logger.info(f"Request: {request.method} {request.url.path} from {masked_ip}")
    response = await call_next(request)
    return response


# Include routers
app.include_router(links.router)
app.include_router(redirect.router)
app.include_router(stats.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
