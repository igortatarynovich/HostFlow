from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
from typing import Optional

from fastapi import APIRouter

# --- Try to propagate DATABASE_URL for the docs module ---
# Priority:
#   1) already set in env
#   2) app.core.config.settings.SYNC_DATABASE_URL (most common in this project)
#   3) backend.app.core.config.settings.SYNC_DATABASE_URL (alt import path)
if not os.environ.get("DATABASE_URL"):
    sync_dsn: Optional[str] = None
    try:
        from backend.app.core.config import settings  # type: ignore

        sync_dsn = getattr(settings, "SYNC_DATABASE_URL", None)
    except Exception:
        try:
            from backend.app.core.config import (
                settings as backend_settings,  # type: ignore
            )

            sync_dsn = getattr(backend_settings, "SYNC_DATABASE_URL", None)
        except Exception:
            sync_dsn = os.environ.get("SYNC_DATABASE_URL")
    if sync_dsn:
        os.environ.setdefault("DATABASE_URL", sync_dsn)


def _load_inner_router() -> Optional[APIRouter]:
    """Load docs module router either as a package import or by file path.

    This avoids depending on `docs` being an installed Python package.
    """
    # 1) Try as a normal package import
    try:
        from docs.labs.docs_module.router import router as r  # type: ignore

        if isinstance(r, APIRouter):
            return r
    except Exception:
        pass

    # 2) Try loading by file path
    candidates = []
    # repo_root/backend/app/external_docs_router.py -> repo_root
    here = pathlib.Path(__file__).resolve()
    repo_root = here.parents[2]
    candidates.append(repo_root / "docs" / "labs" / "docs_module" / "router_db.py")
    # also try from current working dir (for dev runs)
    candidates.append(
        pathlib.Path.cwd() / "docs" / "labs" / "docs_module" / "router_db.py"
    )

    for path in candidates:
        if path.exists():
            spec = importlib.util.spec_from_file_location(
                "_docs_module_router_db", str(path)
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["_docs_module_router_db"] = mod
                spec.loader.exec_module(mod)
                r = getattr(mod, "router", None)
                if isinstance(r, APIRouter):
                    return r
    return None


# Top-level router exported to main.py
router = APIRouter(tags=["Documents"])

_inner_router = _load_inner_router()

if _inner_router is not None:
    # If the inner router already starts with "/db", mount at root.
    # Otherwise mount it under "/db" so the final path is /api/v1/db/...
    inner_prefix = getattr(_inner_router, "prefix", "") or ""
    mount_prefix = "" if inner_prefix.startswith("/db") else "/db"
    router.include_router(_inner_router, prefix=mount_prefix)

    @router.get("/db/health")
    def db_health_ok():
        return {
            "ok": True,
            "router": "docs",
            "inner_prefix": inner_prefix,
            "mounted_under": mount_prefix or "/",
        }
else:
    # Provide minimal endpoints only to keep UI from crashing and to signal status
    @router.get("/db/health")
    def db_health_missing():
        return {"ok": False, "router": "docs", "error": "inner_router_missing"}

    @router.get("/db/document-types")
    async def list_document_types_db():
        return []

    @router.get("/db/candidate/{candidate_id}/documents")
    async def list_candidate_documents_db(candidate_id: str):
        return []


# Small startup log (best-effort)
try:
    print(
        "[docs-router] mounted.",
        "inner_prefix=",
        getattr(_inner_router, "prefix", None),
        "exported=/db/*",
    )
except Exception:
    pass
