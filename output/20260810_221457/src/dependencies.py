"""
    Dependency injection container; re-exports commonly used dependencies.
"""
from src.db.postgres import get_db
from src.db.redis import get_redis