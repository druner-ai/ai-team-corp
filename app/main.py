"""
Точка входа в приложение FastAPI для управления заметками.

Инициализирует приложение, настраивает CORS, подключает роутеры и запускает Uvicorn.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models import Note, NoteCreate, NoteUpdate
from app.storage import JSONStorage

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Инициализация хранилища
storage = JSONStorage("notes.json")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    При старте инициализирует файл хранилища, если он отсутствует.
    """
    logger.info("Запуск приложения, инициализация хранилища...")
    await storage.initialize()
    yield
    logger.info("Завершение работы приложения.")


app = FastAPI(
    title="Notes API",
    description="Простое REST API для управления заметками с файловым хранилищем.",
    version="1.0.0",
    lifespan=lifespan,
)

# Настройка CORS (разрешаем все источники для простоты, в production следует ограничить)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Обработчик ошибок валидации и бизнес-логики."""
    logger.warning(f"ValueError: {exc}")
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    """Обработчик ошибок отсутствия файла."""
    logger.error(f"FileNotFoundError: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера: файл данных не найден."})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Общий обработчик непредвиденных ошибок."""
    logger.exception(f"Непредвиденная ошибка: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера."})


@app.post("/notes", response_model=Note, status_code=201)
async def create_note(note_data: NoteCreate) -> Note:
    """
    Создание новой заметки.

    Args:
        note_data: Данные для создания заметки (title, content).

    Returns:
        Созданная заметка с присвоенным ID и временными метками.
    """
    logger.info(f"Создание заметки: {note_data.title}")
    note = await storage.create_note(note_data)
    return note


@app.get("/notes", response_model=list[Note])
async def get_all_notes() -> list[Note]:
    """
    Получение списка всех заметок.

    Returns:
        Массив заметок. Если заметок нет, возвращается пустой массив.
    """
    logger.info("Запрос всех заметок")
    notes = await storage.read_all()
    return notes


@app.get("/notes/{note_id}", response_model=Note)
async def get_note(note_id: int) -> Note:
    """
    Получение заметки по ID.

    Args:
        note_id: Уникальный идентификатор заметки.

    Returns:
        Найденная заметка.

    Raises:
        ValueError: Если заметка с указанным ID не найдена.
    """
    logger.info(f"Запрос заметки с ID={note_id}")
    note = await storage.get_note(note_id)
    if note is None:
        raise ValueError(f"Заметка с ID={note_id} не найдена")
    return note


@app.put("/notes/{note_id}", response_model=Note)
async def update_note(note_id: int, note_data: NoteUpdate) -> Note:
    """
    Обновление существующей заметки.

    Args:
        note_id: ID заметки для обновления.
        note_data: Новые данные (title, content).

    Returns:
        Обновленная заметка с актуальной меткой времени updated_at.

    Raises:
        ValueError: Если заметка с указанным ID не найдена.
    """
    logger.info(f"Обновление заметки с ID={note_id}")
    note = await storage.update_note(note_id, note_data)
    if note is None:
        raise ValueError(f"Заметка с ID={note_id} не найдена")
    return note


@app.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: int) -> None:
    """
    Удаление заметки по ID.

    Args:
        note_id: ID заметки для удаления.

    Raises:
        ValueError: Если заметка с указанным ID не найдена.
    """
    logger.info(f"Удаление заметки с ID={note_id}")
    success = await storage.delete_note(note_id)
    if not success:
        raise ValueError(f"Заметка с ID={note_id} не найдена")
    return None


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
