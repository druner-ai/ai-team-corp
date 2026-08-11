"""
Manual database initialization script for DevOps.

Creates the SQLite database and tables without starting the application.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.repositories.database import DatabaseManager


async def main():
    """Initialize the database."""
    print(f"Initializing database at: {settings.database_path}")
    db_manager = DatabaseManager(settings.database_path)
    await db_manager.init()
    print("Database initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
