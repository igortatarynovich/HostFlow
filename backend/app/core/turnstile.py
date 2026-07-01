"""
Cloudflare Turnstile (invisible CAPTCHA) verification.

Why Turnstile (and not reCAPTCHA)
---------------------------------
* No Google tracking / cookies / ads attribution — cleaner GDPR story.
* Free, unlimited, privacy-preserving.
* Invisible by default; only shows a challenge when traffic looks suspicious.

Lifecycle
---------
1. Operator creates a Turnstile widget in Cloudflare dashboard, gets a
   `site_key` (public) and `secret_key` (server-side).
2. Frontend renders the widget with `site_key`, user (or their browser)
   completes the challenge, frontend receives a `cf-turnstile-response` token.
3. Frontend submits token alongside the form (e.g. as `turnstile_token`).
4. Backend calls `verify_turnstile(token, client_ip)` — a POST to Cloudflare's
   siteverify endpoint with our `secret_key`.

When Turnstile is **disabled** (no secret key), all verification calls return
True — i.e. no gating. This keeps local dev and CI fully green without any
env wiring.

Usage inside an endpoint
------------------------
    from backend.app.core.turnstile import require_turnstile

    @router.post("/register")
    async def register(payload: RegisterIn, request: Request):
        await require_turnstile(request, token=payload.turnstile_token)
        ...
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def is_turnstile_enabled() -> bool:
    """True if operator configured a secret key and left turnstile_enabled on."""
    try:
        from backend.app.core.settings import settings

        return bool(settings.turnstile_enabled and settings.turnstile_secret_key)
    except Exception:
        return False


def get_turnstile_sitekey() -> Optional[str]:
    """Public site key — safe to expose to the browser."""
    try:
        from backend.app.core.settings import settings

        if not settings.turnstile_enabled:
            return None
        return settings.turnstile_sitekey
    except Exception:
        return None


async def verify_turnstile(token: Optional[str], client_ip: Optional[str]) -> bool:
    """
    Validate a Turnstile token against Cloudflare's siteverify endpoint.

    * Returns True when Turnstile is disabled (no gating).
    * Returns False on any error or unsuccessful verification.
    * Never raises — the caller decides whether to translate False into HTTP.
    """
    if not is_turnstile_enabled():
        return True
    if not token:
        return False
    try:
        from backend.app.core.settings import settings

        # Lazy import so httpx is only required when Turnstile is actually used.
        import httpx

        data = {"secret": settings.turnstile_secret_key, "response": token}
        if client_ip:
            data["remoteip"] = client_ip

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(settings.turnstile_verify_url, data=data)
        if resp.status_code != 200:
            logger.warning("[turnstile] siteverify http %s", resp.status_code)
            return False
        body = resp.json()
        ok = bool(body.get("success"))
        if not ok:
            logger.info("[turnstile] challenge failed: %s", body.get("error-codes"))
        return ok
    except Exception as exc:  # pragma: no cover - network/time outs
        logger.warning("[turnstile] verify error: %s", exc)
        return False


async def require_turnstile(request: Request, *, token: Optional[str]) -> None:
    """
    FastAPI helper: raise HTTPException(400) when Turnstile is required and
    the submitted token is invalid. No-op when Turnstile is disabled.
    """
    if not is_turnstile_enabled():
        return
    client_ip = request.client.host if request.client else None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        client_ip = xff.split(",")[0].strip() or client_ip
    if not await verify_turnstile(token, client_ip):
        raise HTTPException(
            status_code=400,
            detail={"code": "captcha_failed", "message": "Please complete the challenge and try again."},
        )
