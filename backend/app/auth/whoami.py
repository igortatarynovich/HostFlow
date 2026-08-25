from __future__ import annotations

from typing import Any, Dict, Optional

import jwt  # PyJWT
from fastapi import APIRouter, Header, HTTPException, Request

from backend.app.auth.jwt_tools import decode
from backend.app.auth.session_cookies import resolve_access_token

router = APIRouter()


def _require_access_token(
    request: Request, authorization: Optional[str] = None
) -> str:
    """Bearer first, else shared Domain=.hostflow.cc access cookie (Stage 6B)."""
    token = resolve_access_token(request, authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    return token


def _session_kind_from_payload(payload: Dict[str, Any]) -> str:
    raw_type = str(payload.get("type") or "").strip().lower()
    if raw_type == "impersonation":
        return "impersonation"
    return "normal"


def _session_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    kind = _session_kind_from_payload(payload)
    out: Dict[str, Any] = {"session_kind": kind}
    if kind == "impersonation":
        out["impersonated_by"] = payload.get("impersonated_by")
    return out


@router.get("/whoami")
def whoami(
    request: Request, authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    token = _require_access_token(request, authorization)
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    return {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role"),
        "tenant_id": payload.get("tenant_id"),
        "iat": payload.get("iat"),
        "exp": payload.get("exp"),
        "raw": payload,
        **_session_fields(payload),
    }


@router.get("/whoami-verify")
def whoami_verify(
    request: Request, authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    token = _require_access_token(request, authorization)
    try:
        payload = decode(token)
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Signature verification failed: {e}"
        )
    return {
        "verified_with": "settings.jwt_secret (HS256)",
        "email": payload.get("email"),
        "sub": payload.get("sub"),
        "role": payload.get("role"),
        "tenant_id": payload.get("tenant_id"),
        "iat": payload.get("iat"),
        "exp": payload.get("exp"),
        **_session_fields(payload),
    }
