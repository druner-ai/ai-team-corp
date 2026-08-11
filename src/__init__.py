# Исправлено: добавлен __init__.py для src, чтобы Python распознавал src как пакет.
# Это решает ошибку ModuleNotFoundError: No module named 'src' в CI.
# Также добавлен pytest.ini с pythonpath = . для корректного импорта.
