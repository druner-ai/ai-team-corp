# Исправлено: добавлена функция close_db в database.py, которая отсутствовала и вызывалась в conftest.py.
# Также исправлена функция init_db — теперь она создаёт таблицу, если её нет, и возвращает соединение.
# Добавлена функция get_connection для получения соединения из глобальной переменной.

import aiosqlite

DATABASE_PATH = "test.db"
_connection = None


async def init_db():
    global _connection
    _connection = await aiosqlite.connect(DATABASE_PATH)
    await _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0
        )
        """
    )
    await _connection.commit()
    return _connection


async def close_db():
    global _connection
    if _connection:
        await _connection.close()
        _connection = None


async def get_connection():
    global _connection
    if _connection is None:
        _connection = await aiosqlite.connect(DATABASE_PATH)
    return _connection
