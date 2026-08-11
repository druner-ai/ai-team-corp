# Исправление: добавлен файл __init__.py, чтобы Python распознавал директорию app как пакет.
# Без этого файла импорт 'from app.main import app' в conftest.py вызывал ModuleNotFoundError.
