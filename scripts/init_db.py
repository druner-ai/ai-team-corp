"""
Manual database initialization script for development.

Creates the SQLite database and tables without starting the server.
Usage: python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config import settings
from src.repositories.database import close_db, init_db


async def main() -> None:
    """Initialize the database and print status."""
    print(f"Initializing database at: {settings.db_path}")
    await init_db(settings.db_path)
    print("Database initialized successfully.")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
