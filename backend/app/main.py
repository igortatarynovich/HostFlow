from __future__ import annotations
import asyncio
import logging
from logging.config import dictConfig
import os
import importlib
import sys as _sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from databases import Database
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.formparsers import MultiPartParser
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path
from uuid import UUID
from sqlalchemy import create_engine

logger = logging.getLogger("backend.app.main")
try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
except Exception:  # pragma: no cover - optional dependency
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    def generate_latest(*_args, **_kwargs):  # type: ignore[override]
        return b"# Prometheus client not installed\n"

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except Exception:  # pragma: no cover - optional dependency
    Instrumentator = None  # type: ignore[assignment]

# Ensure absolute imports (backend.app.*) resolve even when running with PYTHONPATH=backend
current_pkg = _sys.modules.get("app")
if current_pkg is None:
    current_pkg = importlib.import_module("app")
_sys.modules.setdefault("backend", current_pkg)
_sys.modules.setdefault("backend.app", current_pkg)

from . import models as _models  # noqa: F401
from backend.app.db.base import Base
_sys.modules.setdefault("backend.app.models", _sys.modules.get("app.models", _models))

_DOCUMENTS_DISABLED = bool(int(os.environ.get("DOCUMENTS_DISABLED", "0")))

try:
    from backend.app.api.v1 import meta as meta_router  # meta_router.router
    from backend.app.api.v1 import health as health_router
    from backend.app.api.v1 import users as general_users_router
    from backend.app.api.v1 import analytics as analytics_router
    from backend.app.api.v1 import candidates_delete as candidate_delete_router
    from backend.app.api.v1 import catalogs as catalogs_router
    from backend.app.api.v1 import reminders_v2 as reminders_v2_router
    from backend.app.api.v1 import services as additional_services_router
    try:
        from backend.app.api.v1 import scanner as scanner_router
    except ImportError as _e:
        logger.warning("[startup] scanner module disabled (opencv/cv2 unavailable): %s", _e)
        scanner_router = None  # type: ignore[assignment]
    from backend.app.auth.router import router as auth_router
    from backend.app.auth.whoami import router as whoami_router
    from backend.app.auth.ensure_multitenancy import ensure_auth_multitenancy
    from backend.app.auth.ensure_seed import ensure_auth_seed
    from backend.app.core.settings import settings
    from app.modules.leads import webhook as meta_webhook
    from backend.app.modules.companies.router import router as companies_router
    from backend.app.modules.companies.ensure_schema import ensure_companies_schema
    from backend.app.modules.notifications.ensure_schema import ensure_notifications_schema
    from backend.app.services.ensure_reminders_schema import ensure_reminders_schema
    from backend.app.services.ensure_communications_schema import ensure_communications_schema
    from backend.app.services.ensure_funnels_schema import ensure_funnels_schema
    from backend.app.api.v1.vacancies.router import router as vacancies_router
    from backend.app.api.public import intake as public_intake_router
    try:
        from backend.app.api.public import scanner as public_scanner_router
    except ImportError as _e:
        logger.warning("[startup] public scanner module disabled (opencv/cv2 unavailable): %s", _e)
        public_scanner_router = None  # type: ignore[assignment]
    from backend.app.api.public import notifications as public_notifications_router
    from backend.app.api.public import client_portal as public_client_portal_router
    if not _DOCUMENTS_DISABLED:
        from backend.app.modules.documents.router import router as documents_db_router  # type: ignore[assignment]
        from backend.app.modules.documents.ensure_schema import ensure_documents_schema  # type: ignore[no-redef]
        from backend.app.api.v1.documents import router as documents_router  # type: ignore[assignment]
    else:
        documents_router = None  # type: ignore[assignment]
        documents_db_router = None  # type: ignore[assignment]
        def ensure_documents_schema(*args, **kwargs):  # type: ignore[no-redef]
            return None

    try:
        from . import models as _models  # noqa: F401
        if getattr(_models, 'Document', None) is None:
            logger.warning("[startup] documents module unavailable: model bindings missing")
    except Exception as exc:
        logger.warning("[startup] documents module unavailable: %s", exc)
    if not _DOCUMENTS_DISABLED:
        from backend.app.modules.candidate_children.ensure_schema import ensure_candidate_children_schema
    else:
        ensure_candidate_children_schema = lambda *args, **kwargs: None  # type: ignore
    from backend.app.modules.leads.ensure_schema import ensure_leads_schema
    if not _DOCUMENTS_DISABLED:
        from backend.app.api.v1.candidate_permits import router as candidate_permits_router
        from backend.app.api.v1.candidate_visas import router as candidate_visas_router
        from backend.app.api.v1.candidate_tasks import router as candidate_tasks_router
    from backend.app.api.v1.candidate_employments import router as candidate_employments_router
    from backend.app.api.v1.stages import router as stages_router
    from backend.app.api.v1.tenants.router import router as tenants_router
    from backend.app.api.v1.platform import tenants as platform_tenants_router
    from backend.app.api.v1.settings import leads as settings_leads_router
    from backend.app.api.v1.settings import team as settings_team_router
    from backend.app.api.v1.settings import billing as settings_billing_router
    from backend.app.api.v1.settings import email as settings_email_router
    from backend.app.api.v1.settings import communications as settings_communications_router
    from backend.app.api.v1.admin import users as admin_users_router
    from backend.app.api.v1.admin import companies_access as admin_companies_access_router
    from backend.app.api.v1.admin import audit as admin_audit_router
    from backend.app.api.v1.admin import draft_reminders as admin_draft_reminders_router
    from backend.app.api.v1.recruiters.router import router as recruiters_router
    from backend.app.api.v1.leads.router import router as leads_router
    from backend.app.api.v1.notifications import router as notifications_router
    from backend.app.api.v1.communications import router as communications_router
    from backend.app.api.v1.invoices.router import router as invoices_router
    from backend.app.api.v1 import document_policies as document_policies_router
    from backend.app.api.v1 import custom_fields as custom_fields_router
    from backend.app.api.v1 import candidate_profiles as candidate_profiles_router
    from backend.app.api.v1.candidate_stages import router as candidate_stages_router
    from backend.app.api.v1.funnels import router as funnels_router
    from backend.app.api.v1 import legal_documents as legal_documents_router
    from backend.app.api.v1 import contact_attempts as contact_attempts_router
    from backend.app.api.v1 import handoffs as handoffs_router
    from backend.app.api.v1 import onboarding as onboarding_router
