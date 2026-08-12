"""Проверка кодом: арбитр не ослабляет контракт, а гейт G3 видит немой CI.

Оба механизма нельзя проверять текстом промпта: право арбитра менять тесты
и есть способ сделать гейт зелёным, убрав проверки, а `|| true` в ci.yml
делает CI зелёным всегда. Поэтому здесь проверяются сами функции.
"""
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402

TEST_SRC = b"""import pytest


def test_a():
    assert 1 == 1
    assert 2 == 2


def test_b():
    with pytest.raises(ValueError):
        raise ValueError
"""


def snap(text: bytes = TEST_SRC) -> dict[str, bytes]:
    return {"tests/test_x.py": text}


# ─── tests_not_weakened ───────────────────────────────────────


def test_counts_считает_функции_и_проверки():
    funcs, asserts = main._test_counts(snap())
    assert funcs == 2
    assert asserts == 3          # два assert плюс один pytest.raises


def test_неизменные_тесты_проходят():
    ok, why = main.tests_not_weakened(snap(), snap())
    assert ok, why


def test_удаление_теста_отклоняется():
    after = snap(TEST_SRC.replace(b"""

def test_b():
    with pytest.raises(ValueError):
        raise ValueError
""", b""))
    ok, why = main.tests_not_weakened(snap(), after)
    assert not ok
    assert "число тестов" in why


def test_skip_маркер_отклоняется():
    after = snap(TEST_SRC.replace(b"def test_b():",
                                  b"@pytest.mark.skip\ndef test_b():"))
    ok, why = main.tests_not_weakened(snap(), after)
    assert not ok
    assert "skip" in why


def test_xfail_маркер_отклоняется():
    after = snap(TEST_SRC.replace(b"def test_b():",
                                  b"@pytest.mark.xfail\ndef test_b():"))
    ok, why = main.tests_not_weakened(snap(), after)
    assert not ok


def test_потеря_проверок_отклоняется():
    before = snap(TEST_SRC + b"""

def test_c():
    assert 3 == 3
    assert 4 == 4
    assert 5 == 5
    assert 6 == 6
    assert 7 == 7
    assert 8 == 8
    assert 9 == 9
""")
    after = snap(TEST_SRC + b"""

def test_c():
    assert 3 == 3
""")
    ok, why = main.tests_not_weakened(before, after)
    assert not ok
    assert "проверок" in why


def test_добавление_теста_разрешено():
    after = snap(TEST_SRC + b"""

def test_c():
    assert 3 == 3
""")
    ok, why = main.tests_not_weakened(snap(), after)
    assert ok, why


def test_переписанный_тест_той_же_силы_разрешён():
    """Смысл проверки может меняться, объём проверок — нет."""
    after = snap(TEST_SRC.replace(b"assert 1 == 1", b"assert bool(1) is True"))
    ok, why = main.tests_not_weakened(snap(), after)
    assert ok, why


# ─── снимок и откат тестов ────────────────────────────────────


def test_снимок_не_захватывает_журнал_stage(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_bytes(TEST_SRC)
    stage = tmp_path / "stage_01_tests" / "tests"
    stage.mkdir(parents=True)
    (stage / "test_x.py").write_bytes(TEST_SRC)
    s = main._tests_snapshot(tmp_path)
    assert list(s) == ["tests/test_x.py"]
    assert main._test_counts(s) == (2, 3)


def test_откат_возвращает_ослабленный_тест(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    f = tmp_path / "tests" / "test_x.py"
    f.write_bytes(TEST_SRC)
    before = main._tests_snapshot(tmp_path)
    f.write_bytes(b"def test_a():\n    assert True\n")
    (tmp_path / "tests" / "test_new.py").write_bytes(b"def test_z():\n    pass\n")
    changed = main._tests_restore(tmp_path, before)
    assert changed == 2                       # правка отката и удаление добавленного
    assert f.read_bytes() == TEST_SRC
    assert not (tmp_path / "tests" / "test_new.py").exists()


# ─── гейт G3 ──────────────────────────────────────────────────

CI_OK = """name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ -q
"""


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    """Проект с зелёными тестами и корректным ci.yml."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(CI_OK)
    (tmp_path / "requirements-dev.txt").write_text("pytest\n")
    monkeypatch.setattr(main, "_gate", lambda name, rd: (True, "1 passed"))
    return tmp_path


def test_g3_зелёный_на_корректном_ci(project: Path):
    ok, problems = main.gate_g3(project)
    assert ok, problems


def test_g3_ловит_or_true(project: Path):
    wf = project / ".github" / "workflows" / "ci.yml"
    wf.write_text(CI_OK.replace("pytest tests/ -q", "pytest tests/ -q || true"))
    ok, problems = main.gate_g3(project)
    assert not ok
    assert any("|| true" in p for p in problems)


def test_g3_ловит_continue_on_error(project: Path):
    wf = project / ".github" / "workflows" / "ci.yml"
    wf.write_text(CI_OK + "        continue-on-error: true\n")
    ok, problems = main.gate_g3(project)
    assert not ok


def test_g3_ловит_отсутствие_workflow(project: Path):
    (project / ".github" / "workflows" / "ci.yml").unlink()
    ok, problems = main.gate_g3(project)
    assert not ok
    assert any("ci.yml" in p for p in problems)


def test_g3_ловит_битый_yaml(project: Path):
    wf = project / ".github" / "workflows" / "ci.yml"
    wf.write_text("name: CI\non: [push\njobs:\n  test: {{{\n")
    ok, problems = main.gate_g3(project)
    assert not ok
    assert any("не разбирается" in p for p in problems)


def test_g3_требует_playwright_install(project: Path):
    (project / "requirements-dev.txt").write_text("pytest\npytest-playwright\n")
    ok, problems = main.gate_g3(project)
    assert not ok
    assert any("playwright" in p for p in problems)


def test_g3_красный_при_красных_тестах(project: Path, monkeypatch):
    monkeypatch.setattr(main, "_gate", lambda name, rd: (False, "1 failed"))
    ok, problems = main.gate_g3(project)
    assert not ok
    assert any("упаковка" in p for p in problems)
