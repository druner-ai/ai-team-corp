#!/usr/bin/env python3
"""
AI Team Corporation v2.0 — оркестратор AI-команды разработки.

Архитектор (GLM-5.2) → Разработчик (DeepSeek V4 Pro) + QA архитектуры (параллельно)
    → QA кода (Codestral 2508) → правки (макс 1 цикл) → DevOps (DeepSeek V4 Pro)

v2.0:
- output_pydantic (JSON) вместо regex markdown-парсинга
- _write_file_safe: единая функция записи с обработкой коллизий
- JSON-first extraction, regex-fallback

Использование:
    uv run python main.py "Создай REST API для блога..."
"""

import sys
import time
import os
import re
import json
import signal
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv("/home/deploy/hermes/data/.env")

from crewai import Crew, Process
from crewai.tasks.task_output import TaskOutput

from config import (MODELS, FALLBACK_MODEL, PHASE_MODEL_WEIGHTS, SOFT_BUDGET_USD,
                    HARD_BUDGET_USD, MAX_FIX_ATTEMPTS, MAX_CI_FIX_ATTEMPTS,
                    MAX_ARBITER_FIX_ATTEMPTS, TEST_TIMEOUT, OUTPUT_DIR, VERSION)
from agents import (architect, ux_designer, test_designer, developer, qa_gate,
                    devops, contract_arbiter, switch_to_fallback)
from tasks import (make_spec_task, make_spec_fix_task, make_baseline_tests_task,
                   make_design_task, make_impl_tasks, make_fix_task,
                   make_test_fix_task, make_phase_c_tasks, make_arbiter_task)
from observability import init_log, log_event

# ─── global state ─────────────────────────────────────────────

_all_outputs: list[tuple[str, str, str, dict]] = []  # (task_name, agent_role, raw_output, json_dict)
_written_files: dict[str, Path] = {}  # манифест всего, что записано на диск
_RUN_DIR: Path | None = None
_LAST_SEVERITY: dict = {}
_FIX_ATTEMPT: int = 0        # номер текущей попытки починки, 0 — вне цикла правок
_CHEAP_MODE: bool = False    # режим дешёвых моделей после soft-порога бюджета

# Соответствие имени задачи (name= в tasks.py) стадии и защите тестов.
# protect_tests=True означает: роль не имеет права писать в tests/**.
STAGE_BY_TASK: dict[str, tuple[str, bool]] = {
    "architecture": ("stage_00_arch", False),
    "spec_fix":     ("stage_00_arch_fix", False),
    "baseline_tests": ("stage_00_baseline", False),
    "design":       ("stage_01_design", False),
    "test_design":  ("stage_01_tests", False),
    "coding":       ("stage_02_dev", False),
    "review":       ("stage_03_qa", False),
    "fix":          ("stage_04_fix", True),
    "test_fix":     ("stage_04_testfix", False),
    "devops":       ("stage_05_devops", False),
    # Арбитр — единственная роль с правом менять tests/**, поэтому
    # protect_tests=False. Ограничение здесь не запрет, а проверка
    # неослабления после записи: tests_not_weakened.
    "arbitrate":    ("stage_06_arbiter", False),
}


def _refresh_prices() -> str:
    """Сверить цены моделей с прайсом OpenRouter. Возвращает источник цен.

    Цены в конфиге молча разошлись с реальными по всем ролям сразу, и так
    же молча исказили все 26 прошлых отчётов. Зависеть от вручную вбитой
    цифры без проверки нельзя: метрика, которая тихо врёт, хуже отсутствующей.
    При недоступности API остаются запасные цены, и это видно в журнале.
    """
    try:
        import httpx
        key = os.getenv("OPENROUTER_API_KEY")
        r = httpx.get("https://openrouter.ai/api/v1/models",
                      headers={"Authorization": f"Bearer {key}"}, timeout=20)
        r.raise_for_status()
        prices = {}
        for m in r.json().get("data", []):
            p = m.get("pricing") or {}
            if m.get("id") and p.get("prompt") is not None:
                prices[m["id"]] = (float(p["prompt"]) * 1e6,
                                   float(p.get("completion", 0)) * 1e6)
        changed = {}
        for role, cfg in MODELS.items():
            actual = prices.get(cfg["name"])
            if actual and tuple(round(x, 4) for x in actual) != tuple(cfg["price_per_1m"]):
                changed[role] = {"was": list(cfg["price_per_1m"]),
                                 "now": [round(x, 4) for x in actual]}
                cfg["price_per_1m"] = (round(actual[0], 4), round(actual[1], 4))
        if not prices:
            return "config"
        log_event({"event": "prices", "source": "openrouter", "changed": changed})
        if changed:
            for role, d in changed.items():
                print(f"  Цена {role}: {d['was']} → {d['now']} $/1M")
        return "openrouter"
    except Exception as e:
        log_event({"event": "prices", "source": "config", "error": f"{type(e).__name__}: {e}"})
        print(f"  Цены не сверены с OpenRouter ({type(e).__name__}), считаю по конфигу")
        return "config"


def _phase_cost(phase: str, tokens_in: int, tokens_out: int,
                cheap: bool = False) -> tuple[float, str]:
    """Стоимость фазы по фактическому составу моделей.

    Раньше было среднее арифметическое цен всех ролей на весь прогон: оно
    завышало вклад дешёвых ролей и занижало вклад дорогой. После разбиения
    на фазы состав моделей в фазе известен, и цена смешивается по его весам.
    Метод возвращается рядом с числом: ценнее честная оценка с пометкой о
    способе счёта, чем аккуратно выглядящее число неизвестной природы.
    """
    if not tokens_in and not tokens_out:
        return 0.0, "empty"
    if cheap:
        weights, method = {"fallback": 1.0}, "per_phase_fallback"
    else:
        # Точное имя фазы важнее первой буквы: у A1 и A2 разный состав
        # моделей, а срез phase[0] схлопнул бы обе в "A" с неверными весами.
        weights = (PHASE_MODEL_WEIGHTS.get(phase.upper())
                   or PHASE_MODEL_WEIGHTS.get(phase[0].upper()))  # B1, G2_1 → B
        if not weights:
            weights, method = {"developer": 1.0}, "per_phase_default"
        else:
            method = "per_phase_weights"
    cin = sum(w * MODELS[k]["price_per_1m"][0] for k, w in weights.items())
    cout = sum(w * MODELS[k]["price_per_1m"][1] for k, w in weights.items())
    return tokens_in / 1e6 * cin + tokens_out / 1e6 * cout, method