except ModuleNotFoundError:  # pragma: no cover - backend package alias
    from .api.v1 import meta as meta_router  # type: ignore[no-redef]
    from .api.v1 import health as health_router  # type: ignore[no-redef]
    from .api.v1 import users as general_users_router  # type: ignore[no-redef]
    from .api.v1 import analytics as analytics_router  # type: ignore[no-redef]
    from .api.v1 import candidates_delete as candidate_delete_router  # type: ignore[no-redef]
    from .api.v1 import catalogs as catalogs_router  # type: ignore[no-redef]
    from .api.v1 import reminders_v2 as reminders_v2_router  # type: ignore[no-redef]
    from .api.v1 import services as additional_services_router  # type: ignore[no-redef]
    try:
        from .api.v1 import scanner as scanner_router  # type: ignore[no-redef]
    except ImportError as _e:
        logger.warning("[startup] scanner module disabled (opencv/cv2 unavailable): %s", _e)
        scanner_router = None  # type: ignore[assignment]
    from .auth.router import router as auth_router  # type: ignore[no-redef]
    from .auth.whoami import router as whoami_router  # type: ignore[no-redef]
    from .auth.ensure_multitenancy import ensure_auth_multitenancy  # type: ignore[no-redef]
    from .auth.ensure_seed import ensure_auth_seed  # type: ignore[no-redef]
    from .core.settings import settings  # type: ignore[no-redef]
    from .modules.leads import webhook as meta_webhook  # type: ignore[no-redef]
    from .modules.companies.router import router as companies_router  # type: ignore[no-redef]
    from .modules.companies.ensure_schema import ensure_companies_schema  # type: ignore[no-redef]
    from .modules.notifications.ensure_schema import ensure_notifications_schema  # type: ignore[no-redef]
    from .services.ensure_reminders_schema import ensure_reminders_schema  # type: ignore[no-redef]
    from .services.ensure_communications_schema import ensure_communications_schema  # type: ignore[no-redef]
    from .services.ensure_funnels_schema import ensure_funnels_schema  # type: ignore[no-redef]
    from .api.v1.vacancies.router import router as vacancies_router  # type: ignore[no-redef]
    from .api.public import intake as public_intake_router  # type: ignore[no-redef]
    try:
        from .api.public import scanner as public_scanner_router  # type: ignore[no-redef]
    except ImportError as _e:
        logger.warning("[startup] public scanner module disabled (opencv/cv2 unavailable): %s", _e)
        public_scanner_router = None  # type: ignore[assignment]
    from .api.public import notifications as public_notifications_router  # type: ignore[no-redef]
    from .api.public import client_portal as public_client_portal_router  # type: ignore[no-redef]
    if not _DOCUMENTS_DISABLED:
        from .modules.documents.router import router as documents_db_router  # type: ignore[no-redef]
        from .modules.documents.ensure_schema import ensure_documents_schema  # type: ignore[no-redef]
        from .api.v1.documents import router as documents_router  # type: ignore[no-redef]
    if not _DOCUMENTS_DISABLED:
        from .modules.candidate_children.ensure_schema import ensure_candidate_children_schema  # type: ignore[no-redef]
    else:
        ensure_candidate_children_schema = lambda *args, **kwargs: None  # type: ignore
    from .modules.leads.ensure_schema import ensure_leads_schema  # type: ignore[no-redef]
    if not _DOCUMENTS_DISABLED:
        from .api.v1.candidate_permits import router as candidate_permits_router  # type: ignore[no-redef]
        from .api.v1.candidate_visas import router as candidate_visas_router  # type: ignore[no-redef]
        from .api.v1.candidate_tasks import router as candidate_tasks_router  # type: ignore[no-redef]
    from .api.v1.candidate_employments import router as candidate_employments_router  # type: ignore[no-redef]
    from .api.v1.stages import router as stages_router  # type: ignore[no-redef]
    from .api.v1.tenants.router import router as tenants_router  # type: ignore[no-redef]
    from .api.v1.platform import tenants as platform_tenants_router  # type: ignore[no-redef]
    from .api.v1.settings import leads as settings_leads_router  # type: ignore[no-redef]
    from .api.v1.settings import team as settings_team_router  # type: ignore[no-redef]
    from .api.v1.settings import billing as settings_billing_router  # type: ignore[no-redef]
    from .api.v1.settings import email as settings_email_router  # type: ignore[no-redef]
    from .api.v1.settings import communications as settings_communications_router  # type: ignore[no-redef]
    from .api.v1.admin import users as admin_users_router  # type: ignore[no-redef]
    from .api.v1.admin import companies_access as admin_companies_access_router  # type: ignore[no-redef]
    from .api.v1.admin import audit as admin_audit_router  # type: ignore[no-redef]
    from .api.v1.admin import draft_reminders as admin_draft_reminders_router  # type: ignore[no-redef]
    from .api.v1.recruiters.router import router as recruiters_router  # type: ignore[no-redef]
    from .api.v1.leads.router import router as leads_router  # type: ignore[no-redef]
    from .api.v1.notifications import router as notifications_router  # type: ignore[no-redef]
    from .api.v1.communications import router as communications_router  # type: ignore[no-redef]
    from .api.v1.invoices.router import router as invoices_router  # type: ignore[no-redef]
    from .api.v1 import document_policies as document_policies_router  # type: ignore[no-redef]
    from .api.v1 import custom_fields as custom_fields_router  # type: ignore[no-redef]
    from .api.v1 import candidate_profiles as candidate_profiles_router  # type: ignore[no-redef]
    from .api.v1.candidate_stages import router as candidate_stages_router  # type: ignore[no-redef]
    from .api.v1.funnels import router as funnels_router  # type: ignore[no-redef]
    from .api.v1 import legal_documents as legal_documents_router  # type: ignore[no-redef]
    from .api.v1 import contact_attempts as contact_attempts_router  # type: ignore[no-redef]
    from .api.v1 import handoffs as handoffs_router  # type: ignore[no-redef]
    from .api.v1 import onboarding as onboarding_router  # type: ignore[no-redef]

