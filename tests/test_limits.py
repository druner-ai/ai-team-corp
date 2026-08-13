"""Лимиты first-class (Loop Engineering): единый блок и видимость агентам.

Лимиты (бюджет/попытки/таймаут) — first-class узел outer loop: один источник
правды в config.LIMITS и сводка, которую агент видит в контексте правок.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402
import config  # noqa: E402


def test_limits_единый_блок_полный():
    for k in ("soft_budget_usd", "hard_budget_usd", "max_fix_attempts",
              "max_arbiter_fix_attempts", "max_ci_fix_attempts",
              "test_timeout_seconds"):
        assert k in config.LIMITS


def test_test_timeout_число_положительное():
    assert isinstance(config.TEST_TIMEOUT, int)
    assert config.TEST_TIMEOUT > 0


def test_limits_context_содержит_границы():
    ctx = main._limits_context()
    assert "ЛИМИТЫ ПРОГОНА" in ctx
    assert "Бюджет" in ctx
    assert "Попыток починки" in ctx
    assert "Таймаут теста" in ctx
    assert str(config.TEST_TIMEOUT) in ctx


def test_fix_context_склеивает_лимиты_статус_и_файлы(tmp_path: Path):
    (tmp_path / "STATUS.md").write_text("## Гейт G1: КРАСНЫЙ\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_a():\n    assert False\n")
    ctx = main._fix_context(tmp_path, "FAILED tests/test_x.py - assert False")
    assert "ЛИМИТЫ ПРОГОНА" in ctx
    assert "СТАТУС ПРОГОНА" in ctx
    assert "test_x.py" in ctx


def test_pytest_args_таймаут_интерполирован():
    """Регресс: --timeout должен получить ЗНАЧЕНИЕ, а не литерал {_TEST_TIMEOUT}.

    Прогон 20260813_201740 сломался на 0 collected по всем гейтам: в tools.py
    была обычная строка вместо f-string, pytest падал 'invalid float value'.
    Юнит-тесты это не ловили (мокают run_tests_quiet) — проверяем команду напрямую.
    """
    import tools
    args = tools._pytest_args(Path("/x/pytest"), Path("/x/tests"))
    assert args[0] == "/x/pytest"
    assert args[1] == "/x/tests"
    assert args[2] == "-vv"
    assert args[4].startswith("--timeout=")
    assert "{_TEST_TIMEOUT}" not in args[4]
    assert args[4] == f"--timeout={tools._TEST_TIMEOUT}"
