"""
Rate limiting for public endpoints (Phase 0 audit plan).

Why an imperative helper and not `@limiter.limit(...)` decorators
-----------------------------------------------------------------
Our handlers live in modules that start with `from __future__ import
annotations`. Under that mode every type hint becomes a string at import
time, so when `slowapi` wraps the function with `functools.wraps`, FastAPI's
route introspection can no longer resolve `payload: LoginIn` to a Pydantic
model — it falls back to treating the body as a query parameter and returns
422 "missing field: payload". That's a known interaction (see slowapi
issue tracker).

To avoid wrapping the function at all, we expose a single coroutine,
`enforce_rate_limit(request, limit_str, scope=...)`, that handlers can call
in their body. It uses the same `limits`-library storage as slowapi (Redis
when REDIS_URL is set, memory otherwise), so limits are consistent across
workers and survive restarts.

Usage
-----
    from backend.app.core.rate_limit import enforce_rate_limit, rate_limits

    @router.post("/login")
    async def auth_login(payload: LoginIn, request: Request):
        await enforce_rate_limit(request, rate_limits().login, scope="login")
        ...

Keys
----
Clients are identified by IP. Behind a proxy (Caddy, Nginx, Cloudflare) we
trust `X-Forwarded-For` ONLY when `TRUSTED_PROXY_HOPS > 0` is set, to avoid
spoofed rate-limit bypass. Locally we use `request.client.host`.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import HTTPException
from starlette.requests import Request

logger = logging.getLogger(__name__)

# `limits` is slowapi's underlying engine (pip install limits, pulled via slowapi).
# We use it directly to avoid the decorator-wrapping FastAPI introspection hazard.
try:
    from limits import parse as _parse_limit
    from limits.storage import storage_from_string
    from limits.strategies import FixedWindowRateLimiter
    _LIMITS_AVAILABLE = True
except ImportError:  # pragma: no cover - defensive
    _LIMITS_AVAILABLE = False
    _parse_limit = None  # type: ignore[assignment]
    storage_from_string = None  # type: ignore[assignment]
    FixedWindowRateLimiter = None  # type: ignore[assignment,misc]


TRUSTED_PROXY_HOPS = int(os.environ.get("TRUSTED_PROXY_HOPS", "0") or "0")


def _client_key(request: Request) -> str:
    """
    Return a stable client key for rate-limiting.

    Prefers `X-Forwarded-For` (last `TRUSTED_PROXY_HOPS` entries from the right
    are treated as trusted infrastructure), then `X-Real-IP`, then
    `request.client.host`. Never returns empty — falls back to "anonymous".

    Behind Caddy/nginx, `TRUSTED_PROXY_HOPS` MUST be >= 1; otherwise every
    browser shares the proxy container IP and auth endpoints 429 globally.
    """
    if TRUSTED_PROXY_HOPS > 0:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            # Walk from the right, skipping TRUSTED_PROXY_HOPS trusted hops.
            idx = max(0, len(parts) - 1 - TRUSTED_PROXY_HOPS)
            if 0 <= idx < len(parts):
                return parts[idx]
        real_ip = (request.headers.get("x-real-ip") or "").strip()
        if real_ip:
            return real_ip.split(",")[0].strip() or real_ip
    return (request.client.host if request.client else "") or "anonymous"


def _storage_uri() -> str:
    """Pick storage backend. Redis → memory fallback."""
    try:
        from backend.app.core.settings import settings

        override = settings.rate_limit_storage_url
    except Exception:
        override = os.environ.get("RATE_LIMIT_STORAGE_URL")
    if override:
        return override
    redis_url = os.environ.get("REDIS_URL")
    return redis_url or "memory://"


def _is_enabled() -> bool:
    if not _LIMITS_AVAILABLE:
        return False
    try:
        from backend.app.core.settings import settings

        return bool(settings.rate_limit_enabled)
    except Exception:
        return os.environ.get("RATE_LIMIT_ENABLED", "true").lower() not in {"0", "false", "no"}


_storage: Any = None
_strategy: Any = None


def _get_strategy() -> Optional[Any]:
    """Lazy-init the storage + FixedWindow strategy (shared across requests)."""
    global _storage, _strategy
    if _strategy is not None:
        return _strategy
    if not _LIMITS_AVAILABLE:
        return None
    try:
        _storage = storage_from_string(_storage_uri())
        _strategy = FixedWindowRateLimiter(_storage)
        return _strategy
    except Exception as exc:  # pragma: no cover - Redis unavailable at boot
        logger.warning("[rate-limit] storage init failed (%s); falling back to memory", exc)
        try:
            _storage = storage_from_string("memory://")
            _strategy = FixedWindowRateLimiter(_storage)
            return _strategy
        except Exception:
            return None


# Back-compat: keep a `limiter` handle with `.enabled` so existing callers (and
# startup logs) don't break. Not used for decoration anywhere.
class _LimiterHandle:
    @property
    def enabled(self) -> bool:
        return _is_enabled() and _get_strategy() is not None


limiter = _LimiterHandle()


class _Limits:
    """
    Snapshot of rate-limit strings, read from settings.

    Cached per-process; the values are used inside decorators and need to be
    resolvable at import time (before `settings` may have finished constructing
    on cold starts of certain test fixtures). Falls back to sensible defaults.
    """

    def __init__(self) -> None:
        self._cached: Optional[dict[str, str]] = None

    def _load(self) -> dict[str, str]:
        if self._cached is not None:
            return self._cached
        defaults = {
            "login": "10/minute",
            "session_sync": "60/minute",
            "refresh": "60/minute",
            "signup": "5/hour",
            "password_reset": "5/hour",
            "public_intake": "20/hour",
            "magic_link": "5/hour",
            "public_default": "60/minute",
        }
        try:
            from backend.app.core.settings import settings

            defaults.update(
                {
                    "login": settings.rate_limit_login,
                    "session_sync": settings.rate_limit_session_sync,
                    "refresh": settings.rate_limit_refresh,
                    "signup": settings.rate_limit_signup,
                    "password_reset": settings.rate_limit_password_reset,
                    "public_intake": settings.rate_limit_public_intake,
                    "magic_link": settings.rate_limit_magic_link,
                    "public_default": settings.rate_limit_public_default,
                }
            )
        except Exception:
            pass
        self._cached = defaults
        return defaults

    @property
    def login(self) -> str:
        return self._load()["login"]

    @property
    def session_sync(self) -> str:
        return self._load()["session_sync"]

    @property
    def refresh(self) -> str:
        return self._load()["refresh"]

    @property
    def signup(self) -> str:
        return self._load()["signup"]

    @property
    def password_reset(self) -> str:
        return self._load()["password_reset"]

    @property
    def public_intake(self) -> str:
        return self._load()["public_intake"]

    @property
    def magic_link(self) -> str:
        return self._load()["magic_link"]

    @property
    def public_default(self) -> str:
        return self._load()["public_default"]


_limits_instance = _Limits()


def rate_limits() -> _Limits:
    """Access configured rate-limit strings."""
    return _limits_instance


async def enforce_rate_limit(request: Request, limit_str: str, *, scope: str) -> None:
    """
    Consume one hit in the `scope` bucket for this client; raise 429 on overflow.

    * No-op when rate limiting is disabled or the `limits` engine isn't available.
    * `scope` distinguishes independent buckets (e.g. "login", "signup"). Without
      it, a single actor hitting many endpoints would share one counter.
    * `limit_str` follows the classic rate-limit DSL: "10/minute", "5/hour",
      "100 per day".
    """
    if not _is_enabled():
        return
    strategy = _get_strategy()
    if strategy is None or _parse_limit is None:
        return
    try:
        parsed = _parse_limit(limit_str)
    except Exception as exc:
        logger.warning("[rate-limit] invalid limit string %r: %s", limit_str, exc)
        return
    key = _client_key(request)
    try:
        allowed = strategy.hit(parsed, scope, key)
    except Exception as exc:  # pragma: no cover - Redis outage: fail-open
        logger.warning("[rate-limit] hit() error (%s); allowing request", exc)
        return
    if allowed:
        return
    retry_after: Optional[int] = None
    try:
        stats = strategy.get_window_stats(parsed, scope, key)
        # limits returns (reset_epoch, remaining) as WindowStats
        reset_epoch = int(getattr(stats, "reset_time", 0) or 0)
        import time as _time

        retry_after = max(1, reset_epoch - int(_time.time())) if reset_epoch else None
    except Exception:
        retry_after = None
    headers = {"Retry-After": str(retry_after)} if retry_after else None
    raise HTTPException(
        status_code=429,
        detail={
            "error": "rate_limited",
            "message": "Too many requests. Please try again later.",
            "scope": scope,
            "retry_after": retry_after,
        },
        headers=headers,
    )


def register_rate_limit(app) -> bool:
    """
    Log a startup line and expose the limiter on `app.state`. Kept for compat
    with `main.py`; no middleware or exception handlers are needed now that
    enforcement is imperative.
    """
    app.state.limiter = limiter
    enabled = _is_enabled() and _get_strategy() is not None
    logger.info(
        "[rate-limit] enabled=%s storage=%s",
        enabled,
        _storage_uri(),
    )
    return enabled
