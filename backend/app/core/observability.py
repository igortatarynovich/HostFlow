"""
Observability: Sentry init + structured logging config.

Why this module exists
----------------------
The app has historically relied on raw `print` / `logger.warning` and a single
Prometheus exporter. Real incidents in production need more:

1. Exceptions with context (tenant_id, user_id, request_id, path, method).
2. Structured logs that can be shipped to an aggregator (Datadog, Loki, ELK).
3. Performance traces for the slowest endpoints.

This module is the single place to wire those up. It is a no-op if Sentry DSN
is not configured, so every environment (including CI and local) stays clean.

Usage
-----
    from backend.app.core.observability import init_sentry, logging_dict_config

    init_sentry()                               # call once at import of main.py
    dictConfig(logging_dict_config())           # replaces the ad-hoc dictConfig

    # In request middleware:
    from backend.app.core.observability import bind_request_context
    bind_request_context(tenant_id=..., user_id=..., request_id=...)

Environment variables
---------------------
    SENTRY_DSN                      — enable Sentry if set
    SENTRY_ENVIRONMENT              — production / staging / development / local
    SENTRY_RELEASE                  — git sha or app version (shown on issues)
    SENTRY_TRACES_SAMPLE_RATE       — 0.0–1.0, default 0.1
    SENTRY_PROFILES_SAMPLE_RATE     — 0.0–1.0, default 0.0
    SENTRY_SEND_DEFAULT_PII         — "1"/"true" to send default PII; default off
    LOG_FORMAT                      — "json" (for prod) or "text" (for dev)
    LOG_LEVEL                       — DEBUG / INFO / WARNING / ERROR; default INFO

All of these are already exposed via `backend.app.core.settings.Settings`.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_SENTRY_INITIALIZED = False


def _settings_value(name: str, default: Any = None) -> Any:
    """Read from Settings if available, else env var (for very early init)."""
    try:
        from backend.app.core.settings import settings  # local import to avoid cycles
    except Exception:  # pragma: no cover - startup ordering
        return os.environ.get(name.upper(), default)
    return getattr(settings, name, os.environ.get(name.upper(), default))


def init_sentry() -> bool:
    """
    Initialize Sentry exactly once. Returns True if enabled, False otherwise.

    Safe to call multiple times — subsequent calls are no-ops.
    No-op if `SENTRY_DSN` is not configured; the rest of the app behaves identically.
    """
    global _SENTRY_INITIALIZED
    if _SENTRY_INITIALIZED:
        return True

    dsn = _settings_value("sentry_dsn")
    if not dsn:
        logger.info("[observability] Sentry DSN not set — skipping init")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError as exc:  # pragma: no cover - defensive
        logger.warning("[observability] sentry-sdk not installed (%s); skipping", exc)
        return False

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=_settings_value("sentry_environment") or "unknown",
            release=_settings_value("sentry_release"),
            traces_sample_rate=float(_settings_value("sentry_traces_sample_rate", 0.1) or 0.1),
            profiles_sample_rate=float(_settings_value("sentry_profiles_sample_rate", 0.0) or 0.0),
            send_default_pii=bool(_settings_value("sentry_send_default_pii", False)),
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                AsyncioIntegration(),
                # Capture logs at ERROR level as Sentry events; INFO+ as breadcrumbs
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            # Strip potentially sensitive data from breadcrumbs/events
            before_send=_sentry_before_send,
        )
        _SENTRY_INITIALIZED = True
        logger.info(
            "[observability] Sentry initialized (env=%s traces=%s)",
            _settings_value("sentry_environment") or "unknown",
            _settings_value("sentry_traces_sample_rate", 0.1),
        )
        return True
    except Exception as exc:  # pragma: no cover - never block startup
        logger.warning("[observability] Sentry init failed: %s", exc)
        return False


def _sentry_before_send(event: dict, hint: dict) -> dict | None:
    """Strip common sensitive headers/cookies from outgoing events."""
    try:
        request = event.get("request") or {}
        headers = request.get("headers") or {}
        for h in list(headers.keys()):
            if h.lower() in {
                "authorization",
                "cookie",
                "x-api-key",
                "x-auth-token",
                "stripe-signature",
                "x-meta-webhook-secret",
            }:
                headers[h] = "[Filtered]"
        if "cookies" in request:
            request["cookies"] = "[Filtered]"
    except Exception:
        pass  # never break error reporting
    return event


def bind_request_context(
    *,
    tenant_id: str | None = None,
    user_id: str | None = None,
    request_id: str | None = None,
    path: str | None = None,
    method: str | None = None,
) -> None:
    """
    Attach per-request context to the current Sentry scope.

    Call this from an ASGI middleware after we've resolved the tenant/user from
    the incoming request. Safe when Sentry is disabled.
    """
    if not _SENTRY_INITIALIZED:
        return
    try:
        import sentry_sdk

        scope = sentry_sdk.get_current_scope()
        if tenant_id:
            scope.set_tag("tenant_id", tenant_id)
        if user_id:
            scope.set_user({"id": user_id})
        if request_id:
            scope.set_tag("request_id", request_id)
        if path:
            scope.set_tag("http.path", path)
        if method:
            scope.set_tag("http.method", method)
    except Exception:
        pass  # never let observability break the request


def logging_dict_config() -> dict:
    """
    Return a dictConfig for `logging.config.dictConfig`.

    Format is controlled by `settings.log_format`:
      * "json" — JSON lines, safe for Datadog/Loki/ELK ingestion
      * "text" (default) — human-readable, matches previous behavior

    Structured fields included in JSON mode: asctime, level, name, message,
    pathname, lineno, funcName, plus any `extra={...}` dict from `logger.info(...)`.
    """
    log_format = str(_settings_value("log_format", "text") or "text").lower()
    log_level = str(_settings_value("log_level", "INFO") or "INFO").upper()

    if log_format == "json":
        try:
            # Validate the JSON formatter module exists; if not, fall back to text.
            import pythonjsonlogger  # type: ignore  # noqa: F401
        except ImportError:
            log_format = "text"

    if log_format == "json":
        formatter = {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": (
                "%(asctime)s %(name)s %(levelname)s %(message)s "
                "%(pathname)s %(lineno)d %(funcName)s"
            ),
            "rename_fields": {"levelname": "level", "asctime": "timestamp"},
        }
    else:
        formatter = {"format": "%(levelname)s:%(name)s:%(message)s"}

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"default": formatter},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {"level": log_level, "handlers": ["console"]},
        "loggers": {
            "backend.app": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
            "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn.error": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "aiosqlite": {"level": "WARNING"},
            "passlib": {"level": "WARNING"},
            "sqlalchemy.engine": {"level": "WARNING"},
            "sqlalchemy.pool": {"level": "WARNING"},
        },
    }


def is_sentry_enabled() -> bool:
    """True if `init_sentry()` succeeded at any point."""
    return _SENTRY_INITIALIZED
