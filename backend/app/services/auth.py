from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.session import AuthRefreshToken


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token(prefix: str = "") -> tuple[str, str]:
    """
    Generate a secure random token and return (raw, hashed)
    so the raw value can be sent to the user while the hash
    persists in storage.
    """
    raw = secrets.token_urlsafe(32)
    if prefix:
        raw = f"{prefix}_{raw}"
    return raw, hash_token(raw)


async def revoke_refresh_tokens(
    db: AsyncSession,
    *,
    user_id: str,
    tenant_id: str,
    actor_id: str | None = None,
) -> int:
    """
    Mark all active refresh tokens for the user+tenant pair as revoked.
    Returns the number of rows updated.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        sa.update(AuthRefreshToken)
        .where(AuthRefreshToken.user_id == user_id)
        .where(AuthRefreshToken.tenant_id == tenant_id)
        .where(AuthRefreshToken.revoked_at.is_(None))
        .values(revoked_at=now, revoked_by=actor_id)
    )
    result = await db.execute(stmt)
    await db.flush()
    return int(result.rowcount or 0)


async def issue_refresh_token(
    db: AsyncSession,
    *,
    user_id: str,
    tenant_id: str,
    expires_at: datetime,
    payload: dict | None = None,
) -> str:
    """Persist a hashed refresh token and return the raw value for the cookie."""
    raw, token_hash = generate_token("rf")
    row = AuthRefreshToken(
        user_id=user_id,
        tenant_id=tenant_id,
        token_hash=token_hash,
        expires_at=expires_at,
        payload=payload or {},
    )
    db.add(row)
    await db.flush()
    return raw


async def lookup_active_refresh_token(
    db: AsyncSession,
    *,
    raw_token: str,
) -> AuthRefreshToken | None:
    token_hash = hash_token(raw_token)
    stmt = (
        sa.select(AuthRefreshToken)
        .where(AuthRefreshToken.token_hash == token_hash)
        .where(AuthRefreshToken.revoked_at.is_(None))
        .limit(1)
    )
    row = await db.execute(stmt)
    entry = row.scalar_one_or_none()
    if entry is None:
        return None
    now = datetime.now(timezone.utc)
    expires = entry.expires_at
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= now:
            return None
    return entry


async def revoke_refresh_token_raw(
    db: AsyncSession,
    *,
    raw_token: str,
    actor_id: str | None = None,
) -> bool:
    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)
    stmt = (
        sa.update(AuthRefreshToken)
        .where(AuthRefreshToken.token_hash == token_hash)
        .where(AuthRefreshToken.revoked_at.is_(None))
        .values(revoked_at=now, revoked_by=actor_id)
    )
    result = await db.execute(stmt)
    await db.flush()
    return bool(result.rowcount)
