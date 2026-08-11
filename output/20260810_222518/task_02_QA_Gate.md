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

Отчёт о проверке кода: список проблем с приоритетами, конкретные файлы и строки, итоговый вердикт (❌ No-Go).

## 🟡 Критически важные проблемы

### 1. 🔴 Неправильное добавление Rate Limit Middleware (ломает архитектуру)
**Файл**: `app/main.py`, строка 85-99
**Описание**: Разработчик добавил RateLimitMiddleware через `@app.on_event("startup")`, который добавляет middleware ПОСЛЕ того, как приложение уже создано. В результате:
- Все запросы проходят через CORS middleware, но RateLimitMiddleware будет добавлен в неправильном порядке (или не будет работать корректно, так как Starlette не гарантирует правильный порядок при добавлении middleware после создания приложения).
- Архитектурный документ явно указывает, что RateLimitMiddleware должен быть первым/внешним middleware (чтобы отсекать запросы до основной обработки). Сейчас он будет добавлен последним.
**Предложение по исправлению**: Добавить `RateLimitMiddleware` внутри функции `create_app()` с использованием `State` или передавать `CacheService` через глобальный синглтон. Правильный подход — инициализировать инстанс `RateLimitMiddleware` после создания `app` внутри `create_app()`, передав туда `CacheService`, который может быть лениво инициализирован. Или, что проще и безопаснее: получить `CacheService` внутри middleware при первом вызове, используя паттерн Singleton.
```python
# В create_app()
# Register routers first...
# Then add middleware in correct order
app.add_middleware(CORSMiddleware, ...)
# RateLimitMiddleware should be added here, not in startup
from app.middleware.rate_limit import RateLimitMiddleware
# Need to ensure CacheService is initialized. This is a chicken-and-egg problem.
# Solution: make RateLimitMiddleware lazy-init the cache_service on first request.
```

### 2. 🔴 Небезопасная обработка исключений в `get_db_session`
**Файл**: `app/db/session.py`, строка 67-76
**Описание**: Голый `except Exception` без фильтрации. В случае любой ошибки (включая `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`) будет вызван `rollback()` и `close()`. Это может привести к проблемам:
- `KeyboardInterrupt` во время ожидания БД — rollback будет вызван, но сессия может быть в непредсказуемом состоянии.
- Нет логирования ошибок — проглатываются все исключения в слое работы с БД.
**Предложение по исправлению**: Ловить только `SQLAlchemyError` и `Exception`, но не `BaseException`. Добавить логирование.
```python
except Exception as e:
    await session.rollback()
    raise
```

### 3. 🟡 Потенциальная гонка данных (Race Condition) в статистике
**Файл**: `app/services/cache_service.py`, строка 92-100 (`increment_stats`)
**Файл**: `app/services/stats_service.py`, строка 40-58 (`record_click`)
**Описание**: В `get_original_url` (url_service.py, строка 97) запись клика происходит **синхронно** и **с ожиданием** (`await self.stats_service.record_click`). При высокой нагрузке это может:
- Замедлить ответ на редирект (мы ждём инкремент в Redis и, возможно, запись в БД)
- `record_click` использует `INCR`, который атомарен, но последующая синхронизация в БД при `new_count % sync_threshold == 0` может привести к тому, что два concurrent запроса прочитают одинаковое значение `new_count` (10 и 10) и оба попытаются синхронизироваться, но только один Commit произойдёт, другой получит ошибку. Хотя там есть `rollback()`, это всё же неидеально.
- Архитектурный документ предполагает "буферизованную запись" и периодическую синхронизацию, но не через CRITICAL SECTION без блокировки.
**Предложение по исправлению**: Сделать запись клика фоном (create_task) и добавить более надёжную синхронизацию с БД (например, periodic background task или использование Redis Stream для асинхронной записи). Для `get_original_url` — запись клика НЕ должна замедлять редирект.
```python
# In url_service.py
import asyncio
# ...
async def get_original_url(self, short_id, db_session):
    # ... get cached URL ...
    # Schedule stats recording in background, don't await
    asyncio.create_task(self.stats_service.record_click(short_id, db_session))
    # ... return URL ...
```

