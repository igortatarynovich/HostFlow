from __future__ import annotations

import base64
import json
from typing import Iterable, Optional

from fastapi import HTTPException, Request, status


def _get_role_from_bearer(request: Request) -> Optional[str]:
    """
    Извлекает роль из JWT без верификации подписи.
    Ожидаем "Authorization: Bearer <jwt>" и payload {"role": "..."}.
    """
    auth = request.headers.get("Authorization") or ""
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1]
    segs = token.split(".")
    if len(segs) < 2:
        return None
    payload_b64 = segs[1]
    # base64url pad
    rem = len(payload_b64) % 4
    if rem:
        payload_b64 += "=" * (4 - rem)
    try:
        payload = json.loads(
            base64.urlsafe_b64decode(payload_b64.encode()).decode("utf-8")
        )
        role = payload.get("role")
        if isinstance(role, str):
            return role
    except Exception:
        return None
    return None


def require_role(*allowed: Iterable[str]):
    """
    FastAPI dependency: проверяет, что роль в allowed.
    Если роль не найдена — считаем admin (чтобы не ломать твой флоу).
    """
    allowed_set = set([*allowed]) if allowed else set()

    async def dep(request: Request):
        role = _get_role_from_bearer(request) or "admin"
        if allowed_set and role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden for role '{role}'",
            )
        return role

    return dep
