"""spec.py — ASSERT-NN: приоритеты, классификация падений, гейты спеки (G0/G1a)."""
import re
from pathlib import Path

from observability import log_event


ASSERT_RE = re.compile(r"ASSERT-(\d{1,3})")
# Объявление утверждения — только строка, начинающаяся с ASSERT-NN и
# двоеточия. Упоминание номера в середине абзаца утверждения не создаёт,
# иначе любая ссылка в тексте раздувала бы знаменатель покрытия.
# Маркеры списка, отступы и markdown-жирный шрифт допускаются.
ASSERT_DECL_RE = re.compile(
    r"\s*(?:[-*+]\s*|\d+[.)]\s*)?\**\s*ASSERT-(\d{1,3})\s*\**\s*(?:\[(P[012])\]\s*)?:")


def _assert_decls(spec: str) -> list[str]:
    """Все номера объявлений по порядку, включая повторы."""
    return [m.group(1).zfill(2) for line in (spec or "").splitlines()
            if (m := ASSERT_DECL_RE.match(line))]


def spec_asserts(spec: str) -> list[str]:
    """Уникальные номера утверждений спеки с сохранением порядка."""
    found: list[str] = []
    for num in _assert_decls(spec):
        if num not in found:
            found.append(num)
    return found


def assert_priorities(spec: str) -> dict[str, str]:
    """ASSERT-NN -> приоритет (P0/P1/P2, дефолт P1)."""
    prio: dict[str, str] = {}
    for line in (spec or "").splitlines():
        m = ASSERT_DECL_RE.match(line)
        if m:
            prio[m.group(1).zfill(2)] = m.group(2) or "P1"
    return prio


def _test_priority(docstring: str, priorities: dict[str, str]) -> str:
    """Приоритет теста: максимум приоритетов ASSERT-NN, на которые он ссылается."""
    refs = [n.zfill(2) for n in ASSERT_RE.findall(docstring or "")]
    if not refs:
        return "P1"
    for pp in ("P0", "P1", "P2"):
        if any(priorities.get(r, "P1") == pp for r in refs):
            return pp
    return "P1"


def _parse_failed_tests(summary: str) -> list[str]:
    """Имена упавших тестов из pytest-вывода (file::test_name)."""
    names: list[str] = []
    for line in summary.splitlines():
        m = re.search(r"FAILED\s+(\S+?::\S+)", line)
        if m:
            names.append(m.group(1))
    return names


def _classify_failures(failed: list[str], docs: dict[str, str],
                       priorities: dict[str, str]) -> dict[str, list[str]]:
    """Разложить упавшие тесты по приоритетам P0/P1/P2."""
    by_prio = {"P0": [], "P1": [], "P2": []}
    func_docs = {name.rsplit("::", 1)[-1]: doc for name, doc in docs.items()}
    for fname in failed:
        fn = fname.rsplit("::", 1)[-1]
        pp = _test_priority(func_docs.get(fn, ""), priorities)
        by_prio[pp].append(fname)
    return by_prio


def gate_g0_spec(spec: str) -> tuple[bool, list[str], list[str]]:
    """Гейт G0: спека содержит проверяемые утверждения.

    Смысл гейта — убрать класс споров «спека молчала» до того, как по спеке
    напишут тесты и код. Гейт проверяет форму (есть ли нумерованные
    утверждения и корректны ли номера), а не содержательную полноту —
    последнюю кодом не проверить, и честнее не делать вид.
    """
    MIN_ASSERTS = 8
    problems: list[str] = []
    nums = spec_asserts(spec)
    if len(nums) < MIN_ASSERTS:
        problems.append(f"утверждений ASSERT-NN: {len(nums)}, нужно не менее {MIN_ASSERTS}")
    # Повторы номеров делают ссылку из теста неоднозначной, а спор —
    # неразрешимым: арбитр не поймёт, на какое из требований смотреть.
    declared = _assert_decls(spec)
    dups = sorted({n for n in declared if declared.count(n) > 1})
    if dups:
        problems.append(f"повторяются номера: {', '.join(dups)}")
    if nums and sorted(nums) != [str(i).zfill(2) for i in range(1, len(nums) + 1)]:
        problems.append(f"номера не подряд с 01: {', '.join(sorted(nums))}")
    log_event({"event": "gate", "gate": "G0", "green": not problems,
               "asserts": len(nums), "problems": problems})
    print(f"\nГЕЙТ G0 (спека): {'ЗЕЛЁНЫЙ' if not problems else 'КРАСНЫЙ'}, "
          f"утверждений {len(nums)}")
    for p in problems:
        print(f"  — {p}")
    return not problems, problems, nums


def _test_docstrings(run_dir: Path) -> dict[str, str]:
    """{"файл::имя_теста": docstring} для всего run_dir/tests.

    Разбор через ast: regex по тексту нашёл бы ссылку ASSERT-NN в любом
    месте тела теста, а не только в его docstring.
    """
    import ast
    out: dict[str, str] = {}
    tests_dir = run_dir / "tests"
    if not tests_dir.exists():
        return out
    for path in sorted(tests_dir.rglob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name.startswith("test_"):
                rel = path.relative_to(run_dir).as_posix()
                out[f"{rel}::{node.name}"] = ast.get_docstring(node) or ""
    return out


def gate_g1a_traceability(run_dir: Path, spec: str, label: str = "G1a") -> dict:
    """Гейт G1a: сопоставить утверждения спеки и ссылки в тестах.

    Не блокирует прогон: единственный вердикт по-прежнему у pytest.
    Значение гейта двойное: метрика покрытия утверждений и список
    тестов без опоры в спеке, который получает арбитр: такой тест в споре
    с кодом проигрывает — правят его, а не код.
    """
    declared = spec_asserts(spec)
    docs = _test_docstrings(run_dir)
    covered: set[str] = set()
    unanchored: list[str] = []
    for name, doc in docs.items():
        refs = {n.zfill(2) for n in ASSERT_RE.findall(doc or "")}
        if refs:
            covered |= refs
        else:
            unanchored.append(name)
    result = {
        "spec_asserts": len(declared),
        "tests": len(docs),
        "covered": len(covered & set(declared)),
        "uncovered": sorted(set(declared) - covered),
        "unanchored": sorted(unanchored),
        "unknown_refs": sorted(covered - set(declared)),
    }
    result["ratio"] = (round(result["covered"] / len(declared), 3)
                       if declared else 0.0)
    log_event({"event": "gate", "gate": label, "green": None, **result})
    print(f"\nГЕЙТ {label} (связь со спекой): покрыто "
          f"{result['covered']}/{result['spec_asserts']} утверждений, "
          f"тестов без ссылки {len(result['unanchored'])} из {result['tests']}")
    if result["uncovered"]:
        print(f"  — не покрыты: {', '.join(result['uncovered'])}")
    if result["unknown_refs"]:
        print(f"  — ссылки на несуществующие утверждения: "
              f"{', '.join(result['unknown_refs'])}")
    return result


