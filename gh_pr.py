#!/usr/bin/env python3
"""
Создать Pull Request из сгенерированного AI-командой кода.
Вызывается из main.py после успешной генерации.
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

TOKEN = os.getenv("GITHUB_TOKEN")
USER = os.getenv("GITHUB_USER", "druner-ai")
REPO = os.getenv("GITHUB_REPO", "ai-team-corp")
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
}
API = f"https://api.github.com/repos/{USER}/{REPO}"


def create_pr(branch: str, title: str, body: str, base: str = "master") -> str | None:
    """Создать Pull Request. Возвращает URL или None."""
    r = requests.post(
        f"{API}/pulls",
        headers=HEADERS,
        json={
            "title": title,
            "head": branch,
            "base": base,
            "body": body,
        },
    )
    if r.status_code == 201:
        return r.json()["html_url"]
    elif r.status_code == 422 and "pull request already exists" in r.text.lower():
        print(f"⚠️ PR уже существует для ветки {branch}")
        # Ищем существующий
        r2 = requests.get(f"{API}/pulls?head={USER}:{branch}&state=open", headers=HEADERS)
        if r2.status_code == 200 and r2.json():
            return r2.json()[0]["html_url"]
        return None
    else:
        print(f"❌ PR creation failed: {r.status_code} — {r.text[:200]}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gh_pr.py <branch> <title> [body]")
        sys.exit(1)

    branch = sys.argv[1]
    title = sys.argv[2]
    body = sys.argv[3] if len(sys.argv) > 3 else f"🤖 AI-команда: {title}"

    url = create_pr(branch, title, body)
    if url:
        print(f"✅ PR создан: {url}")
    else:
        sys.exit(1)
