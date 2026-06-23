from __future__ import annotations
import asyncio
import logging
from logging.config import dictConfig
import os
import importlib
import re
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


def _test_light_startup() -> bool:
    return os.environ.get("HOSTFLOW_TEST_LIGHT_STARTUP", "").strip().lower() in ("1", "true", "yes")


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
for _name, _module in list(_sys.modules.items()):
    if _name.startswith("app.models.") and _module is not None:
        _sys.modules.setdefault(f"backend.{_name}", _module)

_DOCUMENTS_DISABLED = bool(int(os.environ.get("DOCUMENTS_DISABLED", "0")))

try:
    from backend.app.api.v1 import meta as meta_router  # meta_router.router
    from backend.app.api.v1 import health as health_router
    from backend.app.api.v1 import users as general_users_router
    from backend.app.api.v1 import analytics as analytics_router
    from backend.app.api.v1 import goals as goals_router
    from backend.app.api.v1 import candidates_delete as candidate_delete_router
    from backend.app.api.v1 import catalogs as catalogs_router
    from backend.app.api.v1 import reminders_v2 as reminders_v2_router
    from backend.app.api.v1 import activities_v1 as activities_v1_router
    from backend.app.api.v1 import automation_log as automation_log_router
    from backend.app.api.v1 import automation_rules as automation_rules_router
    from backend.app.api.v1 import services as additional_services_router
    # Legacy OpenCV document scanner product path removed (see docs/SSOT.md); keep package for future LLM pipeline.
    scanner_router = None  # type: ignore[assignment]
    from backend.app.auth.router import router as auth_router
    from backend.app.auth.whoami import router as whoami_router
    from backend.app.auth.ensure_multitenancy import ensure_auth_multitenancy
    from backend.app.auth.ensure_seed import ensure_auth_seed
    from backend.app.core.settings import settings
    from backend.app.modules.leads import inbound_public as leads_inbound_public
    from backend.app.modules.leads import webhook as meta_webhook
    from backend.app.modules.companies.router import router as companies_router
    from backend.app.modules.companies.ensure_schema import ensure_companies_schema
    from backend.app.modules.notifications.ensure_schema import ensure_notifications_schema
    from backend.app.services.ensure_reminders_schema import ensure_reminders_schema
    from backend.app.services.ensure_additional_services_schema import (
        ensure_additional_services_schema,
        ensure_service_orders_own_company_id_column,
    )
    from backend.app.services.ensure_automation_rules_schema import ensure_automation_rules_schema
    from backend.app.services.ensure_communications_schema import ensure_communications_schema
    from backend.app.services.ensure_funnels_schema import ensure_funnels_schema
    from backend.app.services.ensure_global_search_fts import ensure_global_search_fts_function_async
    from backend.app.api.v1.vacancies.router import router as vacancies_router
    from backend.app.api.v1.own_companies import legacy_router as own_companies_legacy_router
    from backend.app.api.v1.own_companies import router as own_companies_router
    from backend.app.api.public import intake as public_intake_router
    public_scanner_router = None  # type: ignore[assignment]
    from backend.app.api.public import notifications as public_notifications_router
    from backend.app.api.public import client_portal as public_client_portal_router
    from backend.app.api.public import goals as public_goals_router
    from backend.app.api.public import legal_pages as public_legal_pages_router
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
        # Phase 2.1 (ADR-012): legacy /api/v1/candidates/{id}/tasks removed.
        # Use /api/v1/activities (canonical) — see ADR-012 §6 + canon §7.2.
    from backend.app.api.v1.candidate_employments import router as candidate_employments_router
    from backend.app.api.v1.stages import router as stages_router
    from backend.app.api.v1.tenants.router import router as tenants_router
    from backend.app.api.v1.platform import tenants as platform_tenants_router
    from backend.app.api.v1.platform import field_registry as platform_field_registry_router
    from backend.app.api.v1.platform import entity_profiles as platform_entity_profiles_router
    from backend.app.api.v1.platform import requirement_rules as platform_requirement_rules_router
    from backend.app.api.v1.platform import tenant_requirement_overrides as platform_tenant_requirement_overrides_router
    from backend.app.api.v1.platform import notification_events as platform_notification_events_router
    from backend.app.api.v1.platform import module_registry as platform_module_registry_router
    from backend.app.api.v1.settings import leads as settings_leads_router
    from backend.app.api.v1.settings import team as settings_team_router
    from backend.app.api.v1.settings import billing as settings_billing_router
    from backend.app.api.v1.settings import lead_forms as settings_lead_forms_router
    from backend.app.api.v1.settings import intake_forms as settings_intake_forms_router
    from backend.app.api.v1.settings import email as settings_email_router
    from backend.app.api.v1.settings import communications as settings_communications_router
    from backend.app.api.v1.admin import users as admin_users_router
    from backend.app.api.v1.admin import companies_access as admin_companies_access_router
    from backend.app.api.v1.admin import audit as admin_audit_router
    from backend.app.api.v1.admin import draft_reminders as admin_draft_reminders_router
    from backend.app.api.v1.recruiters.router import router as recruiters_router
    from backend.app.api.v1.leads.router import router as leads_router
    from backend.app.api.v1.next_actions import router as next_actions_router
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
    from backend.app.api.v1 import hr_dashboard as hr_dashboard_router
    from backend.app.api.v1 import hr_inbox as hr_inbox_router
    from backend.app.api.v1.document_merge import router as document_merge_router
    from backend.app.api.v1.workforce.router import router as workforce_router
    from backend.app.api.v1 import global_search as global_search_router
    from backend.app.api.v1.fleet.router import router as fleet_router
    from backend.app.api.v1 import calendar as calendar_router
    from backend.app.api.v1 import onboarding as onboarding_router