### 4. 🟡 Неверная проверка rate limit в `check_rate_limit`
**Файл**: `app/services/cache_service.py`, строка 109-140 (`check_rate_limit`)
**Описание**: Несмотря на использование pipeline (строка 117), Redis-вызовы не атомарны в плане проверки и инкремента. 
- Строка 116: `current = await self.redis_client.get(key)` — это отдельный запрос. После того, как мы прочитали `current` (None), другой запрос может создать ключ.
- Строка 117: `async with self.redis_client.pipeline() as pipe:` — pipeline, но внутри сначала идёт `await pipe.setex(key, window, 1)`, затем `await pipe.ttl(key)`. Это не коммитится атомарно.
- Классическая проблема "race condition" в реализации sliding window counter с INCR. Два запроса от одного IP могут одновременно прочитать `current_count = 99`, оба решат, что они ещё в лимите (99 < 100), оба сделают `INCR`, и реально пройдёт 101 запрос.
- Документ ожидает 100 req/min, а реализация пропустит больше.
**Предложение по исправлению**: Использовать атомарный Lua-скрипт для rate limiting или использовать библиотеку типа `slowapi` с правильной реализацией. Как минимум, нужно использовать `SET NX` с TTL + `INCR` в мульти-командах Lua.
```lua
-- Lua script for atomic rate limit check
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = redis.call('GET', key)
if current and tonumber(current) >= limit then
    local ttl = redis.call('TTL', key)
    return {0, 0, ttl}
end
local new_count = redis.call('INCR', key)
if new_count == 1 then
    redis.call('EXPIRE', key, window)
end
local ttl = redis.call('TTL', key)
return {1, limit - new_count, ttl}
```

### 5. 🟡 Race Condition в `create_short_url` — проверка и вставка не атомарны
**Файл**: `app/services/url_service.py`, строка 42-69
**Описание**: Метод `create_short_url` генерирует ID, проверяет его наличие (SELECT), затем вставляет (INSERT). Между SELECT и INSERT другой запрос может вставить такой же short_id (при крайне низкой вероятности, но с 3.5 триллионами комбинаций — это практически невозможно на практике). **Проблема другая**: `db_session.add()` + `commit()` могут бросить IntegrityError, если уникальный индекс `short_id` будет нарушен. Это исключение не обрабатывается — код просто вызовет `db_session.commit()`, SQLAlchemy поднимет `IntegrityError`, который всплывёт как HTTP 500.
- Код не хендлит `IntegrityError` на случай, если случай сгенерировал тот же ID.
**Предложение по исправлению**: Обернуть блок генерации-добавления в цикл с обработкой `IntegrityError` (или использовать `ON CONFLICT DO NOTHING` + RETURNING, но это сложнее с async SQLAlchemy). Проще:
```python
for attempt in range(MAX_GENERATION_ATTEMPTS):
    short_id = generate_short_id(self.short_id_length)
    try:
        url_mapping = UrlMapping(short_id=short_id, original_url=str(original_url))
        db_session.add(url_mapping)
        await db_session.commit()
        await db_session.refresh(url_mapping)
        await self.cache_service.set_url(short_id, str(original_url))
        return url_mapping
    except IntegrityError:
        await db_session.rollback()
        if attempt == MAX_GENERATION_ATTEMPTS - 1:
            raise ValueError(...)
```

### 6. 🟡 Неправильная обработка здорового пула Redis
**Файл**: `app/db/redis_client.py`, строка 20-31
**Описание**: Глобальные переменные `_redis_pool и _redis_client`. Если функция `get_redis_client` вызывается конкурентно (что и происходит с asyncio), два вызова одновременно могут пройти проверку `if _redis_client is None:`, и будет создано два пула/клиента, один из которых перетрёт другой. Это не потокобезопасно, хотя asyncio однопоточный, `await` может прервать выполнение между проверкой и присвоением.
**Предложение по исправлению**: Использовать `asyncio.Lock()` для защиты инициализации клиента, инициализировать его на старте (в lifespan), или использовать стандартный подход с `await redis.from_url()` без глобальной переменной (создавать при каждом вызове — это overhead, но безопаснее для `lazy` инициализации). Либо просто убрать ленивую инициализацию и инициализировать в `lifespan.startup`.
```python
_redis_lock = asyncio.Lock()
async def get_redis_client():
    global _redis_pool, _redis_client
    if _redis_client is None:
        async with _redis_lock:
            if _redis_client is None:  # Double-checked locking
                _redis_pool = ...
                _redis_client = ...
    return _redis_client
```