def _parse_pytest_counts(output: str) -> dict:
    """Вытащить числа из итоговой строки pytest.

    Ищет числа вида "8 failed, 22 passed in 0.41s" в любом порядке.
    Нули во всех полях — тоже сигнал: итоговой строки нет, тесты не собрались.
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


# ─── callback: захват вывода каждой задачи ────────────────────

def _phase(name: str, agents: list, tasks: list) -> tuple[str, dict]:
    """Выполнить фазу как отдельный Crew. Возвращает (текст результата, токены).

    Раньше был один kickoff из шести задач: между задачами нельзя было
    выполнить код, поэтому единственный настоящий гейт стоял после всех ролей,
    а его вердикт никто не видел. Задача fix выполнялась всегда, devops — тоже,
    включая прогоны с красными тестами.
    """
    log_event({"event": "phase_start", "phase": name, "tasks": [t.name for t in tasks]})
    print(f"\n{'═' * 54}\nФАЗА {name}: {', '.join(t.name or '?' for t in tasks)}\n{'═' * 54}")
    crew = Crew(agents=agents, tasks=tasks, process=Process.sequential,
                task_callback=on_task_complete, verbose=True)
    t0 = time.time()
    try:
        result = crew.kickoff()
        error = None
    except Exception as e:
        result, error = None, f"{type(e).__name__}: {e}"
        print(f"\n❌ Фаза {name} упала: {error}")
    usage = getattr(result, "token_usage", None)
    u = {
        "tokens_in": getattr(usage, "prompt_tokens", 0) or 0,
        "tokens_out": getattr(usage, "completion_tokens", 0) or 0,
    }
    u["cost"], u["cost_method"] = _phase_cost(name, u["tokens_in"], u["tokens_out"],
                                              cheap=_CHEAP_MODE)
    log_event({"event": "phase_end", "phase": name,
               "duration": round(time.time() - t0, 1), "error": error, **u})
    print(f"ФАЗА {name}: ${u['cost']:.4f} "
          f"({u['tokens_in']}/{u['tokens_out']} токенов, {u['cost_method']})")
    _status_append(_RUN_DIR, f"## Фаза {name}: ${u['cost']:.4f} "
                             f"({u['tokens_in']}/{u['tokens_out']} токенов)"
                             + (f" — ОШИБКА: {error}" if error else ""))
    return str(result or error or ""), u


# ─── STATUS.md — живой статус прогона (Ralph loop) ─────────────
# Короткие итерации держат на диске актуальный «план/статус», который
# следующие фазы читают вместо перечитывания всего накопленного контекста.
# fix/арбитр/D2 получают только хвост STATUS.md — сжатую сводку «что уже было».


def _status_append(run_dir: Path | None, text: str) -> None:
    """Дописать строку в живой STATUS.md прогона. Идемпотентно и безопасно."""
    if run_dir is None:
        return
    try:
        with (run_dir / "STATUS.md").open("a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
    except OSError:
        pass


def _status_context(run_dir: Path) -> str:
    """Хвост STATUS.md для инъекции в промпты правок (fix/арбитр/D2).

    Возвращает пустую строку, если статуса нет — тогда контекст не меняется.
    """
    sp = run_dir / "STATUS.md"
    if not sp.is_file():
        return ""
    text = sp.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return ""
    # Только хвост: полный журнал раздул бы промпт без пользы для решения.
    return "=== СТАТУС ПРОГОНА (что уже было сделано) ===\n" + text[-3000:] + "\n\n"


# ─── Cross-run память (Loop Engineering: Memory = источник правды) ──
# Каждый прогон в режиме --enhance читает историю проекта и дописывает в неё
# свой итог. Архитектор следующего прогона видит «что уже решали и как» —
# вместо того чтобы стартовать с нуля и повторять старые ошибки.

MEMORY_DIR = Path(__file__).resolve().parent / "memory"


def _memory_path(repo: str) -> Path:
    """Файл памяти проекта: memory/<owner>__<repo>.md."""
    return MEMORY_DIR / (repo.replace("/", "__") + ".md")


def _memory_read(repo: str) -> str:
    """Прочитать историю проекта для инъекции в промпт Архитектора."""
    p = _memory_path(repo)
    if not p.is_file():
        return ""
    text = p.read_text(encoding="utf-8", errors="ignore").strip()
    return text if text else ""


def _memory_append(repo: str, entry: str) -> None:
    """Дописать запись в память проекта."""
    p = _memory_path(repo)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")
    except OSError:
        pass


def _gate(name: str, run_dir: Path, spec: str = "") -> tuple[bool, str]:
    """Детерминированный гейт: pytest. Единственный источник вердикта.

    Если передан spec — вердикт по КРИТИЧНОСТИ (P0/P1/P2):
    green = 0 ошибок сбора И 0 падений P0 (P1/P2 не блокируют деплой).
    Без spec (G3, G_base) — строго «всё зелёное».
    """
    global _LAST_SEVERITY
    from tools import run_tests_quiet
    green, summary = run_tests_quiet(str(run_dir))
    counts = _parse_pytest_counts(summary)
    severity: dict = {}
    if spec:
        priorities = assert_priorities(spec)
        docs = _test_docstrings(run_dir)
        by_prio = _classify_failures(_parse_failed_tests(summary), docs, priorities)
        severity = {"p0_failing": by_prio["P0"], "p1_failing": by_prio["P1"],
                    "p2_failing": by_prio["P2"]}
        green = counts["errors"] == 0 and not by_prio["P0"]
        _LAST_SEVERITY = severity
    log_event({"event": "gate", "gate": name, "green": green, **counts, **severity})
    (run_dir / f"gate_{name}.txt").write_text(summary)
    verdict = "ЗЕЛЁНЫЙ" if green else "КРАСНЫЙ"
    if severity:
        if severity["p0_failing"]:
            verdict = "КРАСНЫЙ (P0)"
        elif severity["p1_failing"]:
            verdict = f"ЗЕЛЁНЫЙ (P1-ворнинги: {len(severity['p1_failing'])})"
        elif severity["p2_failing"]:
            verdict = f"ЗЕЛЁНЫЙ (P2-ворнинги: {len(severity['p2_failing'])})"
    _status_append(run_dir, f"## Гейт {name}: {verdict} — "
                            f"{counts['passed']} passed / {counts['failed']} failed / "
                            f"{counts['errors']} errors")
    print(f"\nГЕЙТ {name}: {verdict}")
    return green, summary


def _score(summary: str) -> tuple[int, int]:
    """Ключ сравнения двух прогонов pytest: МЕНЬШЕ — ЛУЧШЕ.

    Первичен рост пройденных, а не число проблем: при ошибках сбора
    pytest показывает пять errors вместо десятков незапущенных тестов, и по
    числу проблем переход 5 errors → 35 passed / 11 failed выглядел бы
    ухудшением и откатывал полезную правку.
    """
    c = _parse_pytest_counts(summary)
    return -c["passed"], c["failed"] + c["errors"]


def _errors_code_side(summary: str) -> bool:
    """Ошибки сбора ИЗ-ЗА КОДА, а не тестов: ImportError/AttributeError на app.*-модулях.

    Тест-дизайнер правит tests/ и бессилен, когда код не отдаёт ожидаемый экспорт
    (напр. get_redis_client лежит не в том модуле). Тогда чинить должен разработчик.
    """
    return bool(re.search(
        r"cannot import name .* from ['\"]app\.|AttributeError: <module ['\"]app\.",
        summary))


def _code_snapshot(run_dir: Path) -> dict[str, bytes]:
    """Снять копию кода и конфигов перед попыткой правки.

    tests/ и stage_*/ не входят: тесты — контракт и роли fix недоступны,
    stage_* — журнал прогона, его откатывать нельзя.
    """
    snap: dict[str, bytes] = {}
    for p in run_dir.rglob("*"):
        rel = p.relative_to(run_dir)
        head = rel.parts[0]
        if head == "tests" or head.startswith("stage_") or head == "__pycache__":
            continue
        if p.is_file() and p.suffix in {".py", ".ini", ".toml", ".cfg", ".txt", ".md"}:
            snap[str(rel)] = p.read_bytes()
    return snap


def _code_restore(run_dir: Path, snap: dict[str, bytes]) -> int:
    """Вернуть код к снимку: восстановить изменённое, удалить добавленное."""
    changed = 0
    for rel, data in snap.items():
        p = run_dir / rel
        if not p.is_file() or p.read_bytes() != data:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            changed += 1
    for p in list(run_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(run_dir)
        head = rel.parts[0]
        if head == "tests" or head.startswith("stage_") or head == "__pycache__":
            continue
        if p.suffix in {".py", ".ini", ".toml", ".cfg", ".txt", ".md"} and str(rel) not in snap:
            p.unlink()
            changed += 1
    return changed


def _tests_snapshot(run_dir: Path) -> dict[str, bytes]:
    """Снять копию тестов перед вызовом арбитра.

    Считаем только рабочее дерево run_dir/tests: обход всего run_dir
    захватил бы копии тестов в stage_*/ и удвоил счётчики.
    """
    tests_dir = run_dir / "tests"
    snap: dict[str, bytes] = {}
    if not tests_dir.exists():
        return snap
    for p in tests_dir.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        snap[str(p.relative_to(run_dir))] = p.read_bytes()
    return snap


def _test_counts(snap: dict[str, bytes]) -> tuple[int, int]:
    """Сколько в снимке тестовых функций и проверок."""
    funcs = asserts = 0
    for rel, data in snap.items():
        if not Path(rel).name.startswith("test_"):
            continue
        t = data.decode("utf-8", errors="ignore")
        funcs += len(re.findall(r"^\s*(?:async\s+)?def test_", t, re.M))
        asserts += len(re.findall(r"^\s*assert\b", t, re.M)) + t.count("pytest.raises")
    return funcs, asserts


def tests_not_weakened(before: dict[str, bytes],
                       after: dict[str, bytes]) -> tuple[bool, str]:
    """Проверка кодом, а не моделью: арбитр не ослабил контракт.

    Арбитру нужно право менять тест, иначе спор неразрешим. Но право
    менять тест — это и возможность сделать гейт зелёным, убрав проверки.
    Поэтому граница задана счётом, а не доверием к формулировке решения.
    """
    f0, a0 = _test_counts(before)
    f1, a1 = _test_counts(after)
    if f1 < f0:
        return False, f"число тестов уменьшилось: {f0} → {f1}"
    if a1 < a0 * 0.9:
        return False, f"число проверок упало более чем на 10%: {a0} → {a1}"
    for rel, data in after.items():
        t = data.decode("utf-8", errors="ignore")
        if "mark.skip" in t or "mark.xfail" in t:
            return False, f"появился skip/xfail-маркер в {rel}"
    return True, f"ок: тестов {f0} → {f1}, проверок {a0} → {a1}"


def _tests_restore(run_dir: Path, snap: dict[str, bytes]) -> int:
    """Вернуть тесты к снимку: откат отклонённой правки арбитра."""
    changed = 0
    for rel, data in snap.items():
        p = run_dir / rel
        if not p.is_file() or p.read_bytes() != data:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            changed += 1
    tests_dir = run_dir / "tests"
    if tests_dir.exists():
        for p in list(tests_dir.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            if str(p.relative_to(run_dir)) not in snap:
                p.unlink()
                changed += 1
    return changed


def gate_g3(run_dir: Path, spec: str = "") -> tuple[bool, list[str]]:
    """Гейт G3: упаковка не сломала тесты и CI не прячет падения.

    Раньше ci.yml уезжал в GitHub никем не проверенным: синтаксически битый
    workflow или шаг тестов с `|| true` обнаруживались только на стороне
    GitHub, а `|| true` не обнаруживался вовсе — CI становится зелёным всегда.
    """
    problems: list[str] = []
    ok, summary = _gate("G3_tests", run_dir, spec)
    if not ok:
        problems.append("упаковка сломала зелёные тесты")
    wf = run_dir / ".github" / "workflows" / "ci.yml"
    if not wf.exists():
        problems.append("нет .github/workflows/ci.yml")
    else:
        text = wf.read_text(errors="ignore")
        try:
            import yaml
            yaml.safe_load(text)
        except Exception as e:
            problems.append(f"ci.yml не разбирается: {type(e).__name__}")
        if "|| true" in text:
            problems.append("ci.yml прячет падение тестов через || true")
        if "continue-on-error: true" in text:
            problems.append("ci.yml прячет падение через continue-on-error")
        reqs = run_dir / "requirements-dev.txt"
        if (reqs.exists() and "pytest-playwright" in reqs.read_text(errors="ignore")
                and "playwright install" not in text):
            problems.append("pytest-playwright без шага playwright install")
    log_event({"event": "gate", "gate": "G3", "green": not problems,
               "problems": problems})
    print(f"\nГЕЙТ G3: {'ЗЕЛЁНЫЙ' if not problems else 'КРАСНЫЙ'}")
    for p in problems:
        print(f"  — {p}")
    return not problems, problems


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


def _safe_filename(name: str) -> str:
    """Безопасное имя файла: убирает путь-небезопасные символы ('/', пробелы и пр.).

    Роль может называться «UX/UI дизайнер» — без очистки слэш трактуется как
    вложенный каталог, и запись журнала падает FileNotFoundError (прогон
    20260813_211554: вывод дизайнера был потерян).
    """
    return re.sub(r"[^\w-]+", "_", name)


def on_task_complete(output: TaskOutput):
    """Callback — сохранить вывод и СРАЗУ материализовать файлы на диск.

    Ключевое свойство: следующая роль и гейты видят файлы предыдущей
    роли на диске, а не только в тексте контекста. Раньше вся раскладка
    шла после crew.kickoff(), и QA закономерно получал "No tests/ directory".

    Пишет в два места:
      1. stage_NN_*/  — неизменяемый журнал того, что выдала роль
      2. run_dir/     — рабочее дерево, в котором работает pytest
    """
    task_name = output.name or "unknown"
    agent_role = str(output.agent) if output.agent else "unknown"
    raw_output = str(output.raw) if output.raw else ""
    json_output = output.json_dict or {}

    idx = len(_all_outputs)
    _all_outputs.append((task_name, agent_role, raw_output, json_output))

    if _RUN_DIR is None:
        print("⚠️ on_task_complete: _RUN_DIR не выставлен, файлы не записаны")
        return

    stage_name, protect = STAGE_BY_TASK.get(
        task_name, (f"stage_xx_{task_name}", False)
    )
    # Fix вызывается в цикле: без номера попытки журнал второй попытки
    # затирал бы первую, и сравнить версии было бы нечем.
    if task_name == "fix" and _FIX_ATTEMPT:
        stage_name = f"{stage_name}_{_FIX_ATTEMPT}"

    # 1. Сырой вывод роли — всегда
    # Роль может содержать '/' (напр. "UX/UI дизайнер") — чистим путь-небезопасные
    # символы, иначе "task_01_UX/UI_дизайнер.md" трактуется как вложенный путь и
    # запись падает FileNotFoundError (прогон 20260813_211554: вывод дизайнера потерян).
    safe_role = _safe_filename(agent_role)
    task_file = _RUN_DIR / f"task_{idx:02d}_{safe_role}.md"
    task_file.write_text(
        f"# {agent_role}\n\n## Задача\n{task_name}\n\n## Результат\n\n{raw_output}"
    )
    _written_files[task_file.name] = task_file

    # 2. Журнал стадии — неизменяемая копия вывода роли.
    #    Нужна для сравнения версий и для проверки неослабления тестов.
    stage_dir = _RUN_DIR / stage_name
    stage_dir.mkdir(parents=True, exist_ok=True)
    _extract_files(raw_output, stage_dir, protect_tests=protect,
                   role=agent_role, json_dict=json_output)

    # 3. Рабочее дерево — то, что видят следующие роли и гейты
    written = _extract_files(raw_output, _RUN_DIR, protect_tests=protect,
                            role=agent_role, json_dict=json_output)
    _written_files.update(written)

    log_event({
        "event": "artifacts",
        "task": task_name,
        "role": agent_role,
        "stage": stage_name,
        "protect_tests": protect,
        "files": sorted(written.keys()),
        "raw_len": len(raw_output),
    })
    if written:
        print(f"   💾 {task_name}: записано {len(written)} файлов в {_RUN_DIR.name}/")


# ─── права записи по ролям ─────────────────────────────
# Раньше права были цепочкой if/elif по подстрокам в названии роли,
# и роль, не попавшая ни в одну ветку, получала полный доступ. Именно так
# Архитектор в прогонах 20260812_112451 и _134959 записал в корень мусорные
# файлы "[build-system]" и "@dataclass(frozen=True)" — обломки код-блоков из его
# markdown-документа. Теперь права — таблица, отсутствие роли в таблице значит
# запрет, а deny проверяется раньше allow.
WRITE_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "test designer": {"allow": ("tests/", "pytest.ini", "conftest.py"), "deny": ()},
    "арбитр":       {"allow": ("*",), "deny": ()},
    "разработ":     {"allow": ("*",), "deny": ("tests/",)},
    "devops":        {"allow": ("Dockerfile", "docker-compose.yml", "docker-compose.yaml",
                                ".dockerignore", ".github/", ".env.example", "README.md"),
                      "deny": ()},
    "архитектор":   {"allow": ("docs/", "SPEC.md", "ARCHITECTURE.md", "README.md"), "deny": ()},
    "дизайнер":     {"allow": ("static/", "design.md"), "deny": ("tests/", "backend/")},
    "qa":            {"allow": (), "deny": ("*",)},   # QA не пишет файлы вовсе
}


def _matches(rel: str, pattern: str) -> bool:
    """Путь rel подпадает под правило: каталог по префиксу, иначе имя фаила."""
    if pattern == "*":
        return True
    rel_l, pat_l = rel.lower(), pattern.lower()
    if pattern.endswith("/"):
        return rel_l == pat_l[:-1] or rel_l.startswith(pat_l)
    # Имя файла сравниваем без регистра: агент пишет "Dockerfile" по конвенции.
    return rel_l == pat_l or rel_l.split("/")[-1] == pat_l


def _write_allowed(role: str, rel: str) -> tuple[bool, str]:
    """Может ли роль записать по пути rel (относительному run_dir)."""
    role_lower = role.lower()
    rules = next((r for key, r in WRITE_RULES.items() if key in role_lower), None)
    if rules is None:
        return False, f"роль '{role}' не описана в WRITE_RULES"
    for pattern in rules["deny"]:
        if _matches(rel, pattern):
            return False, f"запрет '{pattern}' для роли '{role}'"
    for pattern in rules["allow"]:
        if _matches(rel, pattern):
            return True, ""
    return False, f"путь вне разрешённых для роли '{role}'"


def _write_file_safe(run_dir: Path, filepath: str, content: str, overwrite: bool = False, protect_tests: bool = False, role: str = "") -> Path | None:
    """Безопасно записать файл, обрабатывая коллизии имён и path traversal.

    Права роли берутся из WRITE_RULES. protect_tests сохранён как дополнительный
    запрет на tests/** для этапов fix и ci-fix независимо от роли.
    """
    # Нормализуем путь
    if filepath.startswith("path/to/"):
        filepath = filepath.replace("path/to/", "", 1)
    filepath = filepath.strip("`*\"'")

    # Path traversal guard — отклоняем абсолютные пути и выход за run_dir
    p = Path(filepath)
    if p.is_absolute():
        return None
    full_path = (run_dir / filepath).resolve()
    try:
        rel = str(full_path.relative_to(run_dir.resolve())).replace("\\", "/")
    except ValueError:
        return None

    # Права роли по таблице
    ok, reason = _write_allowed(role, rel)
    if not ok:
        print(f"Путь отклонён: {filepath} — {reason}")
        log_event({"event": "write_denied", "role": role, "path": rel, "reason": reason})
        return None

    # Защита тестов: этапы fix/ci-fix не меняют tests/** ни при какой роли
    if protect_tests and p.parts[0] in ("tests", "test"):
        log_event({"event": "write_denied", "role": role, "path": rel,
                   "reason": "protect_tests"})
        return None

    # Пропускаем директории
    if full_path.is_dir():
        return None
    # Файл уже существует
    if full_path.exists() and full_path.is_file():
        if overwrite:
            full_path.write_text(content)
            return full_path
        alt = str(full_path) + ".collision"
        Path(alt).write_text(content)
        return Path(alt)

    # Создаём родительские директории
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        # Какой-то из предков — файл. Переименовываем.
        for ancestor in full_path.parents:
            if ancestor.is_file():
                ancestor.rename(str(ancestor) + ".file")
                break
        full_path.parent.mkdir(parents=True, exist_ok=True)

    # Детерминированный guard: строка «ARBITER: …» в .py обязана быть #-комментарием.
    # Арбитр иногда пишет её без решётки — тогда файл не парсится и тесты не собираются.
    if filepath.endswith(".py") and content:
        _lines = content.split("\n")
        for _i, _ln in enumerate(_lines):
            _s = _ln.lstrip()
            if not _s:
                continue
            if _s.startswith("ARBITER") and not _s.startswith("#"):
                _pad = _ln[: len(_ln) - len(_s)]
                _lines[_i] = _pad + "# " + _s
                content = "\n".join(_lines)
            break
    full_path.write_text(content)
    return full_path


def _extract_files_json(raw_output: str, run_dir: Path, protect_tests: bool = False, role: str = "") -> dict[str, Path]:
    """Извлечь файлы из JSON-вывода (output_pydantic). Возвращает {} если не JSON.

    Поддерживает два формата:
    1. Чистый JSON в raw_output
    2. JSON, вложенный в markdown (после ## Результат)
    """
    saved = {}
    data = None

    # Пробуем прямой парсинг (чистый JSON)
    try:
        data = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError):
        pass

    # Если не получилось — ищем JSON в тексте
    if data is None:
        import re
        # Сначала пробуем после "## Результат" (если есть)
        result_marker = raw_output.find("## Результат")
        search_text = raw_output[result_marker:] if result_marker != -1 else raw_output

        # Ищем JSON-блок
        match = re.search(r'\{.*\}', search_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                # Пробуем найти следующий JSON-блок
                remaining = search_text[match.end():]
                match2 = re.search(r'\{.*\}', remaining, re.DOTALL)
                if match2:
                    try:
                        data = json.loads(match2.group())
                    except json.JSONDecodeError:
                        return saved
                else:
                    return saved

    if data is None:
        return saved

    files = data.get("files", [])
    if not isinstance(files, list):
        return saved

    for entry in files:
        if not isinstance(entry, dict):
            continue
        filepath = entry.get("path", "")
        content = entry.get("content", "")
        if not filepath or not content:
            continue
        result = _write_file_safe(run_dir, filepath, content, overwrite=True, protect_tests=protect_tests, role=role)
        if result:
            saved[filepath] = result

    return saved

def _extract_files(text: str, run_dir: Path, protect_tests: bool = False, role: str = "", json_dict: dict | None = None) -> dict[str, Path]:
    """Извлечь файлы: сначала пробуем json_dict (если есть), затем JSON в тексте, затем regex."""
    # 1. Если передан json_dict — используем его (самый надёжный источник)
    if json_dict and isinstance(json_dict, dict):
        files = json_dict.get("files", [])
        if isinstance(files, list):
            saved = {}
            for entry in files:
                if not isinstance(entry, dict):
                    continue
                filepath = entry.get("path", "")
                content = entry.get("content", "")
                if not filepath or not content:
                    continue
                result = _write_file_safe(run_dir, filepath, content, overwrite=True, protect_tests=protect_tests, role=role)
                if result:
                    saved[filepath] = result
            if saved:
                return saved

    # 2. Пробуем JSON в тексте
    saved = _extract_files_json(text, run_dir, protect_tests=protect_tests, role=role)
    if saved:
        return saved

    # Fallback: regex-парсинг markdown блоков
    saved = {}
    pattern = re.compile(
        r'```(?:python|dockerfile|yaml|yml|json|toml|env|markdown|md|text|sql|sh|bash)?\s+(\S+)\n(.*?)```',
        re.DOTALL
    )
    for match in pattern.finditer(text):
        filepath = match.group(1).strip()
        content = match.group(2).strip()

        # Пропускаем не-файловые метки
        skip_labels = {"python", "dockerfile", "yaml", "json", "markdown", "bash", "text", "sql", "sh"}
        if filepath in skip_labels:
            continue
        # Пропускаем однобуквенные имена и JSON-артефакты
        if len(filepath) <= 2 or filepath in "[]{}":
            continue
        # Пропускаем мусор: версии зависимостей, разделители, HTTP-статусы, box-drawing
        if any(c in filepath for c in (">=", "==", ">", "<")) or filepath in ("---", "..."):
            continue
        if filepath.startswith("HTTP/") or filepath.startswith("┌") or filepath.startswith("│") or filepath.startswith("└"):
            continue
        if filepath.endswith("/") or "┐" in filepath or "┘" in filepath:
            continue
        if not any(c.isalpha() for c in filepath.replace("/", "").replace(".", "").replace("-", "").replace("_", "")):
            continue
        if len(content) < 20:
            continue

        # ВАЖНО: regex-фоллбэк тоже обязан уважать whitelist роли и
        # защиту тестов. Раньше он их не передавал — дыра в защите:
        # стоило модели ответить не JSON, и fix-этап мог переписать tests/**.
        result = _write_file_safe(run_dir, filepath, content, overwrite=True,
                                  protect_tests=protect_tests, role=role)
        if result:
            saved[filepath] = result

    return saved


def save_all_artifacts(run_dir: Path) -> dict[str, Path]:
    """Вернуть манифест файлов, уже записанных колбэком.

    Раскладки здесь больше нет: всё пишется в on_task_complete сразу
    после каждой задачи. Копирование стадий в финальное дерево убрано:
    при инкрементальной записи порядок задаёт сам ход прогона, а права
    ролей не дают DevOps перебить код, а fix — тесты. Оттуда же раньше
    брались два conftest.py и файлы .collision.

    stage_NN_*/ остаются как журнал и в рабочее дерево не переносятся.
    """
    return dict(_written_files)


def save_report(run_dir: Path, metrics: dict, deploy_report: str = "") -> Path:
    """Сохранить финальный отчёт."""
    report_path = run_dir / "REPORT.md"

    # Собираем summary всех задач
    tasks_summary = ""
    for i, (task_name, agent_role, raw_output, json_dict) in enumerate(_all_outputs):
        preview = raw_output[:300] + "..." if len(raw_output) > 300 else raw_output
        tasks_summary += f"\n### Шаг {i+1}: {agent_role}\n{preview}\n"

    report = f"""# AI Team — Отчёт о выполнении

