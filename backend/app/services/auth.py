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
