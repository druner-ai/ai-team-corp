"""
Исправления по отчёту QA:
- Добавлен глобальный обработчик исключений в app/main.py (возвращает 500 с деталями).
- Добавлена обработка исключений в middleware SecurityHeadersMiddleware (возвращает 500 с заголовками безопасности).
- Добавлена обработка исключений в endpoint /health (app/routers/health.py) с пробросом HTTPException.
- Добавлены тесты на обработку ошибок: test_health_handles_exception, test_middleware_handles_exception.
"""
