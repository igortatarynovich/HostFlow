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

    # Stripe billing
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_starter: Optional[str] = None
    stripe_price_team: Optional[str] = None
    stripe_price_pro: Optional[str] = None
    stripe_price_operating_company_slot: Optional[str] = None
    stripe_portal_return_url: Optional[str] = None

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
