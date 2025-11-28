from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select

from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.app.core.config import settings
from backend.app.core.security import verify_password
from backend.app.db.session import async_session_maker
from backend.app.models.user import Role as UserRole
from backend.app.models.user import User
from backend.app.schemas.user import UserDetailOut, UserInviteAccept
from backend.app.services import users as users_service
from backend.app.services.users import UserServiceError

router = APIRouter()

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"

_user_memberships = sa.table(
    "user_memberships",
    sa.column("user_id"),
    sa.column("tenant_id"),
    sa.column("role"),
)

_ROLE_MAP = {
    "owner": UserRole.administrator.value,
    "admin": UserRole.administrator.value,
    "administrator": UserRole.administrator.value,
    "manager": UserRole.supervisor.value,
    "supervisor": UserRole.supervisor.value,
    "recruiter": UserRole.recruiter.value,
    "viewer": UserRole.viewer.value,
    "client_manager": UserRole.client_manager.value,
    "client": UserRole.client_manager.value,
    "superadmin": UserRole.superadmin.value,
}

class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    session_id: str | None = None


def _normalize_role(
    user_role: Any,
    membership_role: Optional[str],
) -> str:
    raw_user_role = str(user_role or "").lower()
    if raw_user_role == UserRole.superadmin.value:
        return UserRole.superadmin.value
    if isinstance(user_role, UserRole) and user_role == UserRole.superadmin:
        return UserRole.superadmin.value
    if membership_role:
        mapped = _ROLE_MAP.get(str(membership_role).lower())
        if mapped:
            return mapped
    if isinstance(user_role, UserRole):
        return user_role.value
    raw = str(user_role or UserRole.viewer.value).lower()
    return _ROLE_MAP.get(raw, UserRole.viewer.value)


@router.post(
    "/login", response_model=TokenOut, tags=["auth"], summary="Auth Login"
)
async def auth_login(payload: LoginIn, request: Request) -> TokenOut:
    """
    Проверяет email/пароль по базе и выдаёт подписанный access-токен.
    """
    email = payload.email.lower().strip()
    password = payload.password

    async with async_session_maker() as session:
        row = await session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        user = row.scalar_one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        membership_row = await session.execute(
            select(
                _user_memberships.c.tenant_id,
                _user_memberships.c.role,
            )
            .where(_user_memberships.c.user_id == user.id)
            .limit(1)
        )
        membership = membership_row.first()

        tenant_id = user.tenant_id or (membership.tenant_id if membership else DEFAULT_TENANT_ID)
        membership_role = membership.role if membership else None
        role_value = _normalize_role(user.role, membership_role)

        now = datetime.now(timezone.utc)
        ttl_minutes = max(5, int(getattr(settings, "auth_token_ttl_minutes", 720) or 720))
        exp = now + timedelta(minutes=ttl_minutes)

        token_payload: Dict[str, Any] = {
            "sub": user.id,
            "email": email,
            "role": role_value,
            "tenant_id": tenant_id,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        token = encode_jwt(token_payload)

        client_host = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        device_label = request.headers.get("X-Device-Name")
        session_entry = await users_service.register_user_session(
            session,
            tenant_id=tenant_id,
            user_id=user.id,
            ip_address=client_host,
            user_agent=user_agent,
            device_label=device_label,
            expires_at=exp,
        )
        await session.commit()

    return TokenOut(
        access_token=token,
        user={"id": user.id, "email": email, "role": role_value, "tenant_id": tenant_id},
        session_id=session_entry.id,
    )


@router.post("/invite/accept", response_model=UserDetailOut, tags=["auth"])
async def auth_invite_accept(payload: UserInviteAccept) -> UserDetailOut:
    async with async_session_maker() as session:
        try:
            detail = await users_service.accept_invite(
                session,
                token=payload.token,
                password=payload.password,
                full_name=payload.full_name,
                short_id=payload.short_id,
            )
            await session.commit()
        except UserServiceError as exc:
            await session.rollback()
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except Exception:
            await session.rollback()
            raise
    return UserDetailOut(**detail)
