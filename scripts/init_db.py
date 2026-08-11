"""Script to manually initialize the database."""

import asyncio
import aiosqlite


async def main() -> None:
    conn = await aiosqlite.connect("urls.db")
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA synchronous=NORMAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    with open("app/db/schema.sql") as f:
        schema = f.read()
    await conn.executescript(schema)
    await conn.commit()
    await conn.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
