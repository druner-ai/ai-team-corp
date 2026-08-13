"""Publish stage (CD): развернуть собранное приложение постоянно и выставить наружу.

В отличие от deploy_and_verify (docker compose up → смоук → down -v), эта стадия
ОСТАВЛЯЕТ сервис работать и выводит его на публичный URL. Запускается НЕЗАВИСИМО
от зелёного гейта: «потыкать почти рабочий код» — отдельная цель от «код готов».

Слои:
  1. systemd-юнит (uvicorn) — постоянный процесс на 127.0.0.1:<свободный порт>
  2. nginx vhost (alfa-proxy) — <slug>.185.93.105.16.sslip.io → 127.0.0.1:<порт>
  3. GitHub — отдельный репозиторий druner-ai/<slug> (отдельная функция)
"""
import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

PUBLISH_ROOT = Path.home() / "published"
SYSTEMD_DIR = Path.home() / ".config" / "systemd" / "user"
_UV = shutil.which("uv") or "/home/deploy/.local/bin/uv"

NGINX_CONF = Path.home() / "bank-alfa" / "proxy" / "nginx.conf"
NGINX_CONTAINER = "alfa-proxy"
NGINX_ANCHOR = "# >>> alfa-hostname managed block"


def clean_slug(s: str) -> str:
    """Безопасное имя юнита/репозитория/поддомена: [a-z0-9-]."""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "app"


# Артефакты пайплайна, которые не должны попадать ни в деплой, ни в репозиторий.
_SKIP_NAMES = {
    ".venv", "__pycache__", ".git", ".pytest_cache",
    "run.jsonl", "REPORT.md", "SPEC.md", "tests_output.txt", "tests_full_output.txt",
}


def _skip(item: Path) -> bool:
    name = item.name
    if name in _SKIP_NAMES:
        return True
    if name.startswith(("stage_", "task_", "gate_", ".pytest")):
        return True
    return False


