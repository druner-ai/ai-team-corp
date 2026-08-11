"""
Pydantic модели для валидации и сериализации данных заметок.

Определяет структуры для создания, обновления и представления заметок.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class NoteBase(BaseModel):
    """Базовая модель заметки с общими полями."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Заголовок заметки",
        examples=["Мой список дел"],
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Содержимое заметки",
        examples=["Купить молоко, хлеб, яйца"],
    )

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        """Проверка, что заголовок не состоит только из пробелов."""
        if not v.strip():
            raise ValueError("Заголовок не может быть пустым или состоять только из пробелов")
        return v.strip()

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v: str) -> str:
        """Проверка, что содержимое не состоит только из пробелов."""
        if not v.strip():
            raise ValueError("Содержимое не может быть пустым или состоять только из пробелов")
        return v.strip()


class NoteCreate(NoteBase):
    """Модель для создания новой заметки. Наследует все поля от NoteBase."""
    pass


class NoteUpdate(BaseModel):
    """
    Модель для обновления заметки.

    Все поля опциональны — можно обновить только заголовок или только содержимое.
    """

    title: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Новый заголовок заметки",
    )
    content: str | None = Field(
        None,
        min_length=1,
        description="Новое содержимое заметки",
    )

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty_if_provided(cls, v: str | None) -> str | None:
        """Если заголовок передан, он не должен быть пустым."""
        if v is not None and not v.strip():
            raise ValueError("Заголовок не может быть пустым или состоять только из пробелов")
        return v.strip() if v is not None else v

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty_if_provided(cls, v: str | None) -> str | None:
        """Если содержимое передано, оно не должно быть пустым."""
        if v is not None and not v.strip():
            raise ValueError("Содержимое не может быть пустым или состоять только из пробелов")
        return v.strip() if v is not None else v


class Note(NoteBase):
    """
    Полная модель заметки, возвращаемая API.

    Включает идентификатор и временные метки создания/обновления.
    """

    id: int = Field(..., description="Уникальный идентификатор заметки")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Дата и время создания заметки (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Дата и время последнего обновления заметки (UTC)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "title": "Первая заметка",
                    "content": "Текст первой заметки",
                    "created_at": "2023-10-25T12:00:00Z",
                    "updated_at": "2023-10-25T12:00:00Z",
                }
            ]
        }
    }
