"""Stage 6B — shared session cookies for Domain=.hostflow.cc (ADR-023 §3.7)."""
from __future__ import annotations

import os
import secrets
from typing import Any
from urllib.parse import urlparse

from fastapi import Request, Response

from backend.app.constants.module_deploy_hosts import (
    deployment_hosts,
    load_module_deploy_registry,
)

ACCESS_COOKIE = "hf_access"
REFRESH_COOKIE = "hf_refresh"
CSRF_COOKIE = "hf_csrf"
CSRF_HEADER = "X-CSRF-Token"

# Paths that may mutate session without a prior CSRF cookie.
CSRF_EXEMPT_PATH_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/password/",
    "/api/v1/auth/invite/",
    "/api/v1/auth/logout",
    # Bearer → Domain=.hostflow.cc cookie mint (cross-subdomain handoff).
    "/api/v1/auth/session/sync",
    "/healthz",
)


def session_cookie_names() -> dict[str, str]:
    registry = load_module_deploy_registry()
    cfg = registry.get("session_cookies") or {}
    return {
        "access": str(cfg.get("access") or ACCESS_COOKIE),
        "refresh": str(cfg.get("refresh") or REFRESH_COOKIE),
        "csrf": str(cfg.get("csrf") or CSRF_COOKIE),
        "domain": str(cfg.get("domain") or registry.get("cookie_domain") or ".hostflow.cc"),
        "samesite": str(cfg.get("samesite") or "lax").lower(),
    }


def _request_hostname(request: Request) -> str:
    host = (request.url.hostname or "").strip().lower()
    if host:
        return host
    # Prefer forwarded host when behind Caddy/nginx
    forwarded = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip().lower()
    if forwarded:
        return forwarded.split(":")[0]
    return ""


def use_parent_cookie_domain(request: Request) -> bool:
    """True when request is on hostflow.cc family (production / staging subdomains)."""
    host = _request_hostname(request)
    if not host or host in {"localhost", "127.0.0.1"}:
        return False
    apex = str(load_module_deploy_registry().get("apex_domain") or "hostflow.cc")
    return host == apex or host.endswith(f".{apex}")


def cookie_secure(request: Request) -> bool:
    env = (os.environ.get("AUTH_COOKIE_SECURE") or "").strip().lower()
    if env in {"1", "true", "yes"}:
        return True
    if env in {"0", "false", "no"}:
        return False
    if request.url.scheme == "https":
        return True
    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    return proto == "https"


def cookie_common_kwargs(request: Request) -> dict[str, Any]:
    names = session_cookie_names()
    samesite = names["samesite"]
    if samesite not in {"lax", "strict", "none"}:
        samesite = "lax"
    kwargs: dict[str, Any] = {
        "path": "/",
        "secure": cookie_secure(request),
        "samesite": samesite,
    }
    if use_parent_cookie_domain(request):
        kwargs["domain"] = names["domain"]
    return kwargs


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_session_cookies(
    response: Response,
    request: Request,
    *,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
    access_max_age: int,
    refresh_max_age: int,
) -> None:
    names = session_cookie_names()
    common = cookie_common_kwargs(request)
    # When writing Domain=.hostflow.cc cookies, drop legacy host-only copies first.
    # Otherwise shell keeps a host-only session while module hosts see nothing → redirect loop.
    if "domain" in common:
        for key in (names["access"], names["refresh"], names["csrf"]):
            response.delete_cookie(key=key, path="/")
    response.set_cookie(
        key=names["access"],
        value=access_token,
        max_age=access_max_age,
        httponly=True,
        **common,
    )
    response.set_cookie(
        key=names["refresh"],
        value=refresh_token,
        max_age=refresh_max_age,
        httponly=True,
        **common,
    )
    # Readable by SPA for double-submit CSRF header.
    response.set_cookie(
        key=names["csrf"],
        value=csrf_token,
        max_age=refresh_max_age,
        httponly=False,
        **common,
    )


def clear_session_cookies(response: Response, request: Request) -> None:
    names = session_cookie_names()
    common = cookie_common_kwargs(request)
    for key in (names["access"], names["refresh"], names["csrf"]):
        response.delete_cookie(key=key, path="/", domain=common.get("domain"))
        # Also clear host-only variants from older local sessions.
        if "domain" in common:
            response.delete_cookie(key=key, path="/")


def read_access_token(request: Request) -> str | None:
    names = session_cookie_names()
    raw = request.cookies.get(names["access"])
    return str(raw).strip() if raw else None


def read_refresh_token(request: Request) -> str | None:
    names = session_cookie_names()
    raw = request.cookies.get(names["refresh"])
    return str(raw).strip() if raw else None


def read_csrf_cookie(request: Request) -> str | None:
    names = session_cookie_names()
    raw = request.cookies.get(names["csrf"])
    return str(raw).strip() if raw else None


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def resolve_access_token(request: Request, authorization: str | None = None) -> str | None:
    """Prefer Authorization Bearer (API clients / e2e), else shared access cookie."""
    bearer = extract_bearer_token(authorization if authorization is not None else request.headers.get("authorization"))
    if bearer:
        return bearer
    return read_access_token(request)


def csrf_header_value(request: Request) -> str | None:
    return (request.headers.get(CSRF_HEADER) or request.headers.get("x-csrf-token") or "").strip() or None


def path_is_csrf_exempt(path: str) -> bool:
    p = path or ""
    return any(p == prefix or p.startswith(prefix) for prefix in CSRF_EXEMPT_PATH_PREFIXES)


def requires_csrf_for_request(request: Request) -> bool:
    method = (request.method or "GET").upper()
    if method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return False
    if path_is_csrf_exempt(request.url.path):
        return False
    # Double-submit: when CSRF cookie is present (browser session), always require header —
    # even if SPA also sends Authorization Bearer from localStorage dual-write.
    if read_csrf_cookie(request):
        return True
    # Cookie access/refresh without csrf cookie — protect cookie-only callers.
    if read_access_token(request) or read_refresh_token(request):
        if extract_bearer_token(request.headers.get("authorization")):
            return False
        return True
    return False


def csrf_ok(request: Request) -> bool:
    cookie = read_csrf_cookie(request)
    header = csrf_header_value(request)
    if not cookie or not header:
        return False
    return secrets.compare_digest(cookie, header)


def cors_allowed_origins() -> set[str]:
    origins: set[str] = {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    }
    extra = (os.environ.get("CORS_ALLOWED_ORIGINS") or "").strip()
    if extra:
        for part in extra.split(","):
            value = part.strip().rstrip("/")
            if value:
                origins.add(value)

    hosts = list(deployment_hosts().values())
    hosts.append("www.hostflow.cc")
    for host in hosts:
        origins.add(f"https://{host}")
        # Local/staging HTTP mirrors (optional).
        origins.add(f"http://{host}")
    return origins


def origin_is_allowed(origin: str | None, allowed: set[str] | None = None) -> bool:
    if not origin:
        return False
    pool = allowed if allowed is not None else cors_allowed_origins()
    if origin in pool:
        return True
    # Allow any https://*.hostflow.cc that matches registry apex (defense in depth).
    try:
        parsed = urlparse(origin)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    apex = str(load_module_deploy_registry().get("apex_domain") or "hostflow.cc")
    if host == apex or host.endswith(f".{apex}"):
        return True
    return False