**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Версия:** {VERSION}

## Метрики

| Параметр | Значение |
|----------|----------|
| Время выполнения | {metrics['duration']:.1f} сек |
| Токенов (вход) | {metrics['tokens_in']:,} |
| Токенов (выход) | {metrics['tokens_out']:,} |
| Цена | ${metrics['cost']:.4f} |
| Модели | {metrics['models']} |
| Утверждений в спеке | {metrics.get('spec_asserts', 0)} |
| Покрыто тестами | {metrics.get('asserts_covered', 0)} ({metrics.get('asserts_ratio', 0):.0%}) |
| Тестов без ссылки на спеку | {metrics.get('tests_unanchored', 0)} |
| Статус | {metrics['status']} |

## Результаты по задачам
{tasks_summary}

{deploy_report}
"""
    report_path.write_text(report)
    return report_path


# ─── deploy & verify ─────────────────────────────────────────

def deploy_and_verify(run_dir: Path) -> str:
    """DevOps Phase 2: docker compose up, тесты, healthcheck, cleanup."""
    import subprocess
    import shutil
    import tempfile

    # Ищем docker-compose.yml среди сохранённых файлов
    compose_files = list(run_dir.rglob("docker-compose.yml")) + list(run_dir.rglob("docker-compose.yaml"))
    dockerfiles = list(run_dir.rglob("Dockerfile"))

    if not compose_files:
        return "⚠️ docker-compose.yml не найден — деплой пропущен."

    compose_path = compose_files[0]
    project_dir = compose_path.parent

    # Проверяем, что порты 8000, 5432, 6379 свободны
    for port in [8000, 5432, 6379]:
        r = subprocess.run(
            f"ss -tlnp | grep -q ':{port}'", shell=True,
            capture_output=True, timeout=5
        )
        if r.returncode == 0:
            return f"⚠️ Порт {port} занят — деплой пропущен."

    # Проверяем Docker
    r = subprocess.run("which docker 2>/dev/null", shell=True, capture_output=True)
    if r.returncode != 0:
        return "⚠️ Docker не установлен — деплой пропущен."

    report_lines = ["## 🚀 Деплой и верификация\n"]
    start = time.time()

    try:
        # Копируем .env.example → .env если нужно
        env_example = project_dir / ".env.example"
        env_file = project_dir / ".env"
        if env_example.exists() and not env_file.exists():
            shutil.copy(env_example, env_file)
            report_lines.append("📋 .env.example → .env (скопирован)\n")

        # 1. Запускаем сервисы
        report_lines.append("### 1. Запуск сервисов\n```")
        r = subprocess.run(
            "docker compose up -d --wait --wait-timeout 60",
            shell=True, cwd=str(project_dir),
            capture_output=True, text=True, timeout=120
        )
        report_lines.append(r.stdout.strip())
        if r.stderr.strip():
            report_lines.append(r.stderr.strip())
        report_lines.append("```")
        if r.returncode != 0:
            report_lines.append(f"\n❌ docker compose up failed (exit {r.returncode})")

            # Сохраняем логи контейнеров для диагностики
            logs = subprocess.run(
                "docker compose logs --tail 50 2>&1",
                shell=True, cwd=str(project_dir),
                capture_output=True, text=True, timeout=15
            )
            if logs.stdout.strip():
                report_lines.append("\n### 📋 Логи контейнера (последние 50 строк)\n```")
                report_lines.append(logs.stdout.strip()[:3000])
                report_lines.append("```")

            # Cleanup
            subprocess.run("docker compose down -v 2>/dev/null", shell=True,
                          cwd=str(project_dir), capture_output=True, timeout=30)
            return "\n".join(report_lines)

        # 2. Healthcheck
        time.sleep(5)
        report_lines.append("\n### 2. Healthcheck\n```")
        r = subprocess.run(
            "curl -sf http://localhost:8000/openapi.json | head -c 500",
            shell=True, capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            report_lines.append("✅ Сервис отвечает (OpenAPI JSON)")
            report_lines.append(r.stdout[:300])
        else:
            report_lines.append(f"❌ Сервис не отвечает: {r.stderr[:200]}")
        report_lines.append("```")

        # 3. Прогоняем тесты в контейнере
        report_lines.append("\n### 3. Тесты (pytest в контейнере)\n```")
        # Находим имя сервиса приложения (не db/redis/postgres)
        services = subprocess.run(
            "docker compose config --services 2>/dev/null",
            shell=True, cwd=str(project_dir),
            capture_output=True, text=True, timeout=10
        )
        app_service = None
        infra = {"db", "redis", "postgres", "postgresql", "cache", "broker"}
        for svc in services.stdout.strip().split("\n"):
            if svc and svc.lower() not in infra:
                app_service = svc
                break

        if app_service:
            container = subprocess.run(
                f"docker compose ps -q {app_service} 2>/dev/null",
                shell=True, cwd=str(project_dir),
                capture_output=True, text=True, timeout=10
            )
            app_container = container.stdout.strip()
        else:
            app_container = ""

        if app_container:
            r = subprocess.run(
                f"docker exec {app_container} pytest tests/ -v --tb=short 2>&1",
                shell=True, capture_output=True, text=True, timeout=120
            )
            output = r.stdout.strip()
            # Если тестов нет в контейнере — запускаем с хоста
            if "file or directory not found: tests/" in output or "no tests ran" in output.lower():
                report_lines.append("(тестов нет в контейнере — запускаю с хоста)")
                host_tests = (run_dir / "tests").exists()
                if host_tests:
                    r2 = subprocess.run(
                        f"cd {run_dir} && PYTHONPATH=. {sys.executable} -m pytest tests/ -v --tb=short 2>&1",
                        shell=True, capture_output=True, text=True, timeout=120
                    )
                    report_lines.append(r2.stdout.strip()[:2000])
                    if r2.stderr.strip():
                        report_lines.append("--- stderr ---")
                        report_lines.append(r2.stderr.strip()[:500])
                    test_passed = (r2.returncode == 0)
                else:
                    report_lines.append("⚠️ tests/ не найден ни в контейнере, ни на хосте")
                    test_passed = False
            else:
                report_lines.append(output[:2000])
                if r.stderr.strip():
                    report_lines.append("--- stderr ---")
                    report_lines.append(r.stderr.strip()[:500])
                test_passed = (r.returncode == 0)
        else:
            report_lines.append(f"⚠️ Контейнер приложения не найден (сервис: {app_service or '—'})")
            test_passed = False
        report_lines.append("```")

        duration = time.time() - start
        report_lines.append(f"\n⏱️ Деплой: {duration:.1f} сек | Тесты: {'✅' if test_passed else '❌'}")

        return "\n".join(report_lines)

    except subprocess.TimeoutExpired:
        return "\n".join(report_lines) + "\n❌ Таймаут деплоя (120 сек)"
    except Exception as e:
        return "\n".join(report_lines) + f"\n❌ Ошибка деплоя: {e}"
    finally:
        # Всегда чистим
        subprocess.run(
            "docker compose down -v 2>/dev/null",
            shell=True, cwd=str(project_dir),
            capture_output=True, timeout=30
        )


# ─── signal handler ────────────────────────────────────────────

def _signal_handler(signum, frame):
    print(f"\n⏹️ Сигнал {signum}. Завершение...")
    sys.exit(0)

signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


# ─── main ──────────────────────────────────────────────────────

def validate_task(task: str) -> str | None:
    if len(task.strip()) < 50:
        return "❌ Задача слишком короткая (мин. 50 символов)."
    return None


def _existing_code_summary(run_dir: Path, max_chars: int = 12000) -> str:
    """Краткое описание существующего кода: дерево файлов + ключевые файлы.

    Для enhance-режима: архитектор и разработчик должны видеть, что уже есть,
    чтобы проектировать/вносить ДЕЛЬТУ, а не переписывать проект с нуля.
    """
    skip_dirs = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}
    lines = ["=== ДЕРЕВО ФАЙЛОВ ==="]
    for root, dirs, files in os.walk(run_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel = os.path.relpath(root, run_dir)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > 2:
            continue
        lines.append("  " * depth + (os.path.basename(root) if rel != "." else ".") + "/")
        for f in sorted(files):
            lines.append("  " * (depth + 1) + f)
    key_ext = {".py", ".json", ".yml", ".yaml", ".toml", ".md", ".txt"}
    for root, dirs, files in os.walk(run_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in sorted(files):
            if not any(f.endswith(e) for e in key_ext):
                continue
            if "test" in f.lower():
                continue
            p = os.path.join(root, f)
            try:
                if os.path.getsize(p) > 20000:
                    continue
                content = open(p, errors="replace").read()[:1500]
            except OSError:
                continue
            lines.append(f"\n=== {os.path.relpath(p, run_dir)} ===")
            lines.append(content)
    return "\n".join(lines)[:max_chars]


def _has_tests(run_dir: Path) -> bool:
    """Есть ли в репо хотя бы один тест (tests/test_*.py)."""
    tests_dir = run_dir / "tests"
    return tests_dir.is_dir() and any(tests_dir.glob("test_*.py"))


def main():
    # --enhance <owner>/<repo>: доработка существующего проекта (не greenfield).
    enhance_repo = None
    args = sys.argv[1:]
    if args and args[0] == "--enhance":
        if len(args) < 2:
            print("Использование: --enhance <owner>/<repo> '<запрос на доработку>'")
            sys.exit(1)
        enhance_repo = args[1]
        args = args[2:]
    if args:
        task = " ".join(args)
    elif not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    else:
        print("Использование: uv run python main.py 'описание задачи...'")
        print("  или:          uv run python main.py --enhance <owner>/<repo> '<доработка>'")
        sys.exit(1)

    error = validate_task(task)
    if error:
        print(error)
        sys.exit(1)

    print(f"╔══════════════════════════════════════════╗")
    print(f"║    🏗️  AI Team Corporation v{VERSION}       ║")
    print(f"╠══════════════════════════════════════════╣")
    print(f"║  Архитектор:  {MODELS['architect']['name']}")
    print(f"║  Разработчик: {MODELS['developer']['name']}")
    print(f"║  QA Gate:     {MODELS['qa']['name']}")
    print(f"║  DevOps:      {MODELS['devops']['name']}")
    print(f"║  Бюджет:      дешёвые модели после ${SOFT_BUDGET_USD:.2f}, стоп на ${HARD_BUDGET_USD:.2f}")
    print(f"╚══════════════════════════════════════════╝")
    print(f"\n📋 Задача: {task[:200]}{'...' if len(task) > 200 else ''}\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(OUTPUT_DIR) / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    # ── Доработка существующего проекта: клонируем репо в run_dir ──
    if enhance_repo:
        import subprocess
        token = os.getenv("GITHUB_TOKEN", "")
        clone_url = f"https://druner-ai:{token}@github.com/{enhance_repo}.git"
        r = subprocess.run(["git", "clone", "--depth", "1", clone_url, str(run_dir)],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"❌ Не удалось склонировать {enhance_repo}: {r.stderr[:300]}")
            sys.exit(1)
        print(f"\n📦 Доработка существующего проекта: {enhance_repo}")

    # Колбэк пишет файлы сам — ему нужен каталог до kickoff.
    # Инструменты (run_tests) берут тот же каталог из окружения, не из промпта.
    global _RUN_DIR
    _RUN_DIR = run_dir
    os.environ["AI_TEAM_RUN_DIR"] = str(run_dir.resolve())
    init_log(run_dir)
    _status_append(run_dir, f"# STATUS прогона {timestamp}")
    _status_append(run_dir, f"Задача: {task[:300]}")
    _status_append(run_dir, f"Режим: {'enhance ' + enhance_repo if enhance_repo else 'greenfield'}")
    prices_source = _refresh_prices()
    log_event({
        "event": "run_start",
        "version": VERSION,
        "run_dir": str(run_dir.resolve()),
        "task": task[:2000],
        "models": {k: v["name"] for k, v in MODELS.items()},
        "prices": {k: list(v["price_per_1m"]) for k, v in MODELS.items()},
        "prices_source": prices_source,
        "soft_budget_usd": SOFT_BUDGET_USD,
        "hard_budget_usd": HARD_BUDGET_USD,
    })

    global _FIX_ATTEMPT, _CHEAP_MODE
    _CHEAP_MODE = False
    start_time = time.time()
    tokens_in = tokens_out = 0
    spent = 0.0

    def _accrue(u: dict) -> None:
        """Суммировать токены и стоимость всех фаз: usage приходит на каждый kickoff."""
        nonlocal tokens_in, tokens_out, spent
        tokens_in += u["tokens_in"]
        tokens_out += u["tokens_out"]
        spent += u.get("cost", 0.0)

    def _budget_stop(next_phase: str) -> bool:
        """Проверка бюджета между фазами. True — дальше не идём.

        Раньше лимит проверялся один раз после всей работы, когда деньги уже
        потрачены, и влиял только на пропуск деплоя.
        """
        nonlocal spent
        global _CHEAP_MODE
        if spent > HARD_BUDGET_USD:
            log_event({"event": "budget", "level": "hard", "spent": round(spent, 4),
                       "limit": HARD_BUDGET_USD, "next_phase": next_phase})
            print(f"\nБЮДЖЕТ ИСЧЕРПАН: потрачено ${spent:.4f} при жёстком лимите "
                  f"${HARD_BUDGET_USD:.2f}. Фаза {next_phase} не запускается, артефакты сохранены")
            return True
        if spent > SOFT_BUDGET_USD and not _CHEAP_MODE:
            _CHEAP_MODE = True
            roles = switch_to_fallback([architect, ux_designer, test_designer,
                                        developer, qa_gate, devops,
                                        contract_arbiter])
            log_event({"event": "budget", "level": "soft", "spent": round(spent, 4),
                       "limit": SOFT_BUDGET_USD, "next_phase": next_phase,
                       "fallback_model": FALLBACK_MODEL, "roles": roles})
            print(f"\nПОРОГ БЮДЖЕТА: потрачено ${spent:.4f} при мягком лимите "
                  f"${SOFT_BUDGET_USD:.2f}. Дальше все роли идут на {FALLBACK_MODEL}")
        return False

    # ── Фаза A: архитектура → тесты → код → неблокирующее ревю ──
    # Архитектура вынесена в свой kickoff ради гейта G0: пока все четыре
    # задачи шли одним Crew, проверить спеку до написания тестов было негде —
    # код между задачами одного Crew не выполняется.
    existing_code = _existing_code_summary(run_dir) if enhance_repo else ""
    memory = _memory_read(enhance_repo) if enhance_repo else ""

    # ── Доработка: если в репо нет тестов — команда пишет базовые ──
    if enhance_repo and not _has_tests(run_dir) and not _budget_stop("A0"):
        print("\n📝 В репо нет тестов — Test Designer пишет базовые тесты на текущее поведение")
        _, u = _phase("A0", [test_designer], [make_baseline_tests_task(existing_code)])
        _accrue(u)
        base_ok, base_summary = _gate("G_base", run_dir)
        print(f"Базовые тесты: {'✅ зелёные' if base_ok else '❌ ' + base_summary[-160:]}")

    spec, u = _phase("A1", [architect],
                     [make_spec_task(task, enhance=bool(enhance_repo),
                                     existing_code=existing_code, memory=memory)])
    _accrue(u)

    # ── Гейт G0: спека говорит проверяемыми утверждениями ──
    spec_ok, spec_problems, _ = gate_g0_spec(spec)
    spec_fixed = False
    if not spec_ok and not _budget_stop("A1f"):
        # Одна попытка довести спеку до проверяемого вида. Больше одного цикла
        # не делаем: гейт проверяет форму, а форма либо лечится с первого раза,
        # либо не лечится вовсе, а прогон должен идти дальше.
        spec2, u = _phase("A1f", [architect],
                          [make_spec_fix_task(spec, spec_problems)])
        _accrue(u)
        if spec2.strip():
            ok2, problems2, _ = gate_g0_spec(spec2)
            # Берём исправленную версию только если она не хуже исходной:
            # модель способна вернуть один раздел вместо всего документа.
            if len(spec_asserts(spec2)) >= len(spec_asserts(spec)):
                spec, spec_ok, spec_problems, spec_fixed = spec2, ok2, problems2, True
        log_event({"event": "gate", "gate": "G0_retry", "green": spec_ok,
                   "accepted": spec_fixed, "problems": spec_problems})

    # ── Фаза A1d: UX/UI дизайнер проектирует интерфейс по спеке ──
    design_md = ""
    if not _budget_stop("A1d"):
        _, u = _phase("A1d", [ux_designer],
                      [make_design_task(spec, enhance=bool(enhance_repo),
                                        existing_code=existing_code)])
        _accrue(u)
        dfile = run_dir / "design.md"
        if dfile.is_file():
            design_md = dfile.read_text(encoding="utf-8", errors="ignore")[:8000]

    # ── Фаза A2: тесты → код → неблокирующее ревю ──
    result_str, u = _phase("A2", [test_designer, developer, qa_gate],
                           make_impl_tasks(spec, enhance=bool(enhance_repo),
                                           existing_code=existing_code,
                                           design=design_md))
    _accrue(u)

    # ── Гейт G1: единственный источник вердикта ────────────────
    tests_green, tests_summary = _gate("G1", run_dir, spec)
    # Гейт G1a: связь тестов со спекой. Метрика, а не блокировка — вердикт
    # по-прежнему только у pytest.
    trace = gate_g1a_traceability(run_dir, spec)
    dispute = ""

    # ── Фаза B: цикл правок по реальному выводу pytest ─────────
    # Раньше fix выполнялся всегда и видел только статичные эвристики от
    # чужой задачи. Теперь он запускается только на красном гейте и получает
    # дословный вывод pytest плюс файлы из traceback.
    fix_attempts_used = 0
    budget_stopped = ""
    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        if tests_green:
            break
        if _budget_stop(f"B{attempt}"):
            budget_stopped = f"B{attempt}"
            break
        _FIX_ATTEMPT = attempt
        fix_attempts_used = attempt
        # Снимок до правки: без него попытка может ухудшить состояние
        # без возврата — в прогоне 20260812_134959 вторая попытка ввела
        # несуществующую зависимость и увела 35/11 в 18/14/14.
        before_score = _score(tests_summary)
        snap = _code_snapshot(run_dir)
        context = _fix_context(run_dir, tests_summary, fallback=result_str)
        counts = _parse_pytest_counts(tests_summary)
        if counts["errors"] > 0 and _errors_code_side(tests_summary):
            # Ошибки сбора ИЗ-ЗА КОДА (нет экспорта/функции в app.*) — чинит
            # разработчик: тест-дизайнер править tests/ бессилен.
            _, u = _phase(f"B{attempt}", [developer],
                          [make_fix_task(tests_summary, context, attempt)])
        elif counts["errors"] > 0:
            # Ошибки сбора в самих тестах (синтаксис, импорт тест-хелперов) — чинит
            # Test Designer (у него есть право править tests/).
            _, u = _phase(f"B{attempt}", [test_designer],
                          [make_test_fix_task(tests_summary, context, attempt)])
        else:
            _, u = _phase(f"B{attempt}", [developer],
                          [make_fix_task(tests_summary, context, attempt)])
        _accrue(u)
        tests_green, new_summary = _gate(f"G2_{attempt}", run_dir, spec)
        after_score = _score(new_summary)
        if not tests_green and after_score > before_score:
            # Стало хуже: меньше пройденных либо столько же, но больше проблем.
            n = _code_restore(run_dir, snap)
            log_event({"event": "fix_rolled_back", "attempt": attempt,
                       "before": {"passed": -before_score[0], "problems": before_score[1]},
                       "after": {"passed": -after_score[0], "problems": after_score[1]},
                       "files_restored": n})
            print(f"\nПОПЫТКА {attempt} ОТКАЧЕНА: было {-before_score[0]} пройдено "
                  f"при {before_score[1]} проблемах, стало {-after_score[0]} при "
                  f"{after_score[1]}; восстановлено файлов: {n}")
            break
        tests_summary = new_summary
        if not tests_green:
            # Спор с тестом разбирает арбитр контракта (P2.2), пока — фиксация факта.
            stage_dir = run_dir / f"stage_04_fix_{attempt}"
            for f in sorted(stage_dir.rglob("*")) if stage_dir.exists() else []:
                if f.is_file() and "DISPUTE:" in f.read_text(errors="ignore"):
                    dispute = str(f.relative_to(run_dir))
                    log_event({"event": "dispute_declared", "attempt": attempt,
                               "file": dispute})
                    print(f"\nРазработчик заявил спор с тестом: {dispute}")
                    break
    _FIX_ATTEMPT = 0

    # ── Фаза D: арбитр контракта ────────────────────────────────
    # Цикл правок исчерпан, а тесты красные. Раньше здесь прогон заканчивался:
    # тесты закрыты на запись на этапе fix, спека могла спорное поведение не
    # определять, и права принять решение не было ни у одной роли.
    arbiter_decision = ""
    arbiter_accepted: bool | None = None
    if not tests_green and not budget_stopped:
        if _budget_stop("D"):
            budget_stopped = "D"
        else:
            # Источник истины для арбитра — спека фазы A1: именно в ней
            # объявлены ASSERT-NN, на которые ссылаются тесты. Файл на диске
            # берём только если он не беднее утверждениями (арбитр прошлого
            # прогона мог дописать SPEC.md).
            arb_spec = spec
            for cand in ("SPEC.md", "ARCHITECTURE.md", "docs/ARCHITECTURE.md",
                         "docs/SPEC.md"):
                sp = run_dir / cand
                if sp.is_file():
                    text = sp.read_text(errors="ignore")
                    if len(spec_asserts(text)) >= len(spec_asserts(spec)):
                        arb_spec = text
                    break
            if not arb_spec.strip():
                arb_spec = result_str     # вывод фазы A2, если спека пуста
            tests_before = _tests_snapshot(run_dir)
            code_snap = _code_snapshot(run_dir)
            before_score = _score(tests_summary)
            context = _fix_context(run_dir, tests_summary, fallback=result_str)
            arb_out, u = _phase("D", [contract_arbiter],
                                [make_arbiter_task(tests_summary, context, arb_spec,
                                                   dispute,
                                                   trace["unanchored"])])
            _accrue(u)
            # Строгий формат вердикта: если арбитр не дал "ARBITER:" — один раз
            # напоминаем формат явно и повторяем вызов.
            if "ARBITER:" not in arb_out:
                arb_out, u = _phase("D", [contract_arbiter],
                                    [make_arbiter_task(tests_summary, context,
                                                       arb_spec, dispute,
                                                       trace["unanchored"],
                                                       remind_format=True)])
                _accrue(u)
            m = re.search(r"ARBITER:.{0,300}", arb_out)
            arbiter_decision = m.group(0).replace("\\n", " ").strip() if m else ""
            # Право менять тест — это и возможность сделать гейт зелёным, убрав
            # проверки. Границу ставит счёт, а не формулировка решения.
            ok_w, why = tests_not_weakened(tests_before, _tests_snapshot(run_dir))
            if not ok_w:
                arbiter_accepted = False
                n_t = _tests_restore(run_dir, tests_before)
                n_c = _code_restore(run_dir, code_snap)
                log_event({"event": "arbiter", "accepted": False, "reason": why,
                           "decision": arbiter_decision,
                           "tests_restored": n_t, "code_restored": n_c})
                print(f"\nПРАВКА АРБИТРА ОТКЛОНЕНА: {why}")
                print(f"  восстановлено: тестов {n_t}, файлов кода {n_c}")
            else:
                tests_green, new_summary = _gate("G2_arb", run_dir, spec)
                after_score = _score(new_summary)
                if not tests_green and after_score > before_score:
                    arbiter_accepted = False
                    n_t = _tests_restore(run_dir, tests_before)
                    n_c = _code_restore(run_dir, code_snap)
                    log_event({"event": "arbiter", "accepted": False,
                               "reason": "регресс после правки арбитра",
                               "decision": arbiter_decision,
                               "tests_restored": n_t, "code_restored": n_c})
                    print(f"\nПРАВКА АРБИТРА ОТКАЧЕНА: стало хуже "
                          f"({-before_score[0]} → {-after_score[0]} пройдено)")
                else:
                    tests_summary = new_summary
                    arbiter_accepted = True
                    log_event({"event": "arbiter", "accepted": True, "reason": why,
                               "decision": arbiter_decision,
                               "tests_green": tests_green})
                    print(f"\nРЕШЕНИЕ АРБИТРА: {arbiter_decision or '(без пометки ARBITER:)'}")
                    print(f"  контракт не ослаблен — {why}")

    # ── Фаза D2: доводка после арбитра ────────────────────────────
    # Арбитр мог отдать правку, которая сама не проходит тесты (пропущенный
    # import, pydantic v1). Даём разработчику ещё пару попыток починить КОД,
    # глядя на реальный вывод pytest, не трогая tests/.
    if not tests_green and not budget_stopped:
        for d2_attempt in range(1, MAX_ARBITER_FIX_ATTEMPTS + 1):
            if tests_green:
                break
            if _budget_stop(f"D2{d2_attempt}"):
                budget_stopped = f"D2{d2_attempt}"
                break
            d2_before = _score(tests_summary)
            d2_snap = _code_snapshot(run_dir)
            d2_ctx = _fix_context(run_dir, tests_summary, fallback=result_str)
            _, u = _phase(f"D2{d2_attempt}", [developer],
                          [make_fix_task(tests_summary, d2_ctx, d2_attempt)])
            _accrue(u)
            tests_green, new_summary = _gate(f"G2_arbfix{d2_attempt}", run_dir, spec)
            d2_after = _score(new_summary)
            if not tests_green and d2_after > d2_before:
                _code_restore(run_dir, d2_snap)
                print(f"ДОВОДКА D2-{d2_attempt} ОТКАЧЕНА (стало хуже) — откат, следующая попытка")
                continue
            tests_summary = new_summary
            if tests_green:
                print(f"ДОВОДКА D2-{d2_attempt}: тесты зелёные")

    # ── Фаза C: упаковка — только на зелёных тестах и в бюджете ───
    if tests_green and not budget_stopped and not _budget_stop("C"):
        _, u = _phase("C", [devops], make_phase_c_tasks())
        _accrue(u)
        # Гейт G3: упаковка не сломала тесты и CI не прячет падения.
        g3_ok, g3_problems = gate_g3(run_dir, spec)
        if g3_ok:
            status = "✅ Успешно"
        else:
            status = "❌ Гейт G3 не пройден"
            print("PR НЕ СОЗДАЁТСЯ: " + "; ".join(g3_problems))
    elif tests_green:
        budget_stopped = budget_stopped or "C"
        log_event({"event": "phase_skipped", "phase": "C", "reason": "budget_exceeded"})
        print("\nФаза C пропущена: бюджет исчерпан на зелёных тестах")
        status = "⚠️ Бюджет исчерпан, тесты зелёные"
    else:
        reason = "budget_exceeded" if budget_stopped else "gate_red"
        log_event({"event": "phase_skipped", "phase": "C", "reason": reason})
        print("\nФаза C пропущена: " + (
            "бюджет исчерпан до зелёных тестов" if budget_stopped
            else "тесты красные после всех попыток правок и разбора арбитра"))
        print("PR НЕ СОЗДАЁТСЯ")
        status = ("⚠️ Бюджет исчерпан, тесты красные" if budget_stopped
                  else "❌ Tests failed")

    duration = time.time() - start_time
    cost = spent

    # ── Артефакты ──────────────────────────────────────────────
    # Колбэк записал всё по ходу прогона. Повторное извлечение из result
    # убрано: result — вывод последней задачи, который колбэк уже
    # обработал с правильной ролью, а здесь роль была пустая — whitelist не работал.
    saved_files = save_all_artifacts(run_dir)
    (run_dir / "tests_output.txt").write_text(tests_summary)

    # ── Деплой и верификация (DevOps phase 2) ──────────────────
    # Деплой — локальная docker-работа без вызовов модели, поэтому жёсткий
    # лимит его не касается: при превышении прогон уже остановлен выше,
    # и до этого кода со статусом Успешно дело не доходит.
    deploy_report = ""
    if status == "✅ Успешно":
        deploy_report = deploy_and_verify(run_dir)

    # Пересчёт покрытия по финальному состоянию tests/: арбитр и цикл правок
    # могли добавить или переписать тесты после первого замера.
    trace_final = gate_g1a_traceability(run_dir, spec, label="G1a_final")

    metrics = {
        "duration": duration,
        "spec_asserts": trace_final["spec_asserts"],
        "asserts_covered": trace_final["covered"],
        "asserts_ratio": trace_final["ratio"],
        "tests_unanchored": len(trace_final["unanchored"]),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost,
        "models": ", ".join(f"{k}={v['name'].split('/')[1]}" for k, v in MODELS.items()),
        "status": status,
        "tests_green": tests_green,
    }

    report_path = save_report(run_dir, metrics, deploy_report)

    # ── Cross-run память: дописать итог прогона в память проекта ──
    if enhance_repo:
        entry = (
            f"## Прогон {timestamp}\n"
            f"- Задача: {task[:200]}\n"
            f"- Статус: {status}\n"
            f"- Тесты: {'зелёные' if tests_green else 'красные'} "
            f"({trace_final['covered']}/{trace_final['spec_asserts']} утверждений покрыто)\n"
        )
        if arbiter_decision:
            entry += f"- Арбитр: {arbiter_decision[:300]}\n"
        _memory_append(enhance_repo, entry)

    print(f"\n{'─' * 54}")
    print(f"📊 Метрики выполнения")
    print(f"{'─' * 54}")
    print(f"  Статус:         {status}")
    if _LAST_SEVERITY and not _LAST_SEVERITY.get("p0_failing"):
        warn = _LAST_SEVERITY.get("p1_failing", []) + _LAST_SEVERITY.get("p2_failing", [])
        if warn:
            print(f"  Некритичные падения (P1/P2): {len(warn)}")
    print(f"  Время:          {duration:.1f} сек")
    print(f"  Токенов вход:   {tokens_in:,}")
    print(f"  Токенов выход:  {tokens_out:,}")
    print(f"  Цена:           ${cost:.4f}")
    if cost > HARD_BUDGET_USD:
        print(f"  ЖЁСТКИЙ ЛИМИТ ПРЕВЫШЕН: ${cost:.4f} > ${HARD_BUDGET_USD:.2f}")
    elif cost > SOFT_BUDGET_USD:
        print(f"  МЯГКИЙ ЛИМИТ ПРЕВЫШЕН: ${cost:.4f} > ${SOFT_BUDGET_USD:.2f}")
    print(f"  Задач собрано:  {len(_all_outputs)}")
    print(f"  Артефактов:     {len(saved_files)} файлов")
    print(f"  Отчёт:          {report_path}")
    if saved_files:
        print(f"\n  📁 Сохранённые файлы:")
        for name, path in sorted(saved_files.items()):
            if not name.startswith("task_") and name != "REPORT.md":
                print(f"     {name}")

    # ── Создать Pull Request ────────────────────────────────────
    pr_url = None
    if status == "✅ Успешно":
        if enhance_repo:
            pr_url = create_enhance_pr(run_dir, enhance_repo, task, timestamp,
                                       metrics, deploy_report)
        else:
            pr_url = create_pr_from_run(run_dir, task, timestamp, metrics, deploy_report)

    log_event({
        "event": "run_end",
        "status": status,
        "duration": round(duration, 1),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": round(cost, 4),
        "cost_method": "sum_of_phase_costs",
        "cheap_mode": _CHEAP_MODE,
        "budget_stopped_at": budget_stopped or None,
        "tests_green": tests_green,
        "spec_asserts": trace_final["spec_asserts"],
        "asserts_covered": trace_final["covered"],
        "asserts_ratio": trace_final["ratio"],
        "tests_unanchored": len(trace_final["unanchored"]),
        "spec_gate_green": spec_ok,
        "spec_fixed": spec_fixed,
        "fix_attempts": fix_attempts_used,
        "dispute": dispute or None,
        "arbiter_called": arbiter_accepted is not None,
        "arbiter_accepted": arbiter_accepted,
        "arbiter_decision": arbiter_decision or None,
        "artifacts": len(saved_files),
        "pr_url": pr_url,
    })

    # ── Publish (CD): развернуть постоянно + выставить наружу ─────
    # Независимо от зелёного гейта (deploy-anyway): «потыкать почти рабочий
    # код» — отдельная цель от «код готов». Включается env AI_TEAM_PUBLISH=1,
    # слаг поддомена/репо — из AI_TEAM_PUBLISH_SLUG (иначе app-<timestamp>).
    if (os.getenv("AI_TEAM_PUBLISH", "").strip().lower() in {"1", "true", "yes", "on"}
            and status == "✅ Успешно"):
        from publish import publish_service, add_caddy_route, push_repo
        slug = (os.getenv("AI_TEAM_PUBLISH_SLUG", "") or f"app-{timestamp}").strip()
        pub_url = repo_url = pub_port = None
        print(f"\n{'─' * 54}\n🚀 PUBLISH (зелёный прогон): {slug}")
        try:
            pub = publish_service(run_dir, slug)
            print(pub["report"])
            pub_port = pub["port"]
            if pub_port:
                if add_caddy_route(slug, pub_port):
                    pub_url = f"https://{slug}.tochenyi.ru"
                    print(f"🔗 Опубликовано: {pub_url}")
                else:
                    print("⚠️ caddy-маршрут не добавлен (валидация не прошла)")
                repo_url = push_repo(slug, pub["dest"])
                if repo_url:
                    print(f"🐙 Репозиторий: {repo_url}")
        except Exception as e:
            print(f"⚠️ Publish упал: {e}")
        log_event({"event": "publish", "slug": slug, "port": pub_port,
                   "url": pub_url, "repo": repo_url})

        # Дописать ссылку на живой проект в отчёт (то, ради чего прогон запускался)
        if pub_url or repo_url:
            try:
                _extra = ["\n## 🚀 Опубликованный проект\n"]
                if repo_url:
                    _extra.append(f"- Репозиторий: {repo_url}")
                if pub_url:
                    _extra.append(f"- Работающий сервис: {pub_url}")
                with (run_dir / "REPORT.md").open("a", encoding="utf-8") as _f:
                    _f.write("\n".join(_extra) + "\n")
                print("📄 Ссылка на проект дописана в REPORT.md")
            except OSError:
                pass

    # ── CI fix loop: ждём CI, при падении — доработка ──────────
    if pr_url:
        ci_fix_loop(pr_url, run_dir, task, timestamp)


def _wait_for_ci_run(branch: str, timeout: int = 600) -> dict | None:
    """Ждать появления и завершения CI run для ветки. Возвращает run dict или None."""
    import requests

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None
    user = os.getenv("GITHUB_USER", "druner-ai")
    repo = os.getenv("GITHUB_REPO", "ai-team-corp")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{user}/{repo}"

    deadline = time.time() + timeout
    run_id = None

    # Фаза 1: ждём появления run для ветки (до 2 мин)
    while time.time() < deadline and run_id is None:
        try:
            r = requests.get(f"{api}/actions/runs?branch={branch}&per_page=5",
                             headers=headers, timeout=10)
            if r.status_code == 200:
                runs = r.json().get("workflow_runs", [])
                if runs:
                    run_id = runs[0]["id"]
                    print(f"  🔄 CI run {run_id} найден, статус: {runs[0]['status']}")
                    break
        except Exception:
            pass
        time.sleep(10)

    if run_id is None:
        print(f"  ⚠️ CI run для {branch} не появился за 2 мин")
        return None

    # Фаза 2: ждём завершения run
    while time.time() < deadline:
        try:
            r = requests.get(f"{api}/actions/runs/{run_id}", headers=headers, timeout=10)
            if r.status_code == 200:
                run = r.json()
                if run["status"] == "completed":
                    return run
        except Exception:
            pass
        time.sleep(15)

    print(f"  ⚠️ CI run {run_id} не завершился за {timeout} сек")
    return None


def _get_ci_failure_logs(run_id: int, max_chars: int = 6000) -> str:
    """Скачать логи failed-джобов CI run. Возвращает хвост лога (самое важное)."""
    import requests

    token = os.getenv("GITHUB_TOKEN")
    user = os.getenv("GITHUB_USER", "druner-ai")
    repo = os.getenv("GITHUB_REPO", "ai-team-corp")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{user}/{repo}"

    try:
        # Получаем джобы run-а
        r = requests.get(f"{api}/actions/runs/{run_id}/jobs", headers=headers, timeout=10)
        if r.status_code != 200:
            return ""
        failed_jobs = [j for j in r.json().get("jobs", []) if j.get("conclusion") == "failure"]
        if not failed_jobs:
            return ""

        # Берём лог первой failed-джобы
        job_id = failed_jobs[0]["id"]
        log_r = requests.get(f"{api}/actions/jobs/{job_id}/logs",
                             headers=headers, timeout=20, allow_redirects=True)
        if log_r.status_code != 200:
            return ""

        # Хвост лога — там ошибки
        return log_r.text[-max_chars:]
    except Exception:
        return ""


def _collect_traceback_context(output: str, run_dir: Path, fallback: str = "") -> str:
    """Собрать контекст для починки: файлы из traceback + весь tests/.

    Дешевле полной базы и точнее — убирает шум. Работает одинаково
    для вывода локального pytest и для логов CI: единая реализация вместо двух.

    Распознаёт два формата ссылок на файлы:
      File "path/to/file.py"   — традиционный traceback Python
      tests/test_x.py:55:      — короткий формат pytest
    """
    traceback_files = set()
    for match in re.finditer(r'File "([^"]+\.py)"', output):
        # Нормализация по диску, а не по шаблону префикса.
        # Старый split("/ai-team-corp/")[-1] ломался на реальных путях CI
        # (/home/runner/work/ai-team-corp/ai-team-corp/x.py → ai-team-corp/x.py),
        # поэтому починка по логам CI молча уходила в фоллбэк.
        parts = match.group(1).split("/")
        for i in range(len(parts)):
            cand = "/".join(parts[i:])
            if cand and (run_dir / cand).is_file():
                traceback_files.add(cand)
                break

    # Короткий формат pytest: без этого локальный вывод давал пустой контекст
    for match in re.finditer(r'^([\w./\-]+\.py):\d+', output, re.MULTILINE):
        traceback_files.add(match.group(1))
    for match in re.finditer(r'^(?:FAILED|ERROR) ([\w./\-]+\.py)', output, re.MULTILINE):
        traceback_files.add(match.group(1))

    file_contents = []
    seen = set()
    for tf in sorted(traceback_files):
        tf_path = run_dir / tf
        if not (tf_path.exists() and tf_path.is_file()):
            continue
        try:
            rel = str(tf_path.resolve().relative_to(run_dir.resolve()))
        except ValueError:
            continue
        if rel in seen:
            continue
        seen.add(rel)
        file_contents.append(f"### {rel}\n```python\n{tf_path.read_text()}\n```")

    # Весь tests/ — контракт, который не трогаем
    tests_dir = run_dir / "tests"
    if tests_dir.exists():
        for tf in sorted(tests_dir.rglob("*.py")):
            rel = str(tf.relative_to(run_dir))
            if rel in seen:
                continue
            seen.add(rel)
            file_contents.append(f"### {rel}\n```python\n{tf.read_text()}\n```")

    return "\n\n".join(file_contents) if file_contents else fallback[:2000]


def _limits_context() -> str:
    """Сводка лимитов прогона для промптов правок (агент должен знать границы)."""
    return (
        "=== ЛИМИТЫ ПРОГОНА ===\n"
        f"- Бюджет: мягкий ${SOFT_BUDGET_USD:.2f}, жёсткий ${HARD_BUDGET_USD:.2f}\n"
        f"- Попыток починки: {MAX_FIX_ATTEMPTS}, после арбитра: {MAX_ARBITER_FIX_ATTEMPTS}\n"
        f"- Таймаут теста: {TEST_TIMEOUT}с (зависший тест = красный гейт, не краш)\n\n"
    )


def _fix_context(run_dir: Path, output: str, fallback: str = "") -> str:
    """Контекст для правок: лимиты + статус прогона + файлы из traceback/tests.

    Loop Engineering: агент видит свои границы (лимиты), что уже сделано
    (STATUS.md) и конкретные файлы — вместо перечитывания всего контекста.
    """
    return (_limits_context() + _status_context(run_dir)
            + _collect_traceback_context(output, run_dir, fallback=fallback))


def _run_ci_fix(arch_doc: str, ci_logs: str, run_dir: Path) -> int:
    """Запустить Разработчика для исправления CI-ошибок. Возвращает кол-во новых файлов."""
    from crewai import Task, Crew, Process
    from output_models import CodeOutput

    context = _collect_traceback_context(ci_logs, run_dir, fallback=arch_doc)

    # Создаём fix-задачу с CI-логами и файлами из traceback
    fix_task = Task(
        description=f"""
        CI/CD пайплайн упал. Исправь код, чтобы тесты прошли.

        КОНТЕКСТ — файлы, упомянутые в traceback, и весь tests/:
        {context}

        ЛОГИ ОШИБОК CI (последние строки — самое важное):
        ```
        {ci_logs}
        ```

        ПРАВИЛА ДЛЯ ФИКСА:
        - Исправь ТОЛЬКО то, что падает в CI (логические ошибки, инициализация БД, фикстуры)
        - Верни ТОЛЬКО изменённые файлы (не всю базу)
        - В поле content первого файла добавь комментарий: что исправлено и почему
        - НЕ меняй архитектуру без крайней необходимости
        - Убедись, что conftest.py инициализирует БД для тестов (fixture, lifespan и т.д.)
        - КРИТИЧНО: тестовые файлы должны содержать РЕАЛЬНЫЙ КОД тестов, не только комментарии
        - КРИТИЧНО: каждый файл должен иметь правильное расширение и содержать валидный Python-код
        - КРИТИЧНО: НЕ изменяй тесты, НЕ добавляй новые тесты, НЕ удаляй существующие
        """,
        expected_output="JSON с полем files — изменённые файлы с исправлениями.",
        agent=developer,
        output_pydantic=CodeOutput,
    )

    crew = Crew(
        agents=[developer],
        tasks=[fix_task],
        process=Process.sequential,
        verbose=False,
    )

    try:
        result = crew.kickoff()
        # Извлекаем файлы: сериализуем pydantic в JSON, затем парсим
        result_str = ""
        if hasattr(result, "json_dict") and result.json_dict:
            result_str = json.dumps(result.json_dict, ensure_ascii=False)
        elif hasattr(result, "pydantic") and result.pydantic:
            result_str = result.pydantic.model_dump_json()
        else:
            result_str = str(result) if result else ""
        new_files = _extract_files(result_str, run_dir, protect_tests=True)
        return len(new_files)
    except Exception as e:
        print(f"  ⚠️ CI fix failed: {e}")
        return 0


def _push_fix_to_pr(branch: str, run_dir: Path) -> bool:
    """Запушить исправленные файлы в существующую ветку PR. True = успех."""
    import subprocess
    import shutil

    worktree_dir = Path(f"/tmp/ai-team-fix-{branch.split('/')[-1]}")
    try:
        r = subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), branch],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            return False

        code_files = [
            f for f in run_dir.rglob("*")
            if f.is_file()
            and not f.name.startswith("task_")
            and f.name != "REPORT.md"
            and f.name not in (".env", ".env.example", ".gitignore")
            and "__pycache__" not in str(f)
            and ".venv" not in str(f)
            and ".collision" not in f.suffix
        ]
        for src in code_files:
            rel = src.relative_to(run_dir)
            dst = worktree_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        subprocess.run(["git", "add", "-A"], cwd=str(worktree_dir), capture_output=True, timeout=10)
        r = subprocess.run(
            ["git", "commit", "-m", "fix: исправление ошибок CI"],
            cwd=str(worktree_dir), capture_output=True, text=True, timeout=10
        )
        if "nothing to commit" in r.stdout + r.stderr:
            return False

        r = subprocess.run(["git", "push"], cwd=str(worktree_dir),
                           capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False
    finally:
        subprocess.run(["git", "worktree", "remove", str(worktree_dir), "--force"],
                      capture_output=True, timeout=15)


def ci_fix_loop(pr_url: str, run_dir: Path, task: str, timestamp: str) -> None:
    """Ждать CI → при падении запускать доработку → пушить фикс → повторять."""
    branch = f"ai-team/{timestamp}"

    # Извлекаем архитектурный документ для контекста fix-задачи
    arch_doc = ""
    for name, role, raw, _ in _all_outputs:
        if "архитект" in role.lower():
            arch_doc = raw
            break

    for attempt in range(1, MAX_CI_FIX_ATTEMPTS + 1):
        print(f"\n⏳ Ожидание CI для {branch} (попытка {attempt}/{MAX_CI_FIX_ATTEMPTS})...")
        run = _wait_for_ci_run(branch, timeout=600)

        if run is None:
            print(f"  ⚠️ CI run не найден — feedback loop пропущен")
            return

        conclusion = run.get("conclusion")
        print(f"  CI результат: {conclusion}")

        if conclusion == "success":
            print(f"\n🎉 CI ЗЕЛЁНЫЙ! PR готов к ревью: {pr_url}")
            return

        if conclusion != "failure":
            print(f"  ⚠️ CI завершился со статусом {conclusion} — пропускаем")
            return

        # CI упал — получаем логи и запускаем фикс
        print(f"\n🔴 CI упал (попытка {attempt}). Получаю логи...")
        ci_logs = _get_ci_failure_logs(run["id"])
        if not ci_logs:
            print(f"  ⚠️ Не удалось получить логи CI")
            return

        print(f"  🔧 Запускаю Разработчика для исправления...")
        new_files = _run_ci_fix(arch_doc, ci_logs, run_dir)
        if new_files == 0:
            print(f"  ⚠️ Разработчик не внёс изменений — прекращаю loop")
            return

        print(f"  📦 Запушиваю фикс в {branch}...")
        if not _push_fix_to_pr(branch, run_dir):
            print(f"  ⚠️ Не удалось запушить фикс — прекращаю loop")
            return

        print(f"  ✅ Фикс запушен. Жду новый CI run...")
        time.sleep(10)  # даём GitHub время создать новый run

    print(f"\n⚠️ CI не стал зелёным за {MAX_CI_FIX_ATTEMPTS} попыток. PR требует ручного ревью: {pr_url}")


def create_pr_from_run(run_dir: Path, task: str, timestamp: str,
                       metrics: dict | None = None, deploy_report: str = "") -> str | None:
    """Создать ветку через git worktree, запушить код и открыть PR.

    Использует git worktree вместо stash — не трогает текущее состояние репо.
    Закрывает старые PR той же задачи (дедупликация).
    """
    import subprocess
    import shutil

    branch = f"ai-team/{timestamp}"
    title = task[:80] + ("..." if len(task) > 80 else "")
    worktree_dir = Path(f"/tmp/ai-team-wt-{timestamp}")

    # Собираем статистику
    metrics = metrics or {}
    code_lines = _count_code_lines(run_dir)
    file_list = _list_code_files(run_dir)
    test_status = "❌" if "❌" in deploy_report else ("✅" if deploy_report else "—")
    deploy_ok = "✅" if deploy_report and "❌" not in deploy_report else ("❌" if deploy_report else "—")

    # Закрываем старые PR для этой же задачи (дедупликация)
    _close_stale_prs(task)

    try:
        # 1. Создаём worktree от master (не трогает текущий checkout)
        r = subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(worktree_dir), "master"],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            print(f"\n⚠️ git worktree failed: {r.stderr[:200]}")
            return None

        # 2. Копируем сгенерированный код в worktree (только код, не отчёты)
        code_files = [
            f for f in run_dir.rglob("*")
            if f.is_file()
            and not f.name.startswith("task_")
            and f.name != "REPORT.md"
            and f.name not in (".env", ".env.example", ".gitignore")
            and "__pycache__" not in str(f)
            and ".venv" not in str(f)
            and ".collision" not in f.suffix  # пропускаем дубликаты-коллизии
        ]
        for src in code_files:
            rel = src.relative_to(run_dir)
            dst = worktree_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        # 3. Коммитим в worktree
        subprocess.run(["git", "add", "-A"], cwd=str(worktree_dir), capture_output=True, timeout=10)
        commit_msg = f"🤖 AI-команда: {title}"
        r = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=str(worktree_dir), capture_output=True, text=True, timeout=10
        )
        if "nothing to commit" in r.stdout + r.stderr:
            print(f"\n⚠️ Нет изменений для PR")
            return None

        # 4. Пушим
        push_result = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=str(worktree_dir), capture_output=True, text=True, timeout=30
        )
        if push_result.returncode != 0:
            print(f"\n⚠️ Push failed: {push_result.stderr[:200]}")

        # 5. Создаём PR с богатым описанием
        from gh_pr import create_pr
        body = f"""## 🤖 AI-команда

