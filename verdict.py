"""verdict.py — единый источник вердикта гейтов.

Все решения «зелёный/красный» и счётчик сравнения прогонов живут здесь,
а не разбросаны if-ами по main.py. Одна причина, почему гейт красный/зелёный.
"""
import re


def parse_counts(output: str) -> dict:
    """Вытащить числа из итоговой строки pytest.

    Ищет «8 failed, 22 passed in 0.41s» в любом порядке. Нули во всех полях —
    сигнал, что итоговой строки нет (тесты не собрались).
    """
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    for key, pat in (
        ("passed", r"(\d+) passed"),
        ("failed", r"(\d+) failed"),
        ("errors", r"(\d+) error"),
        ("skipped", r"(\d+) skipped"),
    ):
        found = re.findall(pat, output)
        if found:
            counts[key] = int(found[-1])
    return counts


def collection_failed(output: str) -> bool:
    """Сбор тестов упал (импорт/INTERNALERROR/«no tests ran») — провал, а не «0 проблем»."""
    low = output.lower()
    return any(m in low for m in (
        "interneerror", "modulenotfounderror", "no tests ran",
        "collected 0 items", "importerror",
    ))


def score(summary: str) -> tuple[int, int]:
    """Ключ сравнения двух прогонов pytest: МЕНЬШЕ — ЛУЧШЕ.

    Первичен рост пройденных, а не число проблем. При ошибках сбора pytest
    показывает пять errors вместо десятков незапущенных тестов, и по числу
    проблем переход 5 errors → 35 passed / 11 failed выглядел бы ухудшением.
    """
    c = parse_counts(summary)
    if collection_failed(summary) or (c["passed"] == 0 and c["failed"] == 0 and c["errors"] == 0):
        return 0, 1_000_000
    return -c["passed"], c["failed"] + c["errors"]


def errors_code_side(summary: str) -> bool:
    """Ошибки сбора ИЗ-ЗА КОДА, а не тестов: ImportError/AttributeError на app.*-модулях."""
    return bool(re.search(
        r"cannot import name .* from ['\"]app\.|AttributeError: <module ['\"]app\.",
        summary,
    ))


def judge(counts: dict, collection_broken: bool, p0_failing: list | None,
          strict_failed: int) -> bool:
    """Единое правило «зелёный» — вместо разбросанных if по main.py.

    - passed > 0: тесты реально собрались и прошли.
    - errors == 0: нет ошибок сбора/фикстур.
    - not collection_broken: сбор не упал (INTERNALERROR/ImportError).
    - severity-режим (p0_failing не None): нет P0-падений, P1/P2 не блокируют.
    - strict-режим (p0_failing is None): failed == 0 (всё зелёное).
    """
    if not (counts["passed"] > 0 and counts["errors"] == 0 and not collection_broken):
        return False
    if p0_failing is not None:
        return not p0_failing
    return strict_failed == 0

def cluster_failures(output: str) -> str:
    """Сгруппировать падения по типу ошибки — детерминированно, без LLM.

    Несколько падений с похожим сообщением = один корень. Возвращает сводку
    для разработчика (или пустую строку, если падений не распознано).
    """
    items = re.findall(r"FAILED\s+([\w./\-]+::\w+)\s+-\s+([^\n]+)", output)
    if not items:
        items = re.findall(r"([\w./\-]+::\w+)\s+-\s+([^\n]+)", output)
    groups: dict[str, list[str]] = {}
    for test, msg in items:
        norm = re.sub(r"[\'\"][^\'\"]*[\'\"]", "<X>", msg)  # значения в кавычках
        norm = re.sub(r"\d+", "<N>", norm)                       # числа
        key = norm.strip()[:90]
        groups.setdefault(key, []).append(test)
    if not groups:
        return ""
    lines = ["\n=== КЛАСТЕРЫ ПАДЕНИЙ (ищи общий корень) ==="]
    for msg, tests in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"[{len(tests)}] {msg}")
        for t in tests[:4]:
            lines.append(f"    - {t}")
    return "\n".join(lines) + "\n"

