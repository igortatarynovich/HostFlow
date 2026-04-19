from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
    PYDANTIC_V2 = True
except ImportError:  # pragma: no cover - compatibility for system packages
    from pydantic import BaseSettings  # type: ignore

    PYDANTIC_V2 = False

    class SettingsConfigDict(dict):  # type: ignore[misc]
        """Shim so code below stays the same for Pydantic v1."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)

try:
    import dotenv  # noqa: F401
    HAS_DOTENV = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_DOTENV = False
from sqlalchemy.engine.url import URL, make_url


def _mask_url(u: URL) -> str:
    """Маскируем пароль ТОЛЬКО для логов."""
    if u.password:
        return u.set(password="***").render_as_string(hide_password=False)
    return u.render_as_string(hide_password=False)


def _to_async(url: str) -> str:
    """Нормализуем строку подключения к async-драйверу (без маскировки пароля)."""
    u: URL = make_url(url)
    # postgres* → postgresql+asyncpg
    if u.drivername in ("postgres", "postgresql") or u.drivername.startswith(
        ("postgres+", "postgresql+")
    ):
        u = u.set(drivername="postgresql+asyncpg")
        return u.render_as_string(hide_password=False)
    # sqlite* → sqlite+aiosqlite
    if u.drivername == "sqlite" or u.drivername.startswith("sqlite+"):
        u = u.set(drivername="sqlite+aiosqlite")
        return u.render_as_string(hide_password=False)
    return u.render_as_string(hide_password=False)


def _to_sync(url: str) -> str:
    """Нормализуем строку подключения к sync-драйверу (без маскировки пароля)."""
    u: URL = make_url(url)
    if u.drivername == "postgres":
        u = u.set(drivername="postgresql")
    if u.drivername.startswith("postgresql+"):
        u = u.set(drivername="postgresql")
        return u.render_as_string(hide_password=False)
    if u.drivername.startswith("sqlite+"):
        u = u.set(drivername="sqlite")
        return u.render_as_string(hide_password=False)
    return u.render_as_string(hide_password=False)


def _is_postgres(url: str) -> bool:
    try:
        u: URL = make_url(url)
    except Exception:
        return False
    return u.drivername.startswith(("postgres", "postgresql"))


class Settings(BaseSettings):
    """
    Универсальные настройки приложения (Postgres only).

    - `database_url`          — async URL приложения (postgresql+asyncpg).
    - `alembic_database_url`  — sync URL для Alembic (postgresql).
    """

    # Основные переменные
    database_url: Optional[str] = None  # async URL (нормализуем/чиним в __init__)
    sqlalchemy_database_uri: Optional[str] = None
    alembic_database_url: Optional[str] = (
        None  # sync URL (нормализуем/чиним в __init__)
    )

    # Необязательные служебные
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_db: Optional[str] = None
    minio_root_user: Optional[str] = None
    minio_root_password: Optional[str] = None
    jwt_secret: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_timeout: Optional[int] = None
    meta_webhook_secret: Optional[str] = None
    meta_credentials_key: Optional[str] = None
    # Self-serve Meta onboarding (paid tenants): expose in GET /settings/leads/meta/self-serve-onboarding
    meta_leads_app_id: Optional[str] = None
    meta_leads_app_display_name: str = "HostFlow Leads"
    meta_leads_docs_url: Optional[str] = None
    meta_graph_api_version: str = "v24.0"
    # Optional: same App Secret as Meta app (shared app). Shown only to tenant administrators in API.
    meta_leads_shared_app_secret: Optional[str] = None
    # Optional override for Facebook Login redirect (must match Meta app «Valid OAuth Redirect URIs»).
    meta_leads_oauth_redirect_uri: Optional[str] = None
    # Override Focus default for superadmin+bootstrap Meta remap; use off|disable|none|false|0 to disable (forks).
    meta_leads_operational_tenant_id: Optional[str] = None
    pull_field_data_from_graph: bool = True
    auth_token_ttl_minutes: int = 720

    # System email (info@hostflow.cc): password reset, invites
    system_smtp_host: Optional[str] = None
    system_smtp_port: Optional[int] = None
    system_smtp_user: Optional[str] = None
    system_smtp_password: Optional[str] = None
    system_from_email: Optional[str] = None
    system_from_name: Optional[str] = None
    frontend_url: Optional[str] = None  # e.g. https://app.hostflow.cc
    # Optional absolute API origin for inbound webhook URLs shown after rotate (e.g. https://api.hostflow.cc)
    public_api_base_url: Optional[str] = None

    # Stripe billing
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_starter: Optional[str] = None
    stripe_price_starter_yearly: Optional[str] = None
    stripe_price_team: Optional[str] = None
    stripe_price_team_yearly: Optional[str] = None
    stripe_price_pro: Optional[str] = None
    stripe_price_pro_yearly: Optional[str] = None
    stripe_price_operating_company_slot: Optional[str] = None
    stripe_price_operating_company_slot_team: Optional[str] = None
    stripe_price_operating_company_slot_business: Optional[str] = None
    stripe_price_portal_candidates_pack: Optional[str] = None
    portal_candidates_pack_increment: int = 500
    stripe_price_seat_team: Optional[str] = None
    stripe_price_seat_business: Optional[str] = None
    stripe_price_client_portal_account_team: Optional[str] = None
    stripe_price_client_portal_account_business: Optional[str] = None
    stripe_price_client_portal_pack_5: Optional[str] = None
    stripe_price_branded_portal_workspace: Optional[str] = None
    stripe_price_automation_rules_pack_10: Optional[str] = None
    stripe_price_automation_rules_pack_25: Optional[str] = None
    automation_rules_pack_10_increment: int = 10
    automation_rules_pack_25_increment: int = 25
    stripe_price_custom_fields_pack_25: Optional[str] = None
    stripe_price_custom_fields_pack_100: Optional[str] = None
    custom_fields_pack_25_increment: int = 25
    custom_fields_pack_100_increment: int = 100
    stripe_price_lead_source_extra: Optional[str] = None
    stripe_price_lead_forms_pack_5: Optional[str] = None
    lead_forms_pack_increment: int = 5
    stripe_price_communication_channel_extra: Optional[str] = None
    stripe_price_leads_pack_500: Optional[str] = None
    leads_pack_500_increment: int = 500
    stripe_price_active_records_pack_2000: Optional[str] = None
    active_records_pack_2000_increment: int = 2000
    stripe_price_storage_pack_50gb: Optional[str] = None
    storage_pack_50gb_increment_gb: int = 50
    stripe_portal_return_url: Optional[str] = None

    # Observability (Sentry + structured logging)
    # When sentry_dsn is unset, Sentry is a no-op; the app runs exactly as before.
    sentry_dsn: Optional[str] = None
    sentry_environment: Optional[str] = None  # e.g. "production", "staging", "development"
    sentry_release: Optional[str] = None  # e.g. git SHA; surfaced in Sentry issue
    sentry_traces_sample_rate: float = 0.1  # 10% performance trace sampling by default
    sentry_profiles_sample_rate: float = 0.0  # off by default (extra cost)
    sentry_send_default_pii: bool = False  # never send default PII unless explicitly enabled
    # Logging format: "text" (default, human-readable for dev) or "json" (structured for aggregators)
    log_format: str = "text"
    log_level: str = "INFO"

    # Rate limiting (public endpoints). Backed by Redis when REDIS_URL is set.
    # Values follow slowapi syntax: "N/period" where period ∈ {second, minute, hour, day}.
    rate_limit_enabled: bool = True
    rate_limit_storage_url: Optional[str] = None  # falls back to REDIS_URL then memory://
    rate_limit_login: str = "10/minute"
    rate_limit_signup: str = "5/hour"
    rate_limit_password_reset: str = "5/hour"
    rate_limit_public_intake: str = "20/hour"
    rate_limit_magic_link: str = "5/hour"
    rate_limit_public_default: str = "60/minute"

    # Background job queue (ARQ / Redis). When `job_queue_backend == "inprocess"` (default)
    # `app.core.queue.enqueue()` keeps firing asyncio.create_task in the request process —
    # exactly as before. When set to "arq" the same API pushes jobs into ARQ/Redis instead,
    # and a separate `arq backend.app.core.arq_worker.WorkerSettings` worker drains the queue.
    # `job_queue_redis_url` defaults to REDIS_URL when unset.
    job_queue_backend: str = "inprocess"  # "inprocess" | "arq"
    job_queue_redis_url: Optional[str] = None
    job_queue_name: str = "hostflow:jobs"
    job_queue_default_timeout_sec: int = 120
    job_queue_max_tries: int = 5
    # When offloading Stripe webhook handlers to ARQ we still return 200 immediately
    # and let the worker retry — but the signature + idempotency claim still happen
    # on the request path. Set this to false to force inline processing even with ARQ.
    job_queue_stripe_webhook_async: bool = True

    # Object storage (Phase 0 #6). "fs" keeps the historical UPLOAD_DIR layout served
    # via `/uploads/<path>` (default, zero-migration). "s3" routes writes through
    # `app.core.object_storage` to an S3-compatible bucket (AWS S3, MinIO, Cloudflare R2, …)
    # and emits presigned URLs for downloads. `object_storage_bucket` is required when
    # backend=="s3"; other s3_* fields default to MinIO-in-docker-compose values.
    object_storage_backend: str = "fs"  # "fs" | "s3"
    object_storage_bucket: Optional[str] = None
    object_storage_region: str = "us-east-1"
    object_storage_endpoint_url: Optional[str] = None  # e.g. http://minio:9000 for MinIO
    object_storage_access_key_id: Optional[str] = None
    object_storage_secret_access_key: Optional[str] = None
    object_storage_public_base_url: Optional[str] = None  # optional CDN prefix for public reads
    # Force path-style addressing (required for MinIO, Ceph RGW, Backblaze, …).
    object_storage_use_path_style: bool = True
    # TTL for presigned GET URLs handed to clients (seconds).
    object_storage_presign_expires_sec: int = 900
    # When true (default), `/uploads/<key>` handler 302-redirects to a presigned URL
    # instead of serving the file from disk. Set to false to keep direct file serving
    # during an intermediate migration window.
    object_storage_redirect_uploads_endpoint: bool = True

    # Cloudflare Turnstile (CAPTCHA). No-op when turnstile_secret_key is unset.
    # Sitekey flows to the frontend via a public config endpoint or build-time env.
    turnstile_enabled: bool = False
    turnstile_secret_key: Optional[str] = None
    turnstile_sitekey: Optional[str] = None  # exposed publicly; used by frontend widget
    turnstile_verify_url: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

    if PYDANTIC_V2:
        _model_cfg: dict[str, object] = {
            "extra": "ignore",
        }
        if HAS_DOTENV:
            _model_cfg["env_file"] = ".env"
            _model_cfg["env_file_encoding"] = "utf-8"
        model_config = SettingsConfigDict(**_model_cfg)
    else:  # pragma: no cover - Pydantic v1 compatibility
        class Config:
            extra = "ignore"
            if HAS_DOTENV:
                env_file = ".env"
                env_file_encoding = "utf-8"

    def __init__(self, **values):
        super().__init__(**values)

        # 1) Поддержим альтернативные имена переменных окружения
        #    Берём первое непустое из: database_url (поле), DATABASE_URL, ASYNC_DATABASE_URL, SQLALCHEMY_DATABASE_URI
        self.database_url = (
            self.database_url
            or os.environ.get("DATABASE_URL")
            or os.environ.get("ASYNC_DATABASE_URL")
            or self.sqlalchemy_database_uri
            or os.environ.get("SQLALCHEMY_DATABASE_URI")
        )

        allow_sqlite = os.environ.get("ALLOW_SQLITE_FOR_TESTS") in {"1", "true", "True"}

        # 2) Обязательно требуем Postgres (кроме разрешённого тестового режима).
        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL/ASYNC_DATABASE_URL must be set and point to Postgres"
            )

        # 3) Нормализуем к async-драйверу и валидируем, что это Postgres
        self.database_url = _to_async(self.database_url)
        if not _is_postgres(self.database_url) and not allow_sqlite:
            raise RuntimeError(
                f"Only Postgres is supported now. Got: {self.database_url}"
            )

        # 4) Alembic URL (sync). Если явно задан — нормализуем; иначе строим из async.
        if self.alembic_database_url:
            self.alembic_database_url = _to_sync(self.alembic_database_url)
        else:
            self.alembic_database_url = _to_sync(self.database_url)

        # 5) Отладочная печать (маскируем только в логах)
        try:
            au = make_url(self.database_url)
            su = make_url(self.alembic_database_url)
            print(f"[settings] ASYNC_DATABASE_URL = {_mask_url(au)}")
            print(f"[settings] SYNC_DATABASE_URL  = {_mask_url(su)}")
        except Exception:
            pass

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """РЕАЛЬНЫЙ async URL без маскировки, для engine приложения."""
        assert self.database_url is not None, "database_url must be set"
        return self.database_url

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """РЕАЛЬНЫЙ sync URL без маскировки, для Alembic."""
        assert self.alembic_database_url is not None, "alembic_database_url must be set"
        return self.alembic_database_url


settings = Settings()
