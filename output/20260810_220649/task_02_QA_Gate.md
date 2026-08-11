# QA Gate

## Задача

        Проверь код Разработчика на соответствие архитектурному документу Архитектора.

        ЧТО ПРОВЕРЯТЬ:
        1. **Соответствие архитектуре**: все ли компоненты реализованы? Нет ли лишнего?
        2. **Безопасность**: SQL-инъекции, XSS, утечки секретов, небезопасные зависимости
        3. **Обработка ошибок**: все ли исключения обработаны? Нет ли голых try/except?
        4. **Валидация**: проверяются ли входные данные на всех endpoint-ах?
        5. **Тесты**: есть ли они? Покрывают ли основные сценарии?
        6. **Style guide**: PEP 8, нейминг, типизация

        ФОРМАТ ОТВЕТА:
        Для каждой найденной проблемы:
        - Приоритет: 🔴 (критично — блокирует запуск) / 🟡 (важно — нужно исправить) / 🟢 (минор — можно так)
        - Файл и строка (если применимо)
        - Описание проблемы
        - Предложение по исправлению

        В конце: ИТОГОВЫЙ ВЕРДИКТ — ✅ Go (нет критических проблем) или ❌ No-Go (требуются правки).
        Если No-Go — перечисли КОНКРЕТНЫЕ файлы и строки, которые нужно исправить.
        

## Результат

# 🚨 QA Gate: Отчёт о проверке кода

## 🔴 Критические проблемы

### 1. Rate Limiter реализован как fixed-window, а не sliding window
- **Файл:** `app/core/rate_limiter.py`, строка 18-32
- **Описание:** Архитектурный документ явно требует "sliding window algorithm on Redis", но реализация использует простой fixed-window counter. Fixed-window уязвим для burst-атак в конце окна.
- **Предложение:** Переписать на sliding window с использованием Redis sorted sets или Lua-скрипта:
```python
async def is_rate_limited(self, client_ip: str) -> Optional[int]:
    key = f"rate:{client_ip}"
    now = time.time()
    window_start = now - self.window
    
    # Использовать sorted set для sliding window
    await self.redis.zremrangebyscore(key, 0, window_start)
    request_count = await self.redis.zcard(key)
    
    if request_count >= self.limit:
        oldest = await self.redis.zrange(key, 0, 0, withscores=True)
        retry_after = int(oldest[0][1] - window_start) if oldest else self.window
        return None  # blocked
        
    await self.redis.zadd(key, {str(now): now})
    await self.redis.expire(key, self.window)
    return self.limit - request_count - 1
```

### 2. background_tasks выполняются в том же процессе - нет гарантии завершения при shutdown
- **Файл:** `app/api/v1/redirect.py`, строка 38, 57
- **Описание:** FastAPI background_tasks выполняются после отправки ответа, но не гарантируют завершение при graceful shutdown. При аварийном завершении контейнера счетчики не сохранятся.
- **Предложение:** Использовать task queue (Celery/Redis Queue) или хотя бы фоновый thread с asyncio.ensure_future и cancellation handling.

### 3. Тест на stats не проверяет инкремент счетчика должным образом
- **Файл:** `tests/test_stats.py`, строка 22-26
- **Описание:** Тест предполагает, что background task выполнится мгновенно. Это race condition в тесте - тест может падать недетерминированно.
- **Предложение:** Добавить ожидание/retry для проверки счетчика:
```python
@pytest.mark.asyncio
async def test_stats_after_redirect(app: AsyncClient):
    # Create + redirect
    ...
    # Wait for background task
    for _ in range(10):
        stats_resp = await app.get(f"/api/v1/stats/{short_id}")
        if stats_resp.json()["click_count"] == 1:
            break
        await asyncio.sleep(0.1)
    assert stats_resp.json()["click_count"] == 1
```

### 4. Нет теста на 410 Gone для истекших ссылок
- **Файл:** `tests/test_redirect.py`
- **Описание:** Архитектура требует HTTP 410 для истекших URL, но тест не покрывает этот сценарий.
- **Предложение:** Добавить тест:
```python
@pytest.mark.asyncio
async def test_redirect_expired(app: AsyncClient):
    import datetime
    expired_date = "2020-01-01T00:00:00Z"
    payload = {"url": "https://example.com", "expires_at": expired_date}
    create_resp = await app.post("/api/v1/shorten", json=payload)
    short_id = create_resp.json()["short_id"]
    
    redirect_resp = await app.get(f"/api/v1/{short_id}", follow_redirects=False)
    assert redirect_resp.status_code == 410
```

---

## 🟡 Важные проблемы

### 5. Нет валидации и санитизации short_id на endpoint-ах
- **Файл:** `app/api/v1/redirect.py`, строка 20
- **Описание:** short_id принимается как простая строка без валидации. Zabbix/RCE через очень длинный short_id может вызвать DoS на БД. Нужна проверка длины и формата.
- **Предложение:** Создать Pydantic модель или path converter:
```python
from fastapi import Path

@router.get("/{short_id}")
async def redirect_to_original(
    short_id: str = Path(..., min_length=1, max_length=7, regex=r'^[a-zA-Z0-9]+$'),
    ...
):
```