**Задача:** {task}

### 📊 Результаты

| Параметр | Значение |
|----------|----------|
| ⏱️ Время | {metrics.get('duration', 0):.1f} сек |
| 💰 Цена | ${metrics.get('cost', 0):.4f} |
| 📝 Токенов | {metrics.get('tokens_in', 0):,} → {metrics.get('tokens_out', 0):,} |
| 📁 Файлов | {len(file_list)} |
| 📄 Строк кода | {code_lines} |
| 🧪 Тесты | {test_status} |
| 🐳 Деплой | {deploy_ok} |

### 🏗️ Модели

{metrics.get('models', '—')}

### 📁 Сгенерированные файлы

{file_list}

---
*Ветка `{branch}` • Отчёт `{run_dir}/REPORT.md`*
"""
        pr_url = create_pr(branch, f"🤖 {title}", body)
        if pr_url:
            print(f"\n🔀 PR создан: {pr_url}")
        return pr_url

    except Exception as e:
        print(f"\n⚠️ Ошибка создания PR: {e}")
        return None
    finally:
        # Всегда чистим worktree
        subprocess.run(["git", "worktree", "remove", str(worktree_dir), "--force"],
                      capture_output=True, timeout=15)
        # Удаляем локальную ветку (remote остаётся для PR)
        subprocess.run(["git", "branch", "-D", branch], capture_output=True, timeout=10)


def create_enhance_pr(run_dir: Path, repo: str, task: str, timestamp: str,
                      metrics: dict | None = None, deploy_report: str = "") -> str | None:
    """Создать PR на ЦЕЛЕВОМ репо (enhance-режим): run_dir — это git-клон цели.

    В отличие от create_pr_from_run (worktree в ai-team-corp), здесь run_dir
    уже является клоном целевого репозитория. Коммитим изменения колбэка,
    пушим ветку и открываем PR на этот репозиторий.
    """
    import subprocess
    import requests

    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return None
    branch = f"ai-team/{timestamp}"
    title = task[:80] + ("..." if len(task) > 80 else "")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

    def _git(*args):
        return subprocess.run(["git", *args], cwd=str(run_dir),
                              capture_output=True, text=True, timeout=30)

    if not (run_dir / ".git").exists():
        print("⚠️ run_dir не git-клон — PR не создаётся")
        return None

    try:
        import shutil
        # Убираем артефакты пайплайна — в PR идёт только изменение кода.
        for name in ("REPORT.md", "run.jsonl", "SPEC.md", "tests_output.txt", "tests_full_output.txt"):
            (run_dir / name).unlink(missing_ok=True)
        for g in ("task_*.md", "gate_*.txt"):
            for p in run_dir.glob(g):
                p.unlink(missing_ok=True)
        for d in run_dir.glob("stage_*"):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)

        # git identity — иначе commit падает с "Please tell me who you are".
        _git("config", "user.name", "Andrei Tochenyi")
        _git("config", "user.email", "druner@gmail.com")

        r = _git("checkout", "-b", branch)
        if r.returncode != 0:
            _git("checkout", branch)
        _git("add", "-A")
        r = _git("commit", "-m", f"🤖 AI-команда: {title}")
        if "nothing to commit" in (r.stdout + r.stderr):
            print("⚠️ Нет изменений для PR")
            return None
        if r.returncode != 0:
            print(f"⚠️ Commit failed: {r.stderr[:200]}")
            return None

        r = _git("push", "-u", "origin", branch)
        if r.returncode != 0:
            print(f"⚠️ Push failed: {r.stderr[:200]}")
            return None

        r = requests.get(f"https://api.github.com/repos/{repo}", headers=headers, timeout=30)
        base = r.json().get("default_branch", "main") if r.status_code == 200 else "main"
        body = (
            "## 🤖 AI-команда — доработка\n\n"
            f"**Запрос:** {task}\n\n"
            f"**Время:** {(metrics or {}).get('duration', 0):.1f} сек | "
            f"**Цена:** ${(metrics or {}).get('cost', 0):.4f} | "
            f"**Тесты:** {'✅' if deploy_report and '❌' not in deploy_report else ('❌' if deploy_report else '—')}\n"
        )
        r = requests.post(f"https://api.github.com/repos/{repo}/pulls", headers=headers,
                          json={"title": f"🤖 {title}", "head": branch, "base": base,
                                "body": body}, timeout=30)
        if r.status_code == 201:
            url = r.json()["html_url"]
            print(f"\n🔀 PR создан: {url}")
            return url
        print(f"⚠️ PR creation failed: {r.status_code} — {r.text[:200]}")
        return None
    except Exception as e:
        print(f"⚠️ Ошибка создания PR: {e}")
        return None


def _close_stale_prs(task: str) -> None:
    """Закрыть открытые PR с тем же заголовком задачи (дедупликация)."""
    import os
    import requests

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return
    user = os.getenv("GITHUB_USER", "druner-ai")
    repo = os.getenv("GITHUB_REPO", "ai-team-corp")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{user}/{repo}"

    # Нормализуем задачу для сравнения (первые 60 символов без эмодзи)
    task_prefix = task[:60].strip().lower()

    try:
        r = requests.get(f"{api}/pulls?state=open&per_page=50", headers=headers, timeout=10)
        if r.status_code != 200:
            return
        for pr in r.json():
            pr_title = pr["title"].replace("🤖 ", "").strip().lower()
            # Если заголовок PR начинается с тех же 60 символов — это дубль
            if pr_title.startswith(task_prefix[:40]):
                pr_number = pr["number"]
                close_r = requests.patch(
                    f"{api}/pulls/{pr_number}",
                    headers=headers,
                    json={"state": "closed"},
                    timeout=10
                )
                if close_r.status_code == 200:
                    print(f"🔒 Закрыт дубль PR #{pr_number}: {pr['title'][:50]}")
                # Удаляем remote-ветку
                branch_name = pr["head"]["ref"]
                requests.delete(f"{api}/git/refs/heads/{branch_name}", headers=headers, timeout=10)
    except Exception:
        pass  # Не критично, продолжаем


def _count_code_lines(run_dir: Path) -> int:
    """Посчитать строки в сгенерированном коде."""
    total = 0
    for f in run_dir.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".js", ".ts", ".sql", ".yaml", ".yml", ".toml"):
            if "__pycache__" not in str(f) and ".venv" not in str(f):
                try:
                    total += len(f.read_text().splitlines())
                except Exception:
                    pass
    return total


def _list_code_files(run_dir: Path) -> str:
    """Список файлов для PR description."""
    files = []
    for f in sorted(run_dir.rglob("*")):
        if f.is_file() and not f.name.startswith("task_") and f.name != "REPORT.md":
            if "__pycache__" not in str(f) and ".venv" not in str(f):
                rel = f.relative_to(run_dir)
                ext = f.suffix.lstrip(".") or "file"
                files.append(f"`{rel}`")
    if not files:
        return "—"
    return "\n".join(files[:30]) + ("\n..." if len(files) > 30 else "")


if __name__ == "__main__":
    main()