try:
    from backend.app.services.communications_scheduler import (
        communications_scheduler_loop,
        scheduler_enabled as communications_scheduler_enabled,
    )
except Exception:
    try:
        from .services.communications_scheduler import (  # type: ignore[no-redef]
            communications_scheduler_loop,
            scheduler_enabled as communications_scheduler_enabled,
        )
    except Exception as _e:
        logger.warning("[startup] communications scheduler module disabled: %s", _e)

        async def communications_scheduler_loop(_stop_event):  # type: ignore[misc]
            return None

        def communications_scheduler_enabled() -> bool:  # type: ignore[misc]
            return False

# TODO: add FastAPI router for /api/v1/ping that returns {"ok": true}

if not _DOCUMENTS_DISABLED:
    from backend.app.modules.documents.storage import (
        register_document_upload,
        sanitize_filename,
    )
else:
    async def register_document_upload(  # type: ignore[misc]
        document_id: str,
        rel_path: str,
        *,
        original_name: Optional[str],
        size: int,
        mime: Optional[str],
        uploaded_by: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        raise RuntimeError("Document storage disabled in light mode")

    def sanitize_filename(name: Optional[str]) -> str:  # type: ignore[misc]
        return name or "document"

dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(levelname)s:%(name)s:%(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {  # базовый уровень для всего
        "level": "INFO",
        "handlers": ["console"],
    },
    "loggers": {
        # Наше приложение — подробные логи
        "backend.app": {"level": "DEBUG", "handlers": ["console"], "propagate": False},

        # Оставим uvicorn как есть
        "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn.error": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn.access": {"level": "INFO", "handlers": ["console"], "propagate": False},

        # Приглушим болтливых
        "aiosqlite": {"level": "WARNING"},
        "passlib": {"level": "WARNING"},
        "sqlalchemy.engine": {"level": "WARNING"},
        "sqlalchemy.pool": {"level": "WARNING"},
    },
})