### 6. SQLAlchemy session не инжектится в Rate Limiter для проверки статуса БД
- **Файл:** `app/middleware/rate_limit.py`, строка 27-28
- **Описание:** Rate limiting middleware использует get_redis(), но не имеет доступа к get_db(). При недоступности БД rate limit все равно сработает, но редирект упадет с ошибкой.
- **Предложение:** Middleware должна кэшировать состояние БД или проверять через health-check.

### 7. Нет обработки ошибок при получении IP клиента
- **Файл:** `app/middleware/rate_limit.py`, строка 30
- **Описание:** `request.client.host` может быть None (например, за reverse proxy). Это вызовет AttributeError.
- **Предложение:**
```python
client_ip = request.client.host if request.client else "unknown"
```

### 8. Тест rate_limit использует некорректный endpoint
- **Файл:** `tests/test_rate_limit.py`, строка 18-21
- **Описание:** Запрос к `/api/v1/shorten/health` не существует (health-check на `/health`). Тест пройдет только потому что любой ненайденный endpoint возвращает ошибку, но это не проверяет headers.
- **Предложение:** Использовать валидный endpoint:
```python
@pytest.mark.asyncio
async def test_rate_limit_headers_exist(app: AsyncClient):
    payload = {"url": "https://example.com"}
    resp = await app.post("/api/v1/shorten", json=payload)
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
```

### 9. Отсутствует миграция для partial unique index
- **Файл:** `alembic/versions/001_initial_urls.py`, строка 36
- **Описание:** Архитектура требует `CREATE INDEX idx_urls_active ON urls(short_id) WHERE is_active = TRUE`, но миграция создает обычный index на short_id, а не partial.
- **Предложение:** Исправить миграцию:
```python
op.create_index('idx_urls_active', 'urls', ['short_id'], 
                postgresql_where=sa.text('is_active = TRUE'))
```

### 10. Возможна ситуация, когда Redis недоступен при старте
- **Файл:** `app/main.py`, строка 29
- **Описание:** `await get_redis()` может вызвать исключение при недоступности Redis, что убьет приложение при старте. Нужен gracefull degradation.
- **Предложение:** Завернуть в try/except с логированием:

---

## 🟢 Минорные замечания

### 11. PEP 8: Длинные строки
- **Файл:** `app/__init__.py`, строка 1 (нет такой)
- **Описание:** В файлах есть строки > 79 символов (PEP 8). В pyproject.toml указан max-line-length=100, что ок, но flake8 с этим не сработает при линт.

### 12. Не используется asyncio.Lock для rate limiter
- **Файл:** `app/core/rate_limiter.py`
- **Описание:** При конкурентных запросах от одного IP `INCR` может вызвать race condition. Atomic операции Redis это reslove, но если используется KEYS/LUA скрипт, нужна блокировка.

### 13. Тест на rate_limit не проверяет 429
- **Файл:** `tests/test_rate_limit.py`
- **Описание:** Нет теста на превышение лимита. Даже с mock Redis легко проверить.

### 14. Отсутствует обработка пустого expires_at в shorten
- **Файл:** `app/api/v1/shorten.py`, строка 30
- **Описание:** Если expires_at не передан, поле будет None, что корректно, но валидация Pydantic модели не проверяет, что expires_at > now().

---

## 📊 ИТОГОВЫЙ ВЕРДИКТ: ❌ No-Go

### Требуют исправления (конкретные файлы и строки):

| № | Файл | Строка | Описание |
|---|------|--------|----------|
| 1 | `app/core/rate_limiter.py` | 18-32 | Реализация fixed-window вместо sliding window |
| 2 | `app/api/v1/redirect.py` | 38, 57 | Нет гарантии сохранения счетчиков при shutdown |
| 3 | `tests/test_stats.py` | 22-26 | Race condition в тесте инкремента |
| 4 | `tests/test_redirect.py` | - | Нет теста HTTP 410 для истекших ссылок |
| 5 | `app/api/v1/redirect.py` | 20 | Нет валидации short_id на всех endpoint-ах |
| 6 | `app/middleware/rate_limit.py` | 27-28 | Отсутствует проверка БД в middleware |
| 7 | `app/middleware/rate_limit.py` | 30 | Уязвимость к None в request.client |
| 8 | `tests/test_rate_limit.py` | 18-21 | Некорректный endpoint в тесте |
| 9 | `alembic/versions/001_initial_urls.py` | 36 | Non-partial index вместо partial |
| 10 | `app/main.py` | 29 | Нет обработки ошибок Redis |

### Сводка:
- **🔴 Критично:** 4 проблемы (блокируют запуск в production)
- **🟡 Важно:** 6 проблем (требуют исправления перед release)
- **🟢 Минор:** 4 замечания (можно отложить)

**Статус: ❌ No-Go** - Требуется исправление минимум 4 критических проблем перед деплоем. После исправления запросить повторную проверку.