def copy_app(run_dir: Path, dest: Path) -> None:
    """Скопировать код приложения из run_dir в dest, без пайплайн-артефактов."""
    dest.mkdir(parents=True, exist_ok=True)
    for item in run_dir.iterdir():
        if _skip(item):
            continue
        if item.is_dir():
            shutil.copytree(item, dest / item.name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(item, dest / item.name)


def find_app_import(dest: Path) -> str:
    """Entrypoint FastAPI-приложения: 'backend.main:app' | 'app.main:app' | 'main:app'."""
    for rel, imp in (("backend/main.py", "backend.main:app"),
                     ("app/main.py", "app.main:app"),
                     ("main.py", "main:app")):
        p = dest / rel
        if p.is_file() and "fastapi" in p.read_text(errors="ignore").lower():
            return imp
    raise FileNotFoundError(
        "FastAPI entrypoint не найден (ожидал backend/main.py | app/main.py | main.py)")


def find_requirements(dest: Path) -> list[Path]:
    """Все requirements*.txt в дереве dest (как tools._find_req_files)."""
    found = []
    for f in sorted(dest.rglob("requirements*.txt")):
        parts = f.relative_to(dest).parts
        if any(p.startswith(("stage_", ".")) or p in {"node_modules", "__pycache__", ".git"}
               for p in parts[:-1]):
            continue
        found.append(f)
    return found


def free_port(start: int = 8020) -> int:
    """Первый свободный порт на 127.0.0.1, начиная с start."""
    for p in range(start, start + 200):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    raise RuntimeError("Нет свободного порта в диапазоне 8020–8220")


def publish_service(run_dir: Path, slug: str) -> dict:
    """Развернуть приложение постоянно через systemd.

    Возвращает dict: report (str), port (int|None), dest (Path|None), slug (str).
    """
    slug = clean_slug(slug)
    result = {"report": [], "port": None, "dest": None, "slug": slug}
    lines = [f"## 🚀 Publish: {slug}\n"]
    dest = PUBLISH_ROOT / slug
    if dest.exists():
        shutil.rmtree(dest)
    result["dest"] = dest

    # 0. Копия кода
    try:
        copy_app(run_dir, dest)
        import_path = find_app_import(dest)
        req_files = [f for f in find_requirements(dest) if "dev" not in f.name.lower()]
    except FileNotFoundError as e:
        result["report"] = "\n".join(lines) + f"\n❌ {e}"
        return result
    lines.append(f"entrypoint: {import_path} | requirements: "
                 f"{[str(f.relative_to(dest)) for f in req_files] or 'нет'}")

    # 1. Окружение
    lines.append("\n### 1. Окружение (uv venv + pip)\n```")
    r = subprocess.run([_UV, "venv", str(dest / ".venv")], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        result["report"] = "\n".join(lines) + f"\n❌ venv: {r.stderr[:300]}\n```"
        return result
    pip_cmd = [_UV, "pip", "install", "--python", str(dest / ".venv" / "bin" / "python"), "-q"]
    for rf in req_files:
        pip_cmd.extend(["-r", str(rf)])
    r = subprocess.run(pip_cmd, capture_output=True, text=True, timeout=300, cwd=str(dest))
    lines.append((r.stdout or "").strip()[-300:] or "(пусто)")
    lines.append("```")
    if r.returncode != 0:
        result["report"] = "\n".join(lines) + f"\n❌ pip install: {r.stderr[:300]}"
        return result

    # 2. systemd-юнит
    port = free_port()
    result["port"] = port
    lines.append(f"\n### 2. systemd-юнит (порт {port})\n```")
    unit = (
        "[Unit]\n"
        f"Description=Published: {slug}\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={dest}\n"
        f"ExecStart={dest}/.venv/bin/uvicorn {import_path} --host 127.0.0.1 --port {port}\n"
        "Restart=always\n"
        "RestartSec=5\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )
    SYSTEMD_DIR.mkdir(parents=True, exist_ok=True)
    (SYSTEMD_DIR / f"{slug}.service").write_text(unit)
    lines.append(f"{slug}.service → {import_path} :{port}")
    lines.append("```")

    r = subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, text=True, timeout=15)
    r = subprocess.run(["systemctl", "--user", "enable", "--now", f"{slug}.service"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        result["report"] = "\n".join(lines) + f"\n❌ systemd start: {r.stderr[:300]}"
        return result

    # 3. Healthcheck
    lines.append("\n### 3. Healthcheck\n```")
    time.sleep(3)
    ok = False
    for _ in range(6):
        r = subprocess.run(f"curl -sf -o /dev/null http://127.0.0.1:{port}/openapi.json",
                           shell=True, capture_output=True, timeout=10)
        if r.returncode == 0:
            ok = True
            break
        time.sleep(2)
    lines.append(f"{'✅' if ok else '❌'} http://127.0.0.1:{port}/openapi.json")
    lines.append("```")

    lines.append(f"\nПорт: {port} | Юнит: {slug}.service | Каталог: {dest}")
    result["report"] = "\n".join(lines)
    return result


# ─────────────────────────────────────────────────────────────────────────
# nginx vhost
# ─────────────────────────────────────────────────────────────────────────

def _vhost_block(slug: str, port: int) -> str:
    return (
        "    # ═══════════════════════════════════════════════\n"
        f"    # PUBLISHED: {slug}\n"
        "    # ═══════════════════════════════════════════════\n"
        "    server {\n"
        "        listen 80;\n"
        f"        server_name {slug}.185.93.105.16.sslip.io;\n"
        "\n"
        "        location / {\n"
        f"            proxy_pass http://127.0.0.1:{port};\n"
        "            proxy_http_version 1.1;\n"
        "            proxy_set_header Host $host;\n"
        "            proxy_set_header X-Real-IP $remote_addr;\n"
        "            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
        "            proxy_set_header X-Forwarded-Proto $scheme;\n"
        "            proxy_read_timeout 120s;\n"
        "        }\n"
        "    }\n"
    )


def _apply_vhost(conf: str, slug: str, port: int) -> str:
    """Идемпотентно вставить/обновить блок PUBLISHED:<slug> в тексте конфига."""
    block = _vhost_block(slug, port)
    pattern = re.compile(
        r"    # ═+\n    # PUBLISHED: " + re.escape(slug) + r".*?\n    \}\n\n?",
        re.DOTALL,
    )
    conf = pattern.sub("", conf)
    if NGINX_ANCHOR in conf:
        return conf.replace(NGINX_ANCHOR, block + "\n" + NGINX_ANCHOR)
    return conf + "\n" + block


def _nginx_validate(conf_text: str) -> bool:
    """nginx -t на копии в контейнере; живую конфигурацию не трогает."""
    import tempfile
    fd, tmp = tempfile.mkstemp(suffix=".conf")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(conf_text)
        r = subprocess.run(["sudo", "docker", "cp", tmp, f"{NGINX_CONTAINER}:/tmp/nginx-check.conf"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return False
        r = subprocess.run(["sudo", "docker", "exec", NGINX_CONTAINER,
                            "nginx", "-t", "-c", "/tmp/nginx-check.conf"],
                           capture_output=True, text=True, timeout=30)
        return "syntax is ok" in (r.stdout + r.stderr)
    finally:
        os.unlink(tmp)


def add_nginx_vhost(slug: str, port: int) -> bool:
    """Добавить vhost для <slug>.185.93.105.16.sslip.io → 127.0.0.1:<port> и перезагрузить nginx."""
    slug = clean_slug(slug)
    conf = NGINX_CONF.read_text(errors="replace")
    new_conf = _apply_vhost(conf, slug, port)
    if new_conf == conf:
        return True  # блок с тем же портом уже есть
    if not _nginx_validate(new_conf):
        return False
    NGINX_CONF.write_text(new_conf)
    r = subprocess.run(["sudo", "docker", "restart", NGINX_CONTAINER],
                       capture_output=True, text=True, timeout=60)
    return r.returncode == 0


def remove_nginx_vhost(slug: str) -> bool:
    """Убрать vhost PUBLISHED:<slug> и перезагрузить nginx."""
    slug = clean_slug(slug)
    conf = NGINX_CONF.read_text(errors="replace")
    pattern = re.compile(
        r"    # ═+\n    # PUBLISHED: " + re.escape(slug) + r".*?\n    \}\n\n?",
        re.DOTALL,
    )
    new_conf = pattern.sub("", conf)
    if new_conf == conf:
        return True
    if not _nginx_validate(new_conf):
        return False
    NGINX_CONF.write_text(new_conf)
    r = subprocess.run(["sudo", "docker", "restart", NGINX_CONTAINER],
                       capture_output=True, text=True, timeout=60)
    return r.returncode == 0


def push_repo(slug: str, dest: Path) -> str | None:
    """Создать отдельный GitHub-репозиторий druner-ai/<slug> и запушить код. Возвращает URL или None."""
    import requests

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None
    user = os.getenv("GITHUB_USER", "druner-ai")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    repo_full = f"{user}/{slug}"

    # 1. Создать репозиторий, если ещё нет
    r = requests.get(f"https://api.github.com/repos/{repo_full}", headers=headers, timeout=30)
    if r.status_code == 404:
        r = requests.post("https://api.github.com/user/repos", headers=headers,
                          json={"name": slug, "private": False, "auto_init": False,
                                "description": "Опубликовано AI-командой"}, timeout=30)
        if r.status_code not in (200, 201):
            return None
    elif r.status_code != 200:
        return None

    # 2. .gitignore — не пушить .venv/__pycache__ (venv создан на этапе деплоя)
    (dest / ".gitignore").write_text(".venv/\n__pycache__/\n*.pyc\n.pytest_cache/\n.DS_Store\n")

    # 3. git init + commit
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.name", "Andrei Tochenyi"],
                ["git", "config", "user.email", "druner@gmail.com"],
                ["git", "add", "-A"]):
        subprocess.run(cmd, cwd=str(dest), capture_output=True, timeout=15)
    subprocess.run(["git", "commit", "-q", "-m", f"🤖 AI-команда: {slug}"],
                   cwd=str(dest), capture_output=True, timeout=15)

    # 4. remote + push
    subprocess.run(["git", "remote", "add", "origin",
                    f"https://{user}:{token}@github.com/{repo_full}.git"],
                   cwd=str(dest), capture_output=True, timeout=15)
    subprocess.run(["git", "branch", "-M", "main"], cwd=str(dest), capture_output=True, timeout=15)
    r = subprocess.run(["git", "push", "-u", "origin", "main"],
                       cwd=str(dest), capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        return None
    return f"https://github.com/{repo_full}"
