"""STATUS.md (Ralph loop): живой статус прогона и его инъекция в правки.

Приём Loop Engineering: короткие итерации держат на диске актуальный статус,
который следующие фазы читают вместо перечитывания всего контекста.
Проверяются helper'ы `_status_append`/`_status_context` и запись в `_gate`.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


# ─── _status_append ───────────────────────────────────────────


def test_append_создаёт_STATUS(tmp_path: Path):
    main._status_append(tmp_path, "## Гейт G1: ЗЕЛЁНЫЙ — 5 passed")
    text = (tmp_path / "STATUS.md").read_text()
    assert "Гейт G1" in text
    assert text.endswith("\n")


def test_append_дописывает_к_существующему(tmp_path: Path):
    (tmp_path / "STATUS.md").write_text("# STATUS\n")
    main._status_append(tmp_path, "## Фаза A1")
    lines = (tmp_path / "STATUS.md").read_text().splitlines()
    assert lines[0] == "# STATUS"
    assert "## Фаза A1" in lines


def test_append_не_падает_на_None():
    main._status_append(None, "x")  # должно просто ничего не делать


# ─── _status_context ──────────────────────────────────────────


def test_context_пуст_без_файла(tmp_path: Path):
    assert main._status_context(tmp_path) == ""


def test_context_пуст_на_пустом_файле(tmp_path: Path):
    (tmp_path / "STATUS.md").write_text("   \n")
    assert main._status_context(tmp_path) == ""


def test_context_возвращает_хвост_с_заголовком(tmp_path: Path):
    (tmp_path / "STATUS.md").write_text("## Фаза A1\n## Гейт G1: ЗЕЛЁНЫЙ\n")
    ctx = main._status_context(tmp_path)
    assert ctx.startswith("=== СТАТУС ПРОГОНА")
    assert "Гейт G1" in ctx


def test_context_обрезает_до_хвоста(tmp_path: Path):
    """Длинный журнал не раздувает промпт: отдаётся только хвост."""
    (tmp_path / "STATUS.md").write_text("x" * 5000 + "\nКОНЕЦ\n")
    ctx = main._status_context(tmp_path)
    assert "КОНЕЦ" in ctx            # хвост сохранён
    assert "xxxxx" in ctx            # это последние 3000 символов
    header = "=== СТАТУС ПРОГОНА (что уже было сделано) ===\n"
    assert len(ctx) <= len(header) + 3000 + 2


# ─── _gate пишет статус ───────────────────────────────────────


def test_gate_пишет_STATUS(tmp_path: Path, monkeypatch):
    import tools
    monkeypatch.setattr(tools, "run_tests_quiet",
                        lambda rd: (True, "10 passed in 0.10s"))
    green, _summary = main._gate("G1", tmp_path)
    assert green is True
    text = (tmp_path / "STATUS.md").read_text()
    assert "Гейт G1: ЗЕЛЁНЫЙ" in text
    assert "10 passed" in text


def test_gate_красный_фиксируется(tmp_path: Path, monkeypatch):
    import tools
    monkeypatch.setattr(tools, "run_tests_quiet",
                        lambda rd: (False, "3 failed, 7 passed in 0.10s"))
    green, _summary = main._gate("G2_1", tmp_path)
    assert green is False
    text = (tmp_path / "STATUS.md").read_text()
    assert "Гейт G2_1: КРАСНЫЙ" in text
    assert "3 failed" in text