# Ensure key models are fully imported and mapped before any routers load
try:
    try:
        from backend.app.models import Company, Vacancy, Candidate  # noqa: F401
    except ModuleNotFoundError:  # pragma: no cover
        from .models import Company, Vacancy, Candidate  # type: ignore[no-redef]
except Exception as e:
    logger.warning("[models] preload failed: %s", e)

# backend/app/main.py

_here = os.path.dirname(os.path.abspath(__file__))
_backend_root = os.path.abspath(os.path.join(_here, ".."))
_default_config_dir = os.path.abspath(os.path.join(_backend_root, "config"))
os.environ.setdefault("CONFIG_DIR", _default_config_dir)

_default_upload_dir = os.path.abspath(os.path.join(_backend_root, "uploads"))
os.environ.setdefault("UPLOAD_DIR", _default_upload_dir)

ALLOWED_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}

# Increase multipart upload limit to 10 MB (configurable via env override).
MULTIPART_MAX_FILE_SIZE = int(os.environ.get("UPLOAD_MAX_FILE_SIZE", 10 * 1024 * 1024))
MultiPartParser.max_file_size = MULTIPART_MAX_FILE_SIZE


class ForceCORSHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        try:
            response = await call_next(request)
        except Exception as e:
            import sys
            import traceback

            traceback.print_exc(file=sys.stderr)
            err_msg = str(e) if os.environ.get("DEBUG_500") else "Internal Server Error"
            response = JSONResponse(
                {"detail": err_msg}, status_code=500
            )
        if origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            vary = response.headers.get("Vary")
            response.headers["Vary"] = f"{vary}, Origin" if vary else "Origin"
        return response