### 7. 🟡 `close_engine` не вызывается корректно при shutdown
**Файл**: `app/main.py`, строка 62-64 (`lifespan`)
**Файл**: `app/db/session.py`, строка 85-89 (`close_engine`)
**Описание**: В `lifespan.shutdown` вызывается `close_engine()`, но `engine` — это глобальный модульный объект, который мог быть проинициализирован при первом импорте. Проблема в том, что `alembic/env.py` импортирует `engine` из `app.config` и создаёт свой engine для миграций. Если Alembic завершится раньше (что обычно), это не критично. Но если `close_engine()` вызовет `await engine.dispose()`, а потом кто-то попытается использовать `engine` (например, health check ещё висит) — будет исключение. Хотя архитектура ожидает graceful shutdown, нет гарантии, что `engine` не используется после dispose.
**Предложение по исправлению**: Убедиться, что `engine` не используется после вызова `close_engine()`. Установить `engine = None` после dispose или проверять его состояние. В контексте FastAPI lifespan это менее критично, т.к. после shutdown приложение не принимает запросы, но лучше перестраховаться.

### 8. 🟡 Потенциальная утечка памяти в `logger.error` при исключении
**Файл**: `app/services/url_service.py`, строка 82
**Описание**: `logger.error(f"Failed to generate unique short ID after max attempts")` — это нормально. Но строкой выше (`logger.info(f"Created short URL: {short_id} -> {original_url}")`) логируется полный URL. Архитектурный документ (Раздел 6, Безопасность) явно указывает: "**Логи: не логируются полные URL в production (могут содержать чувствительные параметры). Логируется только short_id и метаданные.**". Здесь нарушено это требование.
**Предложение по исправлению**: Убрать `original_url` из логов. Логировать только `short_id`.
```python
logger.info(f"Created short URL: {short_id}")
```

### 9. 🟡 Валидация URL в `ShortenRequest` избыточна, но не блокирует
**Файл**: `app/routers/shorten.py`, строка 44-49
**Файл**: `app/schemas/url.py`, строка 28-40
**Описание**: `validate_url_scheme` в Pydantic и дополнительный вызов `validate_url_safety` в роутере — дублируют функциональность. Первая проверяет схему, вторая — тоже схему + SSRF. Pydantic `HttpUrl` уже проверяет схему (только http/https). Дополнительная проверка схемы в `validate_url_safety` избыточна (но не вредна). Это стилистическая проблема, не критическая.

### 10. 🟢 (Минор) Неверный порядок роутеров в main.py (может вызвать баги)
**Файл**: `app/main.py`, строка 79-84
**Описание**: Комментарий гласит "Order matters", но роутеры регистрируются в порядке: `health_router` (путь `/health`), `shorten_router` (`/shorten`), `stats_router` (`/stats/{short_id}`), `delete_router` (`/{short_id}`), `redirect_router` (`/{short_id}`). Проблема: `delete_router` и `redirect_router` имеют одинаковый путь `/{short_id}`. FastAPI обрабатывает их в порядке регистрации. Если DELETE /{id} зарегистрирован ДО GET /{id}, то при получении GET-запроса на /{id} FastAPI будет искать совпадение по HTTP методу. Он найдёт сначала `DELETE`, но он не совпадает по методу, потом перейдёт к `GET` и найдёт `redirect_router`. Это работает, **но НЕ ВСЕГДА**. Если кто-то поменяет порядок или добавит другой метод (PATCH) к `/{short_id}`, начнутся проблемы.
**Предложение по исправлению**: Роутеры с разными HTTP методами на один путь должны быть **в рамках одного APIRouter** или зарегистрированы в одном месте, чтобы FastAPI мог нормально построить маршруты. Сейчас это потенциальный источник багов при дальнейшей разработке.
```python
# Рекомендуется объединить в один router:
redirect_router = APIRouter()
@redirect_router.get("/{short_id}")
@redirect_router.delete("/{short_id}")
```