except ModuleNotFoundError:  # pragma: no cover - backend package alias
    from .api.v1 import meta as meta_router  # type: ignore[no-redef]
    from .api.v1 import health as health_router  # type: ignore[no-redef]
    from .api.v1 import users as general_users_router  # type: ignore[no-redef]
    from .api.v1 import analytics as analytics_router  # type: ignore[no-redef]
    from .api.v1 import goals as goals_router  # type: ignore[no-redef]
    from .api.v1 import candidates_delete as candidate_delete_router  # type: ignore[no-redef]
    from .api.v1 import catalogs as catalogs_router  # type: ignore[no-redef]
    from .api.v1 import reminders_v2 as reminders_v2_router  # type: ignore[no-redef]
    from .api.v1 import activities_v1 as activities_v1_router  # type: ignore[no-redef]
    from .api.v1 import services as additional_services_router  # type: ignore[no-redef]
    scanner_router = None  # type: ignore[assignment]
    from .auth.router import router as auth_router  # type: ignore[no-redef]
    from .auth.whoami import router as whoami_router  # type: ignore[no-redef]
    from .auth.ensure_multitenancy import ensure_auth_multitenancy  # type: ignore[no-redef]
    from .auth.ensure_seed import ensure_auth_seed  # type: ignore[no-redef]
    from .core.settings import settings  # type: ignore[no-redef]
    from .modules.leads import inbound_public as leads_inbound_public  # type: ignore[no-redef]
    from .modules.leads import webhook as meta_webhook  # type: ignore[no-redef]
    from .modules.companies.router import router as companies_router  # type: ignore[no-redef]
    from .modules.companies.ensure_schema import ensure_companies_schema  # type: ignore[no-redef]
    from .modules.notifications.ensure_schema import ensure_notifications_schema  # type: ignore[no-redef]
    from .services.ensure_reminders_schema import ensure_reminders_schema  # type: ignore[no-redef]
    from .services.ensure_additional_services_schema import (  # type: ignore[no-redef]
        ensure_additional_services_schema,
        ensure_service_orders_own_company_id_column,
    )
    from .services.ensure_communications_schema import ensure_communications_schema  # type: ignore[no-redef]
    from .services.ensure_funnels_schema import ensure_funnels_schema  # type: ignore[no-redef]
    from .services.ensure_global_search_fts import ensure_global_search_fts_function_async  # type: ignore[no-redef]
    from .api.v1.vacancies.router import router as vacancies_router  # type: ignore[no-redef]
    from .api.public import intake as public_intake_router  # type: ignore[no-redef]
    public_scanner_router = None  # type: ignore[assignment]
    from .api.public import notifications as public_notifications_router  # type: ignore[no-redef]
    from .api.public import client_portal as public_client_portal_router  # type: ignore[no-redef]
    from .api.public import goals as public_goals_router  # type: ignore[no-redef]
    from .api.public import legal_pages as public_legal_pages_router  # type: ignore[no-redef]
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
        # Phase 2.1 (ADR-012): legacy /api/v1/candidates/{id}/tasks removed.
        # Use /api/v1/activities (canonical) — see ADR-012 §6 + canon §7.2.
    from .api.v1.candidate_employments import router as candidate_employments_router  # type: ignore[no-redef]
    from .api.v1.stages import router as stages_router  # type: ignore[no-redef]
    from .api.v1.tenants.router import router as tenants_router  # type: ignore[no-redef]
    from .api.v1.platform import tenants as platform_tenants_router  # type: ignore[no-redef]
    from .api.v1.platform import field_registry as platform_field_registry_router  # type: ignore[no-redef]
    from .api.v1.platform import module_registry as platform_module_registry_router  # type: ignore[no-redef]
    from .api.v1.settings import leads as settings_leads_router  # type: ignore[no-redef]
    from .api.v1.settings import team as settings_team_router  # type: ignore[no-redef]
    from .api.v1.settings import billing as settings_billing_router  # type: ignore[no-redef]
    from .api.v1.settings import lead_forms as settings_lead_forms_router  # type: ignore[no-redef]
    from .api.v1.settings import intake_forms as settings_intake_forms_router  # type: ignore[no-redef]
    from .api.v1.settings import email as settings_email_router  # type: ignore[no-redef]
    from .api.v1.settings import communications as settings_communications_router  # type: ignore[no-redef]
    from .api.v1.admin import users as admin_users_router  # type: ignore[no-redef]
    from .api.v1.admin import companies_access as admin_companies_access_router  # type: ignore[no-redef]
    from .api.v1.admin import audit as admin_audit_router  # type: ignore[no-redef]
    from .api.v1.admin import draft_reminders as admin_draft_reminders_router  # type: ignore[no-redef]
    from .api.v1.recruiters.router import router as recruiters_router  # type: ignore[no-redef]
    from .api.v1.leads.router import router as leads_router  # type: ignore[no-redef]
    from .api.v1.next_actions import router as next_actions_router  # type: ignore[no-redef]
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
    from .api.v1 import hr_dashboard as hr_dashboard_router  # type: ignore[no-redef]
    from .api.v1 import hr_inbox as hr_inbox_router  # type: ignore[no-redef]
    from .api.v1.document_merge import router as document_merge_router  # type: ignore[no-redef]
    from .api.v1.workforce.router import router as workforce_router  # type: ignore[no-redef]
    from .api.v1 import global_search as global_search_router  # type: ignore[no-redef]
    from .api.v1.fleet.router import router as fleet_router  # type: ignore[no-redef]
    from .api.v1 import calendar as calendar_router  # type: ignore[no-redef]
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

