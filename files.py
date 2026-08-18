"""files.py — запись файлов агентов с правами по ролям и извлечением из JSON-вывода."""
import datetime
import json
import os
import re
from pathlib import Path

from observability import log_event


def _safe_filename(name: str) -> str:
    """Безопасное имя файла: убирает путь-небезопасные символы ('/', пробелы и пр.).

    Роль может называться «UX/UI дизайнер» — без очистки слэш трактуется как
    вложенный каталог, и запись журнала падает FileNotFoundError (прогон
    20260813_211554: вывод дизайнера был потерян).
    """
    return re.sub(r"[^\w-]+", "_", name)


def _matches(rel: str, pattern: str) -> bool:
    """Путь rel подпадает под правило: каталог по префиксу, иначе имя фаила."""
    if pattern == "*":
        return True
    rel_l, pat_l = rel.lower(), pattern.lower()
    if pattern.endswith("/"):
        return rel_l == pat_l[:-1] or rel_l.startswith(pat_l)
    # Имя файла сравниваем без регистра: агент пишет "Dockerfile" по конвенции.
    return rel_l == pat_l or rel_l.split("/")[-1] == pat_l


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
