"""Тесты гейтов G0 (форма спеки) и G1a (связь тестов со спекой).

Проверяется именно то, что нельзя проверить рассуждением: что счётчик
утверждений не раздувается упоминаниями номеров в прозе, что повторы и
дырки в нумерации ловятся, и что тест без ссылки попадает в unanchored.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENROUTER_API_KEY", "test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


def _spec(n: int, start: int = 1) -> str:
    lines = ["# Спека", "", "## 8. Проверяемые утверждения", ""]
    for i in range(start, start + n):
        lines.append(f"- ASSERT-{i:02d}: система ДОЛЖНА отвечать 200 при корректном входе")
    return "\n".join(lines)


# ─── spec_asserts ───────────────────────────────────────────

def test_asserts_parsed_from_list_items():
    assert main.spec_asserts(_spec(8)) == [f"{i:02d}" for i in range(1, 9)]


def test_asserts_accept_markdown_bold_and_numbering():
    spec = "1. **ASSERT-01**: система ДОЛЖНА писать в stdout\n" \
           "  * ASSERT-02 : код возврата ДОЛЖЕН быть 2 при пустом вводе\n"
    assert main.spec_asserts(spec) == ["01", "02"]


def test_mention_in_prose_is_not_a_declaration():
    """Ссылка в середине абзаца не должна создавать утверждение."""
    spec = _spec(8) + "\n\nПодробнее см. ASSERT-99 и ASSERT-42 в разделе 3.\n"
    assert main.spec_asserts(spec) == [f"{i:02d}" for i in range(1, 9)]


def test_duplicate_declarations_counted_once_in_unique_list():
    spec = _spec(8) + "\n- ASSERT-03: повтор того же номера\n"
    assert len(main.spec_asserts(spec)) == 8


def test_empty_spec_gives_no_asserts():
    assert main.spec_asserts("") == []
    assert main.spec_asserts(None) == []


# ─── gate_g0_spec ───────────────────────────────────────────

def test_g0_green_on_eight_sequential_asserts():
    ok, problems, nums = main.gate_g0_spec(_spec(8))
    assert ok is True
    assert problems == []
    assert len(nums) == 8


def test_g0_red_when_too_few_asserts():
    ok, problems, nums = main.gate_g0_spec(_spec(5))
    assert ok is False
    assert len(nums) == 5
    assert any("не менее 8" in p for p in problems)


def test_g0_red_on_duplicate_numbers():
    spec = _spec(8) + "\n- ASSERT-03: то же самое другими словами\n"
    ok, problems, _ = main.gate_g0_spec(spec)
    assert ok is False
    assert any("повторяются номера: 03" in p for p in problems)


def test_g0_red_on_numbering_gap():
    """Нумерация с дыркой ломает ссылку из теста — гейт должен краснеть."""
    spec = _spec(4) + "\n" + "\n".join(
        f"- ASSERT-{i:02d}: требование" for i in range(7, 11))
    ok, problems, nums = main.gate_g0_spec(spec)
    assert len(nums) == 8
    assert ok is False
    assert any("не подряд" in p for p in problems)


def test_g0_red_on_empty_spec():
    ok, problems, nums = main.gate_g0_spec("")
    assert ok is False
    assert nums == []


def test_g0_does_not_judge_content():
    """Гейт проверяет форму: осмысленность утверждений кодом не проверить."""
    spec = "\n".join(f"- ASSERT-{i:02d}: чепуха" for i in range(1, 9))
    ok, _, _ = main.gate_g0_spec(spec)
    assert ok is True


# ─── _test_docstrings и gate_g1a_traceability ───────────────

def _mk_tests(tmp_path: Path, body: str, name: str = "test_a.py") -> Path:
    d = tmp_path / "tests"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(body)
    return tmp_path


def test_docstrings_collected_for_test_functions(tmp_path):
    run = _mk_tests(tmp_path, '''
def test_one():
    """ASSERT-01: про stdout"""
    assert True

def helper():
    """ASSERT-02: не тест"""

async def test_two():
    """ASSERT-02: про код возврата"""
    assert True
''')
    docs = main._test_docstrings(run)
    assert set(docs) == {"tests/test_a.py::test_one", "tests/test_a.py::test_two"}


def test_docstrings_survive_broken_file(tmp_path):
    """Битый синтаксис одного файла не должен ронять сбор по остальным."""
    run = _mk_tests(tmp_path, 'def test_ok():\n    """ASSERT-01: x"""\n    assert True\n')
    (run / "tests" / "test_broken.py").write_text("def test_(:\n")
    docs = main._test_docstrings(run)
    assert list(docs) == ["tests/test_a.py::test_ok"]


def test_phase_cost_separates_a1_and_a2():
    """Срез phase[0] схлопнул бы A1 и A2 в одни веса — цены должны различаться."""
    c1, m1 = main._phase_cost("A1", 1_000_000, 0)
    c2, m2 = main._phase_cost("A2", 1_000_000, 0)
    ca, _ = main._phase_cost("A", 1_000_000, 0)
    assert m1 == m2 == "per_phase_weights"
    assert c1 != c2
    assert c1 != ca and c2 != ca


def test_phase_cost_still_falls_back_to_first_letter():
    """Фазы вида B1/B2 по-прежнему берут веса базовой буквы."""
    cb1, m = main._phase_cost("B2", 1_000_000, 0)
    cb, _ = main._phase_cost("B", 1_000_000, 0)
    assert m == "per_phase_weights"
    assert cb1 == cb


def test_g1a_counts_covered_and_unanchored(tmp_path):
    run = _mk_tests(tmp_path, '''
def test_a():
    """ASSERT-01: про stdout"""
    assert True

def test_b():
    """ASSERT-02: про stderr"""
    assert True

def test_c():
    """без ссылки на спеку"""
    assert True
''')
    res = main.gate_g1a_traceability(run, _spec(8))
    assert res["spec_asserts"] == 8
    assert res["tests"] == 3
    assert res["covered"] == 2
    assert res["unanchored"] == ["tests/test_a.py::test_c"]
    assert res["uncovered"] == [f"{i:02d}" for i in range(3, 9)]
    assert res["ratio"] == 0.25


def test_g1a_reports_refs_to_missing_asserts(tmp_path):
    run = _mk_tests(tmp_path, '''
def test_a():
    """ASSERT-99: несуществующее требование"""
    assert True
''')
    res = main.gate_g1a_traceability(run, _spec(8))
    assert res["unknown_refs"] == ["99"]
    assert res["covered"] == 0


def test_g1a_ref_anywhere_in_docstring_counts(tmp_path):
    run = _mk_tests(tmp_path, '''
def test_a():
    """Проверяем рендер заголовка.

    Опирается на ASSERT-04 и ASSERT-05.
    """
    assert True
''')
    res = main.gate_g1a_traceability(run, _spec(8))
    assert res["covered"] == 2
    assert res["unanchored"] == []


def test_g1a_ref_in_body_does_not_count(tmp_path):
    """Ссылка комментарием в теле не считается: якорь — docstring."""
    run = _mk_tests(tmp_path, '''
def test_a():
    # ASSERT-01: тут ссылка не считается
    assert True
''')
    res = main.gate_g1a_traceability(run, _spec(8))
    assert res["covered"] == 0
    assert res["unanchored"] == ["tests/test_a.py::test_a"]


def test_g1a_no_tests_dir_is_zero_not_crash(tmp_path):
    res = main.gate_g1a_traceability(tmp_path, _spec(8))
    assert res["tests"] == 0
    assert res["covered"] == 0
    assert res["ratio"] == 0.0


def test_g1a_empty_spec_gives_zero_ratio(tmp_path):
    run = _mk_tests(tmp_path, 'def test_a():\n    """ASSERT-01: x"""\n    assert True\n')
    res = main.gate_g1a_traceability(run, "")
    assert res["spec_asserts"] == 0
    assert res["ratio"] == 0.0
    assert res["unknown_refs"] == ["01"]


def test_g1a_full_coverage_ratio_one(tmp_path):
    body = "\n".join(
        f'def test_{i}():\n    """ASSERT-{i:02d}: требование"""\n    assert True\n'
        for i in range(1, 9))
    run = _mk_tests(tmp_path, body)
    res = main.gate_g1a_traceability(run, _spec(8))
    assert res["covered"] == 8
    assert res["ratio"] == 1.0
    assert res["uncovered"] == []
