"""Роль UX/UI дизайнера: фаза A1d, права записи, инъекция дизайна в A2."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402
import config  # noqa: E402
from agents import ux_designer  # noqa: E402


def test_дизайнер_есть_в_моделях():
    assert "ux_designer" in config.MODELS
    assert config.MODELS["ux_designer"]["name"] == "moonshotai/kimi-k2.7-code"


def test_фаза_A1D_в_весах_стоимости():
    assert config.PHASE_MODEL_WEIGHTS["A1D"] == {"ux_designer": 1.0}


def test_агент_имеет_роль():
    assert ux_designer.role == "UX/UI дизайнер"


def test_права_позволяют_статику():
    for rel in ("static/css/styles.css", "static/index.html", "design.md"):
        ok, why = main._write_allowed("UX/UI дизайнер", rel)
        assert ok, f"{rel}: {why}"


def test_права_запрещают_backend_и_tests():
    assert not main._write_allowed("UX/UI дизайнер", "backend/main.py")[0]
    assert not main._write_allowed("UX/UI дизайнер", "tests/test_x.py")[0]


def test_make_design_task_содержит_артефакты():
    from tasks import make_design_task
    t = make_design_task("спека", enhance=False)
    assert t.name == "design"
    assert "design.md" in t.description
    assert "styles.css" in t.description
    assert "index.html" in t.description


def test_make_impl_tasks_инъектирует_дизайн():
    from tasks import make_impl_tasks
    tasks = make_impl_tasks("спека", design="палитра: синий")
    # дизайн уходит Test Designer'у и Разработчику (но не QA-ревью)
    with_design = [t for t in tasks if "ДИЗАЙН UI" in t.description]
    assert len(with_design) == 2
    assert all("палитра: синий" in t.description for t in with_design)


def test_make_impl_tasks_без_дизайна_чист():
    from tasks import make_impl_tasks
    tasks = make_impl_tasks("спека")
    assert all("ДИЗАЙН UI" not in t.description for t in tasks)