try:
    from backend.app.core.observability import init_sentry, logging_dict_config
    from backend.app.core.rate_limit import register_rate_limit
except ModuleNotFoundError:  # pragma: no cover - backend package alias
    from .core.observability import init_sentry, logging_dict_config  # type: ignore[no-redef]
    from .core.rate_limit import register_rate_limit  # type: ignore[no-redef]

init_sentry()
dictConfig(logging_dict_config())

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

    if not _test_light_startup():
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
            from .modules.intake_routing.ensure_schema import ensure_intake_routing_schema

            ensure_intake_routing_schema()
        except Exception as e:
            logger.warning("[startup:ensure_intake_routing_schema] skipped (%s)", e)

        try:
            ensure_notifications_schema()
        except Exception as e:
            logger.warning("[startup:ensure_notifications_schema] skipped (%s)", e)

        try:
            ensure_reminders_schema()
        except Exception as e:
            logger.warning("[startup:ensure_reminders_schema] skipped (%s)", e)

        try:
            ensure_additional_services_schema()
        except Exception as e:
            logger.warning("[startup:ensure_additional_services_schema] skipped (%s)", e)

        try:
            ensure_service_orders_own_company_id_column()
        except Exception as e:
            logger.warning("[startup:ensure_service_orders_own_company_id] skipped (%s)", e)

        try:
            ensure_automation_rules_schema()
        except Exception as e:
            logger.warning("[startup:ensure_automation_rules_schema] skipped (%s)", e)

        try:
            ensure_communications_schema()
        except Exception as e:
            logger.warning("[startup:ensure_communications_schema] skipped (%s)", e)

        try:
            ensure_funnels_schema()
        except Exception as e:
            logger.warning("[startup:ensure_funnels_schema] skipped (%s)", e)

        try:
            await ensure_global_search_fts_function_async()
        except Exception as e:
            logger.warning("[startup:ensure_global_search_fts_function_async] skipped (%s)", e)

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
            seed_timeout = float(os.environ.get("HOSTFLOW_STARTUP_SEED_TIMEOUT_SECONDS", "30") or "30")
            async with async_session_maker() as db:
                await asyncio.wait_for(run_seed(db), timeout=seed_timeout)
            logger.info("[startup:seed] process templates, requirements, and gates seeded")
        except asyncio.TimeoutError:
            logger.warning("[startup:seed] skipped after timeout")
        except Exception as e:
            logger.warning("[startup:seed] skipped (%s)", e)
    else:
        logger.info("[startup] HOSTFLOW_TEST_LIGHT_STARTUP=1 — skipped heavy schema/seed bootstrap")

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

    # Close the ARQ connection pool if one was created during request handling.
    try:
        from backend.app.core.queue import close_arq_pool

        await close_arq_pool()
    except Exception as e:
        logger.warning("[shutdown:arq] pool close failed (%s)", e)

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