def _run_alembic_upgrade_head(sync_url: str) -> None:
    try:
        from alembic import command
        from alembic.config import Config

        backend_dir = _backend_root
        alembic_ini = os.path.join(backend_dir, "alembic.ini")
        script_location = os.path.join(backend_dir, "alembic")

        cfg = Config(alembic_ini if os.path.exists(alembic_ini) else None)
        cfg.set_main_option("script_location", script_location)
        cfg.set_main_option("sqlalchemy.url", sync_url)

        logger.info("[alembic] upgrade head (script_location=%s) on %s", script_location, sync_url)
        try:
            command.upgrade(cfg, "head")
        except Exception as exc:
            msg = str(exc)
            if "Multiple head revisions are present" in msg:
                logger.warning("[alembic] multiple heads detected, upgrading all heads (%s)", msg)
                command.upgrade(cfg, "heads")
            else:
                raise
    except Exception as e:
        logger.warning("[alembic] skipped (reason: %s)", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_stop_event: asyncio.Event | None = None
    scheduler_task: asyncio.Task | None = None
    if settings.SYNC_DATABASE_URL.startswith("sqlite"):
        _run_alembic_upgrade_head(settings.SYNC_DATABASE_URL)
        try:
            sync_engine = create_engine(settings.SYNC_DATABASE_URL, future=True)
            Base.metadata.create_all(sync_engine)
            logger.info("[startup:create_all] ensured Base metadata on sqlite")
            sync_engine.dispose()
        except Exception as e:
            logger.warning("[startup:create_all] skipped (%s)", e)

    # --- init async Database and expose via app.state.db ---
    # Note: This is optional - we use SQLAlchemy async_session_maker for actual DB operations
    try:
        if not hasattr(app.state, "db") or getattr(app.state, "db", None) is None:
            db = Database(settings.ASYNC_DATABASE_URL)
            await db.connect()
            app.state.db = db
            logger.info("[db] connected and exposed via app.state.db (%s)", settings.ASYNC_DATABASE_URL)
        else:
            logger.info("[db] app.state.db already initialized, skipping connect")
    except Exception as e:
        logger.warning("[db] connect failed (non-critical, using SQLAlchemy instead): %s", e)
        # Don't raise - we use SQLAlchemy async_session_maker for actual DB operations
        app.state.db = None

    try:
        ensure_companies_schema()
    except Exception as e:
        logger.warning("[startup:ensure_companies_schema] skipped (%s)", e)

    try:
        ensure_documents_schema()
    except Exception as e:
        logger.warning("[startup:ensure_documents_schema] skipped (%s)", e)

    try:
        ensure_candidate_children_schema()
    except Exception as e:
        logger.warning("[startup:ensure_candidate_children_schema] skipped (%s)", e)

    try:
        ensure_leads_schema()
    except Exception as e:
        logger.warning("[startup:ensure_leads_schema] skipped (%s)", e)

    try:
        ensure_notifications_schema()
    except Exception as e:
        logger.warning("[startup:ensure_notifications_schema] skipped (%s)", e)

    try:
        ensure_reminders_schema()
    except Exception as e:
        logger.warning("[startup:ensure_reminders_schema] skipped (%s)", e)

    try:
        ensure_communications_schema()
    except Exception as e:
        logger.warning("[startup:ensure_communications_schema] skipped (%s)", e)

    try:
        ensure_funnels_schema()
    except Exception as e:
        logger.warning("[startup:ensure_funnels_schema] skipped (%s)", e)

    try:
        await ensure_auth_multitenancy()
    except Exception as e:
        logger.warning("[startup:ensure_auth_multitenancy] skipped (%s)", e)

    try:
        await ensure_auth_seed()
    except Exception as e:
        logger.warning("[startup:ensure_auth_seed] skipped (%s)", e)

    # Seed process templates, requirements, and gates
    try:
        from backend.app.seed import run_seed
        from backend.app.db.session import async_session_maker
        async with async_session_maker() as db:
            await run_seed(db)
        logger.info("[startup:seed] process templates, requirements, and gates seeded")
    except Exception as e:
        logger.warning("[startup:seed] skipped (%s)", e)

    try:
        if communications_scheduler_enabled():
            scheduler_stop_event = asyncio.Event()
            scheduler_task = asyncio.create_task(
                communications_scheduler_loop(scheduler_stop_event),
                name="communications-scheduler",
            )
            logger.info("[startup:communications_scheduler] started")
        else:
            logger.info("[startup:communications_scheduler] disabled")
    except Exception as e:
        logger.warning("[startup:communications_scheduler] failed to start (%s)", e)

    yield

    if scheduler_stop_event is not None:
        scheduler_stop_event.set()
    if scheduler_task is not None:
        try:
            await asyncio.wait_for(scheduler_task, timeout=10)
            logger.info("[shutdown:communications_scheduler] stopped")
        except Exception as e:
            logger.warning("[shutdown:communications_scheduler] stop failed (%s)", e)

    # graceful DB disconnect on shutdown
    try:
        dbi = getattr(app.state, "db", None)
        if dbi is not None and hasattr(dbi, "disconnect"):
            await dbi.disconnect()
            logger.info("[db] disconnected")
    except Exception as e:
        logger.warning("[db] disconnect failed: %s", e)


app = FastAPI(
    title="HostFlow API",
    version="0.5.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

# CRITICAL: Register /uploads route FIRST, before any other routes/mounts
# This ensures it takes precedence over the root StaticFiles mount
_uploads_dir = os.environ.get("UPLOAD_DIR") or os.path.abspath(
    os.path.join(_backend_root, "uploads")
)
os.makedirs(_uploads_dir, exist_ok=True)

@app.get("/uploads/{file_path:path}")
async def serve_upload_file(file_path: str):
    """Serve uploaded files with correct MIME types."""
    logger.info(f"[uploads] Serving file: {file_path}")
    file_full_path = Path(_uploads_dir) / file_path
    if not file_full_path.exists() or not file_full_path.is_file():
        logger.warning(f"[uploads] File not found: {file_full_path}")
        raise HTTPException(status_code=404, detail="File not found")
    # Ensure file is within uploads directory (security check)
    try:
        file_full_path.resolve().relative_to(Path(_uploads_dir).resolve())
    except ValueError:
        logger.warning(f"[uploads] Access denied: {file_path}")
        raise HTTPException(status_code=403, detail="Access denied")
    logger.info(f"[uploads] Serving file successfully: {file_path}, size: {file_full_path.stat().st_size}")
    return FileResponse(
        str(file_full_path),
        media_type=None,  # Let FileResponse detect MIME type automatically
    )

_metrics_route_registered = False

if Instrumentator is not None:
    try:
        # Configure instrumentator (without custom labels for now to avoid complexity)
        instrumentator = Instrumentator(
            should_group_status_codes=False,
            should_ignore_untemplated=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics", "/healthz", "/health"],
        )
        instrumentator.instrument(app).expose(app, include_in_schema=False)
        _metrics_route_registered = True
        logger.info("[observability] Prometheus instrumentator enabled")
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("[observability] instrumentator init failed: %s", exc)

if not _metrics_route_registered:

    @app.get("/metrics", include_in_schema=False, tags=["internal"])
    async def metrics_endpoint() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Import candidates router directly to avoid side effects from backend.app.api.v1.__init__
try:
    candidates = importlib.import_module("backend.app.api.v1.candidates")
except ModuleNotFoundError:  # pragma: no cover
    candidates = importlib.import_module("app.api.v1.candidates")

# Also mount /api/uploads as StaticFiles for compatibility (fallback)
# Note: /uploads is handled by the explicit route above
app.mount("/api/uploads", StaticFiles(directory=_uploads_dir, html=False), name="api-uploads")

# CRITICAL: Middleware to prevent root StaticFiles from intercepting /uploads requests
# This MUST be registered BEFORE the root StaticFiles mount
@app.middleware("http")
async def prevent_staticfiles_for_uploads(request: Request, call_next):
    """Prevent root StaticFiles from intercepting /uploads requests."""
    if request.url.path.startswith("/uploads/"):
        # Skip StaticFiles and let the explicit /uploads route handle it
        # We need to manually call the route handler
        # But actually, we just need to ensure the route is checked first
        # So we'll let it pass through normally - FastAPI should check routes before mounts
        pass
    response = await call_next(request)
    return response

# Disable cache for /uploads and /api/uploads to avoid stale 304s
@app.middleware("http")
async def _no_cache_uploads(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/uploads/") or request.url.path.startswith("/api/uploads/"):
        headers = response.headers
        # Tell browser not to cache; be explicit to avoid stale 304s
        headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
        headers["Pragma"] = "no-cache"
        # Remove validators that can lead to 304 Not Modified
        for h in ("ETag", "Last-Modified", "Expires"):
            if h in headers:
                del headers[h]
    return response


_CROSS_ORIGIN_ISOLATION_HEADERS = {
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Resource-Policy": "same-origin",
}
_FRONTEND_CONTENT_SECURITY_POLICY = "child-src 'self' blob:; frame-src 'self' blob:"
_CROSS_ORIGIN_EXCLUDE_PREFIXES = (
    "/api",
    "/uploads",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
)
_CROSS_ORIGIN_EXCLUDE_PATHS = {
    "/healthz",
}


def _needs_cross_origin_isolation(path: str) -> bool:
    if not path or path == "":
        return True
    for prefix in _CROSS_ORIGIN_EXCLUDE_PREFIXES:
        if path == prefix or path.startswith(f"{prefix}/"):
            return False
    return path not in _CROSS_ORIGIN_EXCLUDE_PATHS


# Frontend assets (non-/api routes) must opt into cross-origin isolation so OpenCV's
# pthread-enabled wasm (SharedArrayBuffer) can initialise inside the worker.
@app.middleware("http")
async def _ensure_cross_origin_isolation(request: Request, call_next):
    response = await call_next(request)
    if _needs_cross_origin_isolation(request.url.path):
        for header, value in _CROSS_ORIGIN_ISOLATION_HEADERS.items():
            response.headers[header] = value
        response.headers["Content-Security-Policy"] = _FRONTEND_CONTENT_SECURITY_POLICY
    return response


# Normalize legacy proxies that drop the /api prefix (e.g. proxy_pass http://..../)
@app.middleware("http")
async def _restore_api_prefix(request: Request, call_next):
    path = request.scope.get("path", "")
    if path == "/v1" or path.startswith("/v1/"):
        new_path = f"/api{path}"
        request.scope["path"] = new_path
        query = request.scope.get("query_string", b"")
        if query:
            request.scope["raw_path"] = new_path.encode("utf-8") + b"?" + query
        else:
            request.scope["raw_path"] = new_path.encode("utf-8")
    return await call_next(request)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
app.add_middleware(ForceCORSHeadersMiddleware)


@app.get("/healthz", tags=["internal"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}

# --- include routers ---

# Public routes (register FIRST to avoid conflicts with other routes)
# Public scanner routes - NO /api/v1 prefix, they use /public/scan-sessions directly
if public_scanner_router is not None:
    app.include_router(public_scanner_router.meta_router)
    app.include_router(public_scanner_router.router)

# Auth
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(whoami_router, prefix="/api/v1/auth", tags=["auth"])  # /whoami
app.include_router(onboarding_router.router, prefix="/api/v1", tags=["onboarding"])

# Каталоги/метаданные (НЕ требуют X-Tenant-Id)
app.include_router(health_router.router, prefix="/api/v1", tags=["health"])
app.include_router(meta_router.router, prefix="/api/v1", tags=["meta"])
app.include_router(analytics_router.router, prefix="/api/v1", tags=["analytics"])
app.include_router(meta_webhook.router, prefix="/api/v1/leads/meta", tags=["meta-leads"])
app.include_router(general_users_router.router)

app.include_router(catalogs_router.router, prefix="/api/v1", tags=["catalogs"])
app.include_router(additional_services_router.router, prefix="/api/v1", tags=["additional-services"])
app.include_router(reminders_v2_router.router, prefix="/api/v1", tags=["reminders"])

app.include_router(stages_router, prefix="/api/v1", tags=["stages"])
app.include_router(tenants_router, prefix="/api/v1", tags=["tenants"])
app.include_router(platform_tenants_router.router, prefix="/api/v1", tags=["platform-tenants"])
app.include_router(admin_users_router.router, prefix="/api/v1")
app.include_router(admin_companies_access_router.router, prefix="/api/v1")
app.include_router(admin_audit_router.router, prefix="/api/v1")
app.include_router(admin_draft_reminders_router.router, prefix="/api/v1")
app.include_router(settings_leads_router.router, prefix="/api/v1/settings")
app.include_router(settings_team_router.router, prefix="/api/v1/settings")
app.include_router(settings_billing_router.router, prefix="/api/v1/settings")
app.include_router(settings_email_router.router, prefix="/api/v1/settings")
app.include_router(settings_communications_router.router, prefix="/api/v1/settings")
app.include_router(public_intake_router.router, prefix="/api/v1", tags=["public-intake"])
app.include_router(public_notifications_router.router, prefix="/api/v1", tags=["public-notifications"])
app.include_router(public_client_portal_router.router, prefix="/api/v1", tags=["public-client-portal"])
if scanner_router is not None:
    app.include_router(scanner_router.meta_router)
    app.include_router(scanner_router.router)
app.include_router(invoices_router, prefix="/api/v1", tags=["invoices"])

# Домен
app.include_router(companies_router, prefix="/api/v1", tags=["companies"])
app.include_router(vacancies_router, prefix="/api/v1", tags=["vacancies"])
app.include_router(recruiters_router, prefix="/api/v1", tags=["recruiters"])
app.include_router(leads_router, prefix="/api/v1", tags=["leads"])
app.include_router(notifications_router, prefix="/api/v1", tags=["notifications"])
app.include_router(communications_router, prefix="/api/v1", tags=["communications"])

# Document policies and custom fields
app.include_router(document_policies_router.router, prefix="/api/v1", tags=["document-policies"])
app.include_router(custom_fields_router.router, prefix="/api/v1", tags=["custom-fields"])
app.include_router(candidate_profiles_router.router, prefix="/api/v1", tags=["candidate-profiles"])
app.include_router(candidate_stages_router, prefix="/api/v1", tags=["candidate-stages"])
app.include_router(funnels_router, prefix="/api/v1", tags=["funnels"])
app.include_router(legal_documents_router.router, prefix="/api/v1", tags=["legal-documents"])
app.include_router(contact_attempts_router.router, prefix="/api/v1", tags=["contact-attempts"])
app.include_router(handoffs_router.router, prefix="/api/v1", tags=["handoffs"])

# Documents (mount under /api/v1)
if documents_router is not None:
    app.include_router(documents_router, prefix="/api/v1", tags=["documents"])
if documents_db_router is not None:
    app.include_router(documents_db_router, prefix="/api/v1", tags=["documents-db"])

# Кандидаты
app.include_router(candidates.router, prefix="/api/v1/candidates", tags=["candidates"])
app.include_router(candidate_employments_router, prefix="/api/v1", tags=["candidate-employments"])

if not _DOCUMENTS_DISABLED:
    try:
        from backend.app.api.v1.candidate_notes.router import router as candidate_notes_router
        app.include_router(candidate_notes_router)
    except Exception as e:
        logger.warning("[router] candidate-notes skipped: %s", e)

# Documents endpoints (explicit include to guarantee mounting)
if not _DOCUMENTS_DISABLED:
    try:
        from backend.app.api.v1.candidate_documents import router as candidate_docs_router
        app.include_router(candidate_docs_router, prefix="/api/v1", tags=["candidate-docs"])
        app.include_router(candidate_docs_router, tags=["candidate-docs-legacy"])
    except Exception as e:
        logger.warning("[router] candidate-docs skipped (explicit): %s", e)

if not _DOCUMENTS_DISABLED:
    app.include_router(candidate_permits_router, prefix="/api/v1", tags=["candidate-permits"])
    app.include_router(candidate_visas_router, prefix="/api/v1", tags=["candidate-visas"])
    app.include_router(candidate_tasks_router, prefix="/api/v1", tags=["candidate-tasks"])
app.include_router(candidate_delete_router.router)

# Mount root static files LAST to avoid intercepting /uploads requests
# CRITICAL FIX: Use a custom StaticFiles that properly excludes /uploads
# The issue is that with html=True, StaticFiles returns index.html for 404s
# We need to raise a proper exception for /uploads so FastAPI tries the explicit route
public_dir = Path("/app/public")
if public_dir.is_dir():
    class ExcludeUploadsStaticFiles(StaticFiles):
        def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
            # CRITICAL: Exclude /uploads paths completely
            # This raises FileNotFoundError which FastAPI will catch and try other routes
            if path.startswith("uploads/") or path.startswith("/uploads/"):
                raise FileNotFoundError("Path excluded: /uploads handled by explicit route")
            # For other paths, use normal StaticFiles behavior
            return super().lookup_path(path)
        
        async def __call__(self, scope, receive, send):
            # Double check in __call__ as well
            path = scope.get("path", "")
            if path.startswith("/uploads/"):
                from starlette.responses import Response
                response = Response(status_code=404, content="Not found")
                await response(scope, receive, send)
                return
            await super().__call__(scope, receive, send)
    
    app.mount("/", ExcludeUploadsStaticFiles(directory=public_dir, html=True), name="static")

    # SPA fallback for client-side routes like /signup, /login, /app/*
    # NOTE: Starlette StaticFiles with html=True serves index.html for directories,
    # but does not guarantee SPA-style fallback for arbitrary routes.
    index_html = public_dir / "index.html"

    @app.middleware("http")
    async def spa_fallback_middleware(request: Request, call_next):  # type: ignore[no-redef]
        response = await call_next(request)
        if response.status_code != 404:
            return response
        if request.method != "GET":
            return response
        path = request.url.path or "/"
        if path.startswith("/api/") or path == "/api" or path.startswith("/docs") or path.startswith("/openapi"):
            return response
        if path.startswith("/uploads/") or path.startswith("/api/uploads"):
            return response
        accept = request.headers.get("accept", "")
        # Only serve SPA shell for browser navigations.
        if "text/html" not in accept and "*/*" not in accept:
            return response
        if index_html.is_file():
            return FileResponse(str(index_html))
        return response

# S3-style mock upload endpoint for tests/dev
@app.post("/api/v1/db/mock-upload")
async def mock_upload(
    request: Request,
    key: str = Form(...),
    file: UploadFile = File(...),
):
    """Accepts form-data with at least fields: key, file. Other S3-like fields are ignored.
    The uploaded file is persisted under a timestamped path inside UPLOAD_DIR so previous
    revisions remain accessible. Document metadata is synchronised to expose the latest
    file via /documents/{id}/file and /documents/{id}/file-url.
    """
    import os

    if not key:
        raise HTTPException(status_code=400, detail="key is required")

    data = await file.read()
    timestamp = datetime.now(timezone.utc)
    key = key.strip().lstrip("/")
    base_dir, requested_name = os.path.split(key)
    safe_name = sanitize_filename(file.filename or requested_name or "document")
    versioned_name = f"{timestamp.strftime('%Y%m%d%H%M%S')}_{safe_name}"
    rel_dir = Path(base_dir) if base_dir else Path()
    rel_path = (rel_dir / versioned_name).as_posix()

    dest_path = Path(_uploads_dir) / rel_path
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(data)

    stored_url = f"/uploads/{rel_path}"

    document_id: Optional[str] = None
    for part in Path(rel_path).parts:
        try:
            document_id = str(UUID(part))
            break
        except ValueError:
            continue

    if not document_id:
        return {"ok": True, "stored_as": stored_url}

    entry = await register_document_upload(
        document_id=document_id,
        rel_path=rel_path,
        original_name=file.filename or requested_name,
        size=len(data),
        mime=file.content_type,
        uploaded_by=request.headers.get("X-User-Id")
        or request.headers.get("x-user-id"),
    )

    if entry is None:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "ok": True,
        "stored_as": stored_url,
        "document_id": document_id,
        "version": entry.get("version"),
        "url": entry.get("url"),
    }


# Health
@app.get("/health")
async def health():
    return {
        "ok": True,
        "config_dir": os.environ.get("CONFIG_DIR"),
        "upload_dir": os.environ.get("UPLOAD_DIR"),
        "version": getattr(app, "version", None),
    }
