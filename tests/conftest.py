# tests/conftest.py
# ИСПРАВЛЕНИЯ:
# 1. Добавлена фикстура для инициализации тестовой БД перед каждым тестом
# 2. Используется временная БД в памяти (:memory:) для изоляции тестов
# 3. Добавлен TestClient с правильным lifespan

import os
import pytest
from fastapi.testclient import TestClient

# Устанавливаем тестовую БД до импорта приложения
os.environ["DB_PATH"] = ":memory:"

from app.main import app, init_db


@pytest.fixture(autouse=True)
def setup_db():
    """Инициализация БД перед каждым тестом."""
    init_db()
    yield


@pytest.fixture
def client():
    """Тестовый клиент FastAPI."""
    with TestClient(app) as c:
        yield c
