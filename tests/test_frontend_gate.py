"""Гейт фронтенда: static/index.html обязан иметь рабочий JS."""
from pathlib import Path

import main  # noqa: E402


def test_no_frontend_is_ok(tmp_path: Path):
    """Нет static/index.html — гейт неприменим, не блокируем."""
    ok, problems = main.gate_frontend(tmp_path)
    assert ok is True and not problems


def test_frontend_without_js_is_red(tmp_path: Path):
    """Есть index.html, но нет .js — фронт неинтерактивен → красный."""
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "index.html").write_text("<html><button>Забронировать</button></html>")
    ok, problems = main.gate_frontend(tmp_path)
    assert ok is False
    assert any("нет ни одного .js" in p for p in problems)


def test_frontend_with_js_is_green(tmp_path: Path):
    """Есть index.html + подключённый app.js → зелёный."""
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "app.js").write_text("document.addEventListener('DOMContentLoaded', () => {});")
    (tmp_path / "static" / "index.html").write_text('<html><script src="app.js"></script></html>')
    ok, problems = main.gate_frontend(tmp_path)
    assert ok is True and not problems
