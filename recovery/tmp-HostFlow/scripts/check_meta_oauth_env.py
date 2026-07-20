#!/usr/bin/env python3
"""
Проверить переменные окружения для Facebook Login (Meta OAuth) без запуска API и БД.

Читает backend/.env (и при наличии .env в корне репозитория), не перезаписывает уже
выставленные в shell переменные.

Запуск из корня репозитория:

  python3 scripts/check_meta_oauth_env.py
  make check-meta-oauth-env

Код выхода: 0 — redirect и credentials готовы; 1 — чего-то не хватает.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ENV = ROOT / "backend" / ".env"
ROOT_ENV = ROOT / ".env"


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val


def _redirect_uri() -> str | None:
    raw = (os.environ.get("META_LEADS_OAUTH_REDIRECT_URI") or "").strip()
    if raw:
        return raw.rstrip("/")
    base = (os.environ.get("FRONTEND_URL") or "").strip().rstrip("/")
    if not base:
        return None
    return f"{base}/app/settings/integrations/meta"


def main() -> int:
    _load_env_file(BACKEND_ENV)
    _load_env_file(ROOT_ENV)

    app_id = (os.environ.get("META_LEADS_APP_ID") or "").strip()
    secret = (os.environ.get("META_LEADS_SHARED_APP_SECRET") or "").strip()
    redirect = _redirect_uri()

    lines = [
        ("META_LEADS_APP_ID", bool(app_id), app_id[:6] + "…" if len(app_id) > 6 else app_id or "(empty)"),
        ("META_LEADS_SHARED_APP_SECRET", bool(secret), "***" if secret else "(empty)"),
        (
            "OAuth redirect",
            bool(redirect),
            redirect or "(set META_LEADS_OAUTH_REDIRECT_URI or FRONTEND_URL)",
        ),
    ]

    print("Meta OAuth / Facebook Login — deployment check\n")
    for label, ok, hint in lines:
        status = "OK" if ok else "MISSING"
        print(f"  [{status:7}] {label}: {hint}")

    if app_id and secret and redirect:
        print("\nAll required values are set. Restart the API if you just edited .env.")
        print("Add the redirect URL to the Meta app → Facebook Login → Valid OAuth Redirect URIs.")
        return 0

    print("\nFix the MISSING rows in backend/.env, then restart backend and re-run this script.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
