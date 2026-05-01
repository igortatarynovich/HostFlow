from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, Iterator

import jwt  # PyJWT
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.settings import settings

# TODO: add FastAPI router for /api/v1/ping that returns {"ok": true}

ALGO = "HS256"
bearer = HTTPBearer(auto_error=False)


class Role(str, Enum):
    superadmin = "superadmin"
    administrator = "administrator"
    supervisor = "supervisor"
    recruiter = "recruiter"
    client_manager = "client_manager"
    client_processor = "client_processor"  # Handoff: accepts/processes candidates from agency
    compliance_officer = "compliance_officer"  # Process documents (work permit, residence card, tacho, etc.)
    hr_officer = "hr_officer"  # HR / people workspace (employees, isolated from recruitment)
    viewer = "viewer"
    admin = administrator
    owner = administrator
    manager = supervisor
    hr = recruiter
    user = viewer
    client = client_manager


ROLE_VALUES = {r.value for r in Role}
ROLE_ALIASES = {
    "admin": Role.administrator.value,
    "owner": Role.administrator.value,
    "manager": Role.supervisor.value,
    "supervisor": Role.supervisor.value,
    "recruiter": Role.recruiter.value,
    "hr": Role.recruiter.value,
    "user": Role.viewer.value,
    "viewer": Role.viewer.value,
    "client": Role.client_manager.value,
    "client_manager": Role.client_manager.value,
    "client_processor": Role.client_processor.value,
    "processor": Role.client_processor.value,
    "compliance_officer": Role.compliance_officer.value,
    "compliance": Role.compliance_officer.value,
    "docs_officer": Role.compliance_officer.value,
    "hr_officer": Role.hr_officer.value,
    "people_ops": Role.hr_officer.value,
    "superadmin": Role.superadmin.value,
}


def _secret() -> str:
    # ЕДИНАЯ точка правды для всех проверок
    return settings.jwt_secret or "hostflow-dev-secret"


@dataclass
class UserCtx:
    sub: str
    email: str
    role: str  # payload может прийти строкой
    tenant_id: str
    supervisor_id: str | None
    raw: Dict[str, Any]


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> UserCtx:
    if not cred or not cred.scheme or cred.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = cred.credentials
    try:
        data = jwt.decode(token, key=_secret(), algorithms=[ALGO])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    sub = str(data.get("sub") or "").strip()
    email = str(data.get("email") or "").strip()

    # Normalize role: accept either a single "role" claim or first value from "roles" list; default to "user"
    raw_role: str | None = None
    if "role" in data and data.get("role") is not None:
        raw_role = str(data.get("role"))
    elif isinstance(data.get("roles"), (list, tuple)) and data.get("roles"):
        raw_role = str(data["roles"][0])

    role = (raw_role or Role.viewer.value).strip().lower()
    if role not in ROLE_VALUES:
        role = ROLE_ALIASES.get(role, Role.viewer.value)

    tenant_id = str(data.get("tenant_id") or "").strip()

    if not sub or not email:
        raise HTTPException(status_code=401, detail="Invalid token")

    supervisor_id_val = data.get("supervisor_id")
    if supervisor_id_val is not None:
        supervisor_id = str(supervisor_id_val or "").strip() or None
    else:
        supervisor_id = None

    return UserCtx(
        sub=sub,
        email=email,
        role=role,
        tenant_id=tenant_id,
        supervisor_id=supervisor_id,
        raw=data,
    )


def _flatten_allowed(items: Iterable[object]) -> Iterator[object]:
    """
    Accept nested iterables (lists/tuples/sets) but keep strings as atomic values.
    """
    for item in items:
        if isinstance(item, (list, tuple, set, frozenset)):
            yield from _flatten_allowed(item)
        else:
            yield item


def _normalize_role_value(value: object) -> str | None:
    if isinstance(value, Role):
        return value.value.lower()
    raw = getattr(value, "value", None)
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        return ROLE_ALIASES.get(lowered, lowered)
    if isinstance(value, str):
        lowered = value.strip().lower()
        return ROLE_ALIASES.get(lowered, lowered)
    text = str(value or "").strip().lower()
    if not text:
        return None
    return ROLE_ALIASES.get(text, text)


def _to_values(allowed: Iterable[object]) -> set[str]:
    vals: set[str] = set()
    for entry in _flatten_allowed(allowed):
        normalized = _normalize_role_value(entry)
        if normalized:
            vals.add(normalized)
    return vals


def require_roles(*allowed: object):
    allowed_values = _to_values(allowed)

    async def _checker(u: UserCtx = Depends(get_current_user)) -> str:
        ur = (u.role or "").lower()
        # Always allow platform/super admins
        if ur in {Role.superadmin.value, Role.administrator.value}:
            return ur

        # If a role list is provided, enforce it for non-admins
        if allowed_values and ur not in allowed_values:
            raise HTTPException(status_code=403, detail="Forbidden")
        return ur

    return _checker


def require_superadmin():
    async def _checker(u: UserCtx = Depends(get_current_user)) -> str:
        if u.role != Role.superadmin.value:
            raise HTTPException(status_code=403, detail="Forbidden")
        return u.role

    return _checker
