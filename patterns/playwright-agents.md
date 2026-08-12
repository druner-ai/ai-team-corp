# Playwright Patterns для Test Designer, Разработчика и QA

Применяй ЭТОТ файл, когда продукт — интерфейс в браузере: HTML-страница,
Canvas-игра, SPA. Для проектов с HTTP API и БД применяй `pytest-agents.md`.

## Главное правило: только синхронный стиль

`pytest-playwright` — синхронный плагин. Его фикстуры (`page`, `browser`,
`context`, `browser_name`) отдают синхронные объекты. Смешивание с
`pytest-asyncio` ломает ВСЕ тесты до единого.

```python
# ✅ ПРАВИЛЬНО — синхронно, без async/await
def test_canvas_present(page):
    page.goto(BASE_URL)
    expect(page.locator("#game-canvas")).to_be_visible()
```

```python
# ❌ НЕПРАВИЛЬНО — async-фикстура на синхронном плагине
@pytest.fixture
async def page(browser, base_url):        # переопределяет фикстуру плагина
    page = await browser.new_page()       # browser синхронный, await падает
    await page.goto(base_url)
    yield page
```

Такой код даёт `RuntimeError: Runner.run() cannot be called from a running
event loop`, а после снятия `asyncio_mode` — `AssertionError` во всех тестах.

Следствия, которые нужно соблюдать:

- НЕ пиши `async def` ни в тестах, ни в фикстурах.
- НЕ ставь `asyncio_mode = auto` в `pytest.ini`. Этот ключ нужен только
  проектам с реальными `async def test_*`.
- НЕ добавляй `pytest-asyncio` в `requirements-dev.txt` браузерного проекта.
- НЕ переопределяй фикстуры `page`, `browser`, `context` — они уже есть
  в плагине. Своей фикстуре давай другое имя: `game_page`, `loaded_page`.

## Как отдавать статику тестам

Одиночный HTML-файл открывай напрямую, без своего сервера — меньше кода
и ни одной проблемы с портами:

```python
import pathlib
import pytest

@pytest.fixture(scope="session")
def base_url():
    index = pathlib.Path(__file__).parent.parent / "index.html"
    return index.resolve().as_uri()          # file:///.../index.html
```

`file://` не подходит, если код использует `fetch`, модули ES или
Service Worker — их блокирует CORS. Тогда поднимай сервер, но НИКОГДА не
хардкодь порт: он бывает занят другим прогоном или забытым процессом.

```python
import http.server
import threading
import pytest

@pytest.fixture(scope="session")
def base_url(tmp_path_factory):
    root = pathlib.Path(__file__).parent.parent
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(
        *a, directory=str(root), **kw
    )
    # порт 0 — ядро выдаёт свободный; ThreadingHTTPServer имеет
    # allow_reuse_address = 1, поэтому адрес не остаётся занятым
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
```

Обрати внимание: фикстура ОБЯЗАНА гасить сервер через `shutdown()` в
teardown. Демон-поток без остановки оставляет слушающий сокет.

## Контракт тестируемости для Canvas

Пиксели проверять нельзя — тест станет хрупким и нечитаемым. Объяви
контракт: приложение публикует своё состояние в `window`, тесты читают его
через `page.evaluate()`. Test Designer фиксирует контракт в тестах,
Разработчик обязан его реализовать.

```python
def test_eating_food_increases_score(page):
    page.goto(BASE_URL)
    page.evaluate("() => window.__game.reset()")
    before = page.evaluate("() => window.__game.state.score")
    page.evaluate("() => window.__game.forceEat()")
    assert page.evaluate("() => window.__game.state.score") > before
```

Минимальный контракт, который Разработчик выставляет наружу:

```javascript
window.__game = {
  state: { score, highScore, direction, snake, food, isGameOver },
  reset() {},        // новая игра из детерминированного состояния
  step() {},         // ровно один игровой тик, без таймера
  setDirection(d) {},
};
```

`step()` критичен: тест должен двигать игру вручную, а не ждать таймер.

## Ожидания вместо сна

```python
# ✅ авто-ожидание, падает по таймауту с внятным сообщением
expect(page.locator("#game-over")).to_be_visible()
page.wait_for_function("() => window.__game.state.isGameOver === true")

# ❌ гонка: на медленной машине упадёт, на быстрой тратит время
time.sleep(2)
assert page.locator("#game-over").is_visible()
```

Импорт: `from playwright.sync_api import expect`.

## Ввод: клавиатура и свайпы

```python
page.keyboard.press("ArrowLeft")

# свайп — три события, между ними нужны реальные координаты
box = page.locator("#game-canvas").bounding_box()
cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
page.mouse.move(cx, cy)
page.mouse.down()
page.mouse.move(cx + 120, cy, steps=10)   # steps обязателен: без него
page.mouse.up()                            # touchmove не сгенерируется
```

Если код слушает `touchstart`/`touchmove`, мышь их не вызовет. Тогда
диспатчь события напрямую через `page.evaluate()` с `TouchEvent`.

## localStorage

```python
def test_highscore_persists(page):
    page.goto(BASE_URL)
    page.evaluate("() => localStorage.setItem('highScore', '42')")
    page.reload()
    assert page.evaluate("() => window.__game.state.highScore") == 42
```

Для `file://` URL localStorage в Chromium доступен, но изолирован по
origin — очищай его в фикстуре, иначе тесты потекут друг в друга.

## Зависимости и браузер

`requirements-dev.txt` браузерного проекта:

```
pytest>=8.0.0
pytest-playwright>=0.4.0
```

Браузер НЕ является pip-пакетом и в requirements не объявляется. Его
ставит отдельная команда, и место для неё — рецепт CI (задача DevOps):

```yaml
- name: Install Playwright browsers
  run: .venv/bin/playwright install --with-deps chromium
```

`--with-deps` подтягивает системные библиотеки (`libgbm1`, `libasound2`),
без которых браузер не стартует.

## Anti-patterns

| ❌ Не делай | ✅ Делай |
|:---|:---|
| `async def` фикстура или тест | синхронный стиль |
| `asyncio_mode = auto` в pytest.ini | не указывать вовсе |
| `pytest-asyncio` в requirements-dev | только `pytest-playwright` |
| переопределять фикстуру `page` | своя фикстура с другим именем |
| `PORT = 8765` | порт `0`, ядро выдаст свободный |
| `serve_forever()` без `shutdown()` | гасить сервер в teardown |
| `time.sleep()` | `expect()`, `wait_for_function()` |
| сверять пиксели canvas | читать `window.__game.state` |
| ждать игровой таймер | вызывать `step()` вручную |
| `page.mouse.move()` без `steps` | `steps=10` для свайпа |

## QA Gate checklist

- [ ] ни одного `async def` в `tests/`
- [ ] в `pytest.ini` нет `asyncio_mode`
- [ ] `requirements-dev.txt` содержит `pytest-playwright` и НЕ содержит `pytest-asyncio`
- [ ] фикстура `page` из плагина не переопределена
- [ ] порт сервера не захардкожен, сервер гасится в teardown
- [ ] в CI есть шаг `playwright install --with-deps chromium`
- [ ] состояние читается через `window.__game`, а не по пикселям
- [ ] нет `time.sleep()` — только `expect` и `wait_for_*`