### 11. 🟢 (Минор) Отсутствие обработки `ConnectionResetError` и `CancelledError`
**Файл**: `app/db/session.py`, `app/db/redis_client.py`
**Описание**: В асинхронном приложении возможны `CancelledError` (asyncio) и `ConnectionResetError` (сеть). При получении таких ошибок в `get_db_session` или `get_redis_client` приложение может упасть, если их не обрабатывать. Это не критично для текущего состояния, так как Uvicorn должен их перехватывать, но лучше явно обрабатывать при закрытии соединения.
**Предложение по исправлению**: Добавить обработку `asyncio.CancelledError` в соответствующих методах. Это best practice для асинхронных приложений.

### 12. 🟢 (Минор) Не хватает проверки в роутере `redirect` на валидность path-параметра
**Файл**: `app/routers/redirect.py`, строка 23-40
**Описание**: Входной параметр `short_id` — это строка `str`. Если пользователь передаст ID длиной 1000 символов, он будет передан в `validate_short_id`, который вернёт `False`, и будет возвращён 404. Это ожидаемое поведение, но лучше использовать `Path(..., min_length=7, max_length=7)` в аннотации FastAPI для отклонения мусора раньше.
**Предложение по исправлению**: Добавить Path валидацию в аргумент `short_id`.
```python
from fastapi import Path
async def redirect_to_url(
    short_id: str = Path(..., min_length=7, max_length=7, pattern="^[a-zA-Z0-9]+$"),
    ...
```

## ИТОГОВЫЙ ВЕРДИКТ: ❌ No-Go

**Требуются правки.** Перечень файлов и строк, которые нужно исправить (критические и важные):

1. **`app/main.py`, строка 85-99**: Исправить порядок добавления RateLimitMiddleware. **Приоритет: 🔴**
2. **`app/db/session.py`, строка 67-76**: Исправить голый `except`, добавить логирование. **Приоритет: 🔴**
3. **`app/services/url_service.py`, строка 97**: Сделать `record_click` асинхронным (через `create_task`). **Приоритет: 🟡**
4. **`app/services/cache_service.py`, строка 109-140**: Исправить race condition в rate limit. Использовать Lua-скрипт или атомарный INCR с проверкой. **Приоритет: 🟡**
5. **`app/services/url_service.py`, строка 42-69**: Обрабатывать `IntegrityError` при вставке short_id. **Приоритет: 🟡**
6. **`app/db/redis_client.py`, строка 20-31**: Исправить race condition при инициализации Redis. Использовать `asyncio.Lock` или инициализировать в lifespan. **Приоритет: 🟡**
7. **`app/services/url_service.py`, строка 82**: Убрать `original_url` из логов (нарушение архитектуры). **Приоритет: 🟡**
8. **`app/main.py`, строка 79-84**: Объединить роутеры с одинаковыми путями в один APIRouter. **Приоритет: 🟢 (но рекомендую сделать)**
9. **`app/routers/redirect.py`, строка 23**: Добавить Path валидацию. **Приоритет: 🟢 (рекомендуется)**

**Причина No-Go:**
- **Проблема №1 (RateLimitMiddleware) критична** — middleware добавлен неправильно, что противоречит архитектурному документу (должен быть внешним, а добавляется после создания приложения) и может привести к тому, что rate limiting будет применяться не ко всем запросам (например, к /health), и порядок middleware будет нарушен. Это может привести к уязвимости (неограниченный доступ к эндпоинтам до применения лимита) и является грубым архитектурным нарушением.
- **Проблемы №2, 4, 5 — это серьёзные логические и безопасностные дефекты**. Race condition в rate limiting и обработка ошибок in the service layer могут привести к непредсказуемому поведению в production.
- **Проблема №7 — нарушение требований безопасности** из архитектурного документа.

После исправления всех **🔴 и 🟡** проблем можно будет пересмотреть вердикт.