from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, Iterator, Optional

import jwt  # PyJWT
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.settings import settings
from backend.app.auth.session_cookies import extract_bearer_token, read_access_token

# TODO: add FastAPI router for /api/v1/ping that returns {"ok": true}

ALGO = "HS256"
bearer = HTTPBearer(auto_error=False)


class Role(str, Enum):
    """JWT / require_roles storage values. Canonical trust = ADR-036 (see trust_roles).

    Job-title and portal strings are aliases normalized via ROLE_ALIASES / trust_roles;
    they are not distinct enum members after Phase 3 remap.
    """

    superadmin = "superadmin"
    administrator = "administrator"
    employee = "employee"
    viewer = "viewer"
    admin = administrator
    owner = administrator


ROLE_VALUES = {r.value for r in Role}
ROLE_ALIASES = {
    "admin": Role.administrator.value,
    "owner": Role.administrator.value,
    "employee": Role.employee.value,
    "manager": Role.employee.value,
    "supervisor": Role.employee.value,
    "recruiter": Role.employee.value,
    "hr": Role.employee.value,
    "user": Role.viewer.value,
    "viewer": Role.viewer.value,
    "client": Role.viewer.value,
    "client_manager": Role.viewer.value,
    "client_processor": Role.viewer.value,
    "processor": Role.viewer.value,
    "compliance_officer": Role.employee.value,
    "compliance": Role.employee.value,
    "docs_officer": Role.employee.value,
    "hr_officer": Role.employee.value,
    "people_ops": Role.employee.value,
    "superadmin": Role.superadmin.value,
    "lead": Role.employee.value,
}


def _secret() -> str:
    # ЕДИНАЯ точка правды для всех проверок
    return settings.jwt_secret or "hostflow-dev-secret"


@dataclass
class UserCtx:
    sub: str
    email: str
    role: str  # payload может прийти строкой (legacy or canonical)
    tenant_id: str
    supervisor_id: str | None
    raw: Dict[str, Any]
    access_context: str = "tenant"  # ADR-036: tenant | portal (orthogonal to role)
    preset_id: str | None = None  # ADR-036 permission preset (orthogonal to trust role)


def _user_ctx_from_decoded_jwt(data: Dict[str, Any]) -> UserCtx:
    sub = str(data.get("sub") or "").strip()
    email = str(data.get("email") or "").strip()

    raw_role: str | None = None
    if "role" in data and data.get("role") is not None:
        raw_role = str(data.get("role"))
    elif isinstance(data.get("roles"), (list, tuple)) and data.get("roles"):
        raw_role = str(data["roles"][0])

    from backend.app.auth.trust_roles import infer_access_context, normalize_trust_role, resolve_preset_id

    role_raw = (raw_role or Role.viewer.value).strip().lower()
    if role_raw in ROLE_VALUES:
        role = role_raw
    else:
        role = ROLE_ALIASES.get(role_raw, normalize_trust_role(role_raw))

    tenant_id = str(data.get("tenant_id") or "").strip()

    if not sub or not email:
        raise ValueError("missing sub/email")

    supervisor_id_val = data.get("supervisor_id")
    if supervisor_id_val is not None:
        supervisor_id = str(supervisor_id_val or "").strip() or None
    else:
        supervisor_id = None

    explicit_ctx = data.get("access_context")
    access_context = infer_access_context(
        role_raw,
        str(explicit_ctx).strip().lower() if explicit_ctx is not None else None,
    )
    jwt_preset = data.get("preset_id")
    preset_id = resolve_preset_id(
        role_raw,
        explicit=str(jwt_preset).strip().lower() if jwt_preset is not None else None,
    )

    return UserCtx(
        sub=sub,
        email=email,
        role=role,
        tenant_id=tenant_id,
        supervisor_id=supervisor_id,
        raw=data,
        access_context=access_context,
        preset_id=preset_id,
    )


def _decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, key=_secret(), algorithms=[ALGO])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def _token_sub(token: str) -> str | None:
    try:
        data = jwt.decode(token, key=_secret(), algorithms=[ALGO])
    except Exception:
        return None
    sub = str(data.get("sub") or "").strip()
    return sub or None


def _resolve_request_access_token(
    request: Request,
    cred: HTTPAuthorizationCredentials | None,
) -> str | None:
    """
    Prefer Authorization Bearer when present, else Domain cookie.
    If both exist and ``sub`` differs, prefer the shared cookie (stale per-origin Bearer).
    """
    authorization = None
    if cred and cred.scheme and cred.scheme.lower() == "bearer" and cred.credentials:
        authorization = f"Bearer {cred.credentials}"
    bearer_tok = extract_bearer_token(authorization)
    cookie_tok = read_access_token(request)
    if bearer_tok and cookie_tok:
        b_sub = _token_sub(bearer_tok)
        c_sub = _token_sub(cookie_tok)
        if b_sub and c_sub and b_sub != c_sub:
            return cookie_tok
        if b_sub:
            return bearer_tok
        if c_sub:
            return cookie_tok
        return bearer_tok
    return bearer_tok or cookie_tok


async def get_current_user(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> UserCtx:
    token = _resolve_request_access_token(request, cred)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    data = _decode_access_token(token)

    try:
        user = _user_ctx_from_decoded_jwt(data)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        from backend.app.security.runtime_context import set_security_actor_id

        set_security_actor_id(str(user.sub))
    except Exception:
        pass
    return user


async def get_current_user_optional(
    request: Request,
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Optional[UserCtx]:
    """Same JWT validation as get_current_user, but missing session yields None (no 401)."""
    token = _resolve_request_access_token(request, cred)
    if not token:
        return None
    data = _decode_access_token(token)
    try:
        user = _user_ctx_from_decoded_jwt(data)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        from backend.app.security.runtime_context import set_security_actor_id

        set_security_actor_id(str(user.sub))
    except Exception:
        pass
    return user


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
    from backend.app.auth.trust_roles import actor_satisfies_role_allowlist

    allowed_values = _to_values(allowed)

    async def _checker(u: UserCtx = Depends(get_current_user)) -> str:
        ur = (u.role or "").lower()
        # Always allow platform/super admins
        if ur in {Role.superadmin.value, Role.administrator.value}:
            return ur

        # If a role list is provided, enforce it for non-admins (ADR-036 bridges)
        if allowed_values and not actor_satisfies_role_allowlist(
            role=ur,
            allowed=allowed_values,
            access_context=getattr(u, "access_context", None),
        ):
            raise HTTPException(status_code=403, detail="Forbidden")
        return ur

    return _checker


def require_superadmin():
    async def _checker(u: UserCtx = Depends(get_current_user)) -> str:
        if u.role != Role.superadmin.value:
            raise HTTPException(status_code=403, detail="Forbidden")
        return u.role

    return _checker
