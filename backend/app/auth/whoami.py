from __future__ import annotations

from typing import Any, Dict, Optional

import jwt  # PyJWT
from fastapi import APIRouter, Header, HTTPException

from backend.app.auth.jwt_tools import decode

router = APIRouter()


def _extract_bearer(auth_header: Optional[str]) -> str:
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header format"
        )
    return parts[1]


@router.get("/whoami")
def whoami(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    token = _extract_bearer(authorization)
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
    }


@router.get("/whoami-verify")
def whoami_verify(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    token = _extract_bearer(authorization)
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
    }
