"""Cross-run память (Loop Engineering: Memory = источник правды).

Прогон в режиме --enhance читает историю проекта и дописывает свой итог,
чтобы Архитектор следующего прогона видел «что уже решали», а не стартовал
с нуля. Проверяются helper'ы _memory_path/_memory_read/_memory_append.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402
import memory  # noqa: E402


def test_path_слэш_в_подчёркивание(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    p = main._memory_path("druner-ai/internet-radio")
    assert p.name == "druner-ai__internet-radio.md"
    assert p.parent == tmp_path


def test_read_пусто_без_файла(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    assert main._memory_read("druner-ai/internet-radio") == ""


def test_append_и_read_круговорот(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    main._memory_append("druner-ai/x", "## Прогон 1\n- Статус: красные")
    assert "## Прогон 1" in main._memory_read("druner-ai/x")


def test_append_дописывает_не_затирает(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    main._memory_append("druner-ai/x", "## Прогон 1")
    main._memory_append("druner-ai/x", "## Прогон 2")
    text = main._memory_read("druner-ai/x")
    assert "## Прогон 1" in text
    assert "## Прогон 2" in text


def test_разные_репо_разные_файлы(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    main._memory_append("druner-ai/a", "A")
    main._memory_append("druner-ai/b", "B")
    assert main._memory_read("druner-ai/a") == "A"
    assert main._memory_read("druner-ai/b") == "B"
    assert "B" not in main._memory_read("druner-ai/a")


def test_read_обрезка_пустого_файла(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    (tmp_path / "druner-ai__x.md").write_text("   \n")
    assert main._memory_read("druner-ai/x") == ""


def test_make_spec_task_включает_историю():
    from tasks import make_spec_task
    t = make_spec_task("добавить health", enhance=True, existing_code="code",
                       memory="## Прогон 1")
    assert "ИСТОРИЯ ПРОЕКТА" in t.description
    assert "## Прогон 1" in t.description


def test_make_spec_task_без_истории_чист():
    from tasks import make_spec_task
    t = make_spec_task("добавить health", enhance=True, existing_code="code")
    assert "ИСТОРИЯ ПРОЕКТА" not in t.description
