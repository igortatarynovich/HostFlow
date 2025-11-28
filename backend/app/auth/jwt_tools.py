from __future__ import annotations

from typing import Any, Dict

import jwt  # PyJWT
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from fastapi import HTTPException

from backend.app.core.settings import settings

ALGO = "HS256"


def _secret() -> str:
    """Return JWT secret.

    In non-dev environments, require an explicit secret to avoid insecure fallback.
    """
    if settings.jwt_secret:
        return settings.jwt_secret
    # Assume `settings.env` holds environment name; fall back only in dev
    env = getattr(settings, "env", "dev")
    if env != "dev":
        raise RuntimeError("JWT secret is not configured for non-dev environment")
    return "hostflow-dev-secret"


def encode(payload: Dict[str, Any]) -> str:
    """Encode a JWT and always return a string.

    PyJWT may return `bytes` in some versions; normalize to `str`.
    """
    token = jwt.encode(payload, _secret(), algorithm=ALGO)
    if isinstance(token, bytes):
        return token.decode("utf-8")
    return token


def decode(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT.

    Verifies signature and expiration; raises 401-friendly HTTPException on failure.
    Requires `exp` claim to be present.
    """
    try:
        return jwt.decode(
            token,
            key=_secret(),
            algorithms=[ALGO],
            options={"require": ["exp"], "verify_exp": True},
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