# Register rate-limiting (slowapi + Redis when REDIS_URL set; no-op when disabled).
# Must run before any public endpoints are decorated with `@limiter.limit(...)`.
register_rate_limit(app)

# CRITICAL: Register /uploads route FIRST, before any other routes/mounts
# This ensures it takes precedence over the root StaticFiles mount
_uploads_dir = os.environ.get("UPLOAD_DIR") or os.path.abspath(
    os.path.join(_backend_root, "uploads")
)
os.makedirs(_uploads_dir, exist_ok=True)

@app.get("/uploads/{file_path:path}")
async def serve_upload_file(file_path: str):
    """Serve uploaded files.

    When the active object storage backend is filesystem-based this returns
    the file directly (unchanged pre-Phase-0 behaviour). When an S3-compatible
    backend is active and
    ``settings.object_storage_redirect_uploads_endpoint`` is enabled, we
    302-redirect to a short-lived presigned URL so legacy clients that still
    hit ``/uploads/<key>`` keep working without leaking credentials.
    """
    from backend.app.core.object_storage import get_object_storage, normalize_key
    from fastapi.responses import RedirectResponse

    try:
        key = normalize_key(file_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload key") from None

    storage = get_object_storage()
    local_root = storage.local_path("")

    # S3-backed deployment: redirect to a presigned URL and let the bucket /
    # CDN serve the bytes directly.
    if local_root is None:
        if not settings.object_storage_redirect_uploads_endpoint:
            raise HTTPException(status_code=404, detail="File not found")
        try:
            url = storage.presigned_get_url(key)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("[uploads] presign failed for %s: %s", key, exc)
            raise HTTPException(status_code=500, detail="Storage unavailable") from None
        doc_uuid_m = re.search(
            r"(?:^|/)documents/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?:/|$)",
            key,
        )
        if doc_uuid_m:
            from backend.app.security.document_events import emit_document_security_event_v1
            from backend.app.security.event_taxonomy import EVENT_DOCUMENT_SIGNED_URL_GENERATED

            emit_document_security_event_v1(
                event_type=EVENT_DOCUMENT_SIGNED_URL_GENERATED,
                result="success",
                severity="info",
                source="http:main:uploads_presign_redirect",
                tenant_id=None,
                document_id=doc_uuid_m.group(1).lower(),
                access_kind=None,
                has_presigned_url_shape=True,
                response_mode="redirect_302",
            )
        return RedirectResponse(url=url, status_code=302)

    # Filesystem backend: serve from disk as before.
    file_full_path = local_root / key
    if not file_full_path.exists() or not file_full_path.is_file():
        logger.warning(f"[uploads] File not found: {file_full_path}")
        raise HTTPException(status_code=404, detail="File not found")
    try:
        file_full_path.resolve().relative_to(local_root.resolve())
    except ValueError:
        logger.warning(f"[uploads] Access denied: {file_path}")
        raise HTTPException(status_code=403, detail="Access denied")
    return FileResponse(
        str(file_full_path),
        media_type=None,  # Let FileResponse detect MIME type automatically
    )

_metrics_route_registered = False

_enable_prometheus_instrumentator = os.environ.get(
    "HOSTFLOW_ENABLE_PROMETHEUS_INSTRUMENTATOR",
    "",
).strip().lower() in {"1", "true", "yes"}

if Instrumentator is not None and _enable_prometheus_instrumentator:
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


# Attach tenant/user/request context to the Sentry scope and expose X-Request-ID
@app.middleware("http")
async def _observability_context(request: Request, call_next):
    import uuid
    try:
        from backend.app.core.observability import bind_request_context
    except ModuleNotFoundError:  # pragma: no cover
        from .core.observability import bind_request_context  # type: ignore[no-redef]

    from backend.app.security.runtime_context import (
        reset_security_actor_token,
        reset_security_correlation_token,
        set_security_actor_id,
        set_security_correlation_id,
    )

    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    cor_tok = set_security_correlation_id(request_id)
    act_tok = set_security_actor_id(None)
    tenant_id = (
        request.headers.get("x-tenant-id")
        or request.headers.get("X-Tenant-Id")
    )
    user_id = (
        request.headers.get("x-user-id")
        or request.headers.get("X-User-Id")
    )
    try:
        bind_request_context(
            tenant_id=tenant_id,
            user_id=user_id,
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
    except Exception:
        pass
    try:
        response = await call_next(request)
    finally:
        try:
            reset_security_correlation_token(cor_tok)
            reset_security_actor_token(act_tok)
        except Exception:
            pass
    try:
        response.headers.setdefault("X-Request-ID", request_id)
    except Exception:
        pass
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
# Auth
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(whoami_router, prefix="/api/v1/auth", tags=["auth"])  # /whoami
app.include_router(onboarding_router.router, prefix="/api/v1", tags=["onboarding"])

# Каталоги/метаданные (НЕ требуют X-Tenant-Id)
app.include_router(health_router.router, prefix="/api/v1", tags=["health"])
app.include_router(meta_router.router, prefix="/api/v1", tags=["meta"])
app.include_router(analytics_router.router, prefix="/api/v1", tags=["analytics"])
app.include_router(goals_router.router, prefix="/api/v1", tags=["goals"])
app.include_router(meta_webhook.router, prefix="/api/v1/leads/meta", tags=["meta-leads"])
app.include_router(leads_inbound_public.router, prefix="/api/v1", tags=["public-leads-inbound"])
app.include_router(general_users_router.router)

app.include_router(catalogs_router.router, prefix="/api/v1", tags=["catalogs"])
app.include_router(additional_services_router.router, prefix="/api/v1", tags=["additional-services"])
app.include_router(reminders_v2_router.router, prefix="/api/v1", tags=["reminders"])
app.include_router(activities_v1_router.router, prefix="/api/v1", tags=["activities"])
app.include_router(calendar_router.router, prefix="/api/v1", tags=["calendar"])
app.include_router(automation_log_router.router, prefix="/api/v1", tags=["automation-log"])
app.include_router(automation_rules_router.router, prefix="/api/v1", tags=["automation-rules"])

app.include_router(stages_router, prefix="/api/v1", tags=["stages"])
app.include_router(tenants_router, prefix="/api/v1", tags=["tenants"])
app.include_router(platform_tenants_router.router, prefix="/api/v1", tags=["platform-tenants"])
app.include_router(platform_field_registry_router.router, prefix="/api/v1", tags=["field-registry"])
app.include_router(platform_entity_profiles_router.router, prefix="/api/v1", tags=["entity-profiles"])
app.include_router(platform_requirement_rules_router.router, prefix="/api/v1", tags=["requirement-rules"])
app.include_router(platform_tenant_requirement_overrides_router.router, prefix="/api/v1", tags=["requirement-overrides"])
app.include_router(platform_notification_events_router.router, prefix="/api/v1", tags=["notification-events"])
app.include_router(platform_module_registry_router.router, prefix="/api/v1", tags=["module-registry"])
app.include_router(admin_users_router.router, prefix="/api/v1")
app.include_router(admin_companies_access_router.router, prefix="/api/v1")
app.include_router(admin_audit_router.router, prefix="/api/v1")
app.include_router(admin_draft_reminders_router.router, prefix="/api/v1")
app.include_router(settings_leads_router.router, prefix="/api/v1/settings")
app.include_router(settings_team_router.router, prefix="/api/v1/settings")
app.include_router(settings_billing_router.router, prefix="/api/v1/settings")
app.include_router(settings_lead_forms_router.router, prefix="/api/v1/settings")
app.include_router(settings_intake_forms_router.router, prefix="/api/v1/settings")
app.include_router(settings_email_router.router, prefix="/api/v1/settings")
app.include_router(settings_communications_router.router, prefix="/api/v1/settings")
app.include_router(public_intake_router.router, prefix="/api/v1", tags=["public-intake"])
app.include_router(public_notifications_router.router, prefix="/api/v1", tags=["public-notifications"])
app.include_router(public_client_portal_router.router, prefix="/api/v1", tags=["public-client-portal"])
app.include_router(public_goals_router.router, prefix="/api/v1", tags=["public-goals"])
app.include_router(public_legal_pages_router.router)
if scanner_router is not None:
    app.include_router(scanner_router.meta_router)
    app.include_router(scanner_router.router)
app.include_router(invoices_router, prefix="/api/v1", tags=["invoices"])

# Домен
app.include_router(companies_router, prefix="/api/v1", tags=["companies"])
app.include_router(vacancies_router, prefix="/api/v1", tags=["vacancies"])
app.include_router(fleet_router, prefix="/api/v1", tags=["fleet"])
app.include_router(own_companies_router, prefix="/api/v1", tags=["own-companies"])
app.include_router(own_companies_legacy_router, prefix="/api/v1", tags=["own-companies"])
app.include_router(recruiters_router, prefix="/api/v1", tags=["recruiters"])
app.include_router(leads_router, prefix="/api/v1", tags=["leads"])
app.include_router(next_actions_router, prefix="/api/v1", tags=["next-actions"])
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
app.include_router(hr_inbox_router.router, prefix="/api/v1", tags=["hr-inbox"])
app.include_router(hr_dashboard_router.router, prefix="/api/v1", tags=["hr-dashboard"])
app.include_router(document_merge_router, prefix="/api/v1", tags=["document-merge"])
app.include_router(workforce_router, prefix="/api/v1", tags=["workforce"])
app.include_router(global_search_router.router, prefix="/api/v1", tags=["search"])

# Documents (mount under /api/v1)
if documents_router is not None:
    app.include_router(documents_router, prefix="/api/v1", tags=["documents"])
if documents_db_router is not None:
    app.include_router(documents_db_router, prefix="/api/v1", tags=["documents-db"])

# Кандидаты
app.include_router(candidates.router, prefix="/api/v1/candidates", tags=["candidates"])
try:
    from backend.app.api.v1 import candidate_links as candidate_links_router

    app.include_router(candidate_links_router.router, prefix="/api/v1", tags=["candidate-links"])
except Exception as e:
    logger.warning("[router] candidate-links skipped: %s", e)
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
    # Phase 2.1 (ADR-012): legacy candidate-tasks router was mounted here.
    # The HTTP surface /api/v1/candidates/{id}/tasks is gone; canonical
    # task CRUD is /api/v1/activities (mounted above).
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
