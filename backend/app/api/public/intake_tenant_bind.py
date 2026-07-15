"""Resolve tenant for public intake without relying on X-Tenant-Id (lead-form slug/id, intake/status/magic tokens).

PostgreSQL: SECURITY DEFINER SQL functions (migration) bypass RLS for token→tenant lookup.
SQLite / tests: ORM fallback (no RLS).
"""

from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID, bind_tenant_context_to_session, get_db
from backend.app.models.candidate import Candidate
from backend.app.models.magic_link import MagicLink
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.services.lead_forms_quota import normalize_and_validate_public_slug


def _dialect_name(db: AsyncSession) -> str:
    bind = db.get_bind()
    return str(getattr(bind.dialect, "name", "") or "")


async def _orm_intake_token_tenant_id(db: AsyncSession, token: str) -> Optional[str]:
    from backend.app.entity_profile.public_intake_draft_session import resolve_public_intake_lead_draft_tenant_id

    lead_tid = await resolve_public_intake_lead_draft_tenant_id(db, token)
    if lead_tid:
        return lead_tid
    tid = await db.scalar(
        select(Candidate.tenant_id).where(
            Candidate.intake_token == token,
            Candidate.deleted_at.is_(None),
        ).limit(1)
    )
    return str(tid) if tid else None


async def _pg_hf_intake_token_tenant_id(db: AsyncSession, token: str) -> Optional[str]:
    try:
        r = await db.execute(text("SELECT public.hf_intake_token_tenant(:t) AS tid").bindparams(t=token))
        row = r.first()
        if not row or row[0] is None:
            return None
        return str(row[0])
    except ProgrammingError:
        await db.rollback()
        return None


async def resolve_intake_token_tenant_id(db: AsyncSession, token: str) -> Optional[str]:
    if _dialect_name(db) == "postgresql":
        tid = await _pg_hf_intake_token_tenant_id(db, token)
        if tid:
            return tid
    return await _orm_intake_token_tenant_id(db, token)


async def _orm_status_share_token_tenant_id(db: AsyncSession, share_token: str) -> Optional[str]:
    tid = await db.scalar(
        select(Candidate.tenant_id).where(
            Candidate.status_share_token == share_token,
            Candidate.deleted_at.is_(None),
        ).limit(1)
    )
    return str(tid) if tid else None


async def _pg_hf_status_token_tenant_id(db: AsyncSession, share_token: str) -> Optional[str]:
    try:
        r = await db.execute(
            text("SELECT public.hf_status_share_token_tenant(:t) AS tid").bindparams(t=share_token)
        )
        row = r.first()
        if not row or row[0] is None:
            return None
        return str(row[0])
    except ProgrammingError:
        await db.rollback()
        return None


async def resolve_status_share_token_tenant_id(db: AsyncSession, share_token: str) -> Optional[str]:
    if _dialect_name(db) == "postgresql":
        tid = await _pg_hf_status_token_tenant_id(db, share_token)
        if tid:
            return tid
    tid = await _orm_status_share_token_tenant_id(db, share_token)
    if tid:
        return tid
    from backend.app.entity_profile.public_intake_draft_session import (
        resolve_public_intake_lead_draft_status_tenant_id,
    )

    return await resolve_public_intake_lead_draft_status_tenant_id(db, share_token)


async def _orm_magic_link_token_tenant_id(db: AsyncSession, token: str) -> Optional[str]:
    tid = await db.scalar(select(MagicLink.tenant_id).where(MagicLink.token == token).limit(1))
    return str(tid) if tid else None


async def _pg_hf_magic_link_token_tenant_id(db: AsyncSession, token: str) -> Optional[str]:
    try:
        r = await db.execute(text("SELECT public.hf_magic_link_token_tenant(:t) AS tid").bindparams(t=token))
        row = r.first()
        if not row or row[0] is None:
            return None
        return str(row[0])
    except ProgrammingError:
        await db.rollback()
        return None


async def resolve_magic_link_token_tenant_id(db: AsyncSession, token: str) -> Optional[str]:
    if _dialect_name(db) == "postgresql":
        tid = await _pg_hf_magic_link_token_tenant_id(db, token)
        if tid:
            return tid
    return await _orm_magic_link_token_tenant_id(db, token)


async def _orm_lead_form_by_slug(db: AsyncSession, slug_norm: str) -> Optional[TenantLeadForm]:
    rows = (
        await db.execute(
            select(TenantLeadForm).where(
                TenantLeadForm.public_slug == slug_norm,
                TenantLeadForm.is_active.is_(True),
            )
        )
    ).scalars().all()
    if not rows:
        return None
    if len(rows) > 1:
        # Ambiguous until global uniqueness is enforced; fail closed for public intake.
        return None
    return rows[0]


async def _pg_hf_lead_form_by_slug(db: AsyncSession, slug_norm: str) -> Optional[Tuple[str, str]]:
    try:
        r = await db.execute(
            text(
                "SELECT tenant_id::text, form_id::text FROM public.hf_lead_form_by_public_slug(:s)"
            ).bindparams(s=slug_norm)
        )
        row = r.first()
        if not row or not row[0] or not row[1]:
            return None
        return str(row[0]), str(row[1])
    except ProgrammingError:
        await db.rollback()
        return None


async def resolve_lead_form_tenant_and_id_by_slug(db: AsyncSession, slug_raw: str) -> Optional[Tuple[str, str]]:
    try:
        slug_norm = normalize_and_validate_public_slug(slug_raw)
    except ValueError:
        return None
    if not slug_norm:
        return None
    if _dialect_name(db) == "postgresql":
        pair = await _pg_hf_lead_form_by_slug(db, slug_norm)
        if pair:
            return pair
    row = await _orm_lead_form_by_slug(db, slug_norm)
    if row is None:
        return None
    return str(row.tenant_id), str(row.id)


async def _orm_lead_form_by_id(db: AsyncSession, form_id: str) -> Optional[TenantLeadForm]:
    return (
        await db.execute(
            select(TenantLeadForm).where(
                TenantLeadForm.id == form_id.strip(),
                TenantLeadForm.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()


async def _pg_hf_lead_form_by_id(db: AsyncSession, form_id: str) -> Optional[Tuple[str, str]]:
    try:
        r = await db.execute(
            text("SELECT tenant_id::text, form_id::text FROM public.hf_lead_form_by_id(:i)").bindparams(i=form_id.strip())
        )
        row = r.first()
        if not row or not row[0] or not row[1]:
            return None
        return str(row[0]), str(row[1])
    except ProgrammingError:
        await db.rollback()
        return None


async def resolve_lead_form_tenant_and_id_by_form_id(db: AsyncSession, form_id: str) -> Optional[Tuple[str, str]]:
    fid = (form_id or "").strip()
    if not fid:
        return None
    if _dialect_name(db) == "postgresql":
        pair = await _pg_hf_lead_form_by_id(db, fid)
        if pair:
            return pair
    row = await _orm_lead_form_by_id(db, fid)
    if row is None:
        return None
    return str(row.tenant_id), str(row.id)


async def resolve_tenant_uuid_for_public_intake_create(
    db: AsyncSession,
    *,
    x_tenant_id_header: Optional[str],
    lead_form_id: Optional[str],
    lead_form_slug: Optional[str],
) -> UUID:
    """Tenant for POST /public/intake: lead-form reference wins; else explicit X-Tenant-Id (not the legacy default)."""
    fid = (lead_form_id or "").strip()
    slug_raw = (lead_form_slug or "").strip()
    if fid and slug_raw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "lead_form_reference_ambiguous",
                "message": "Send only one of lead_form_id or lead_form_slug.",
            },
        )
    if slug_raw:
        try:
            normalize_and_validate_public_slug(slug_raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "lead_form_slug_invalid", "message": str(exc)},
            ) from exc
        pair = await resolve_lead_form_tenant_and_id_by_slug(db, slug_raw)
        if not pair:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "lead_form_not_found",
                    "message": "Lead form not found, inactive, or slug is not published.",
                },
            )
        return UUID(pair[0])
    if fid:
        pair = await resolve_lead_form_tenant_and_id_by_form_id(db, fid)
        if not pair:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "lead_form_not_found",
                    "message": "Lead form not found, inactive, or slug is not published.",
                },
            )
        return UUID(pair[0])

    raw = (x_tenant_id_header or "").strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "intake_tenant_required",
                "message": (
                    "Specify a published lead_form_slug (or lead_form_id) in the link, "
                    "or send X-Tenant-Id for the default tenant intake."
                ),
            },
        )
    try:
        tid = UUID(raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="X-Tenant-Id must be a valid UUID") from exc
    if tid == PUBLIC_LEGACY_DEFAULT_TENANT_UUID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "intake_default_tenant_forbidden",
                "message": (
                    "Use a tenant-specific link with lead_form_slug (or lead_form_id), "
                    "or send your workspace X-Tenant-Id — not the shared demo default."
                ),
            },
        )
    return tid


# --- FastAPI dependencies (path param names must match route) ---


async def public_intake_apply_session(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> Tuple[AsyncSession, UUID]:
    tid_str = await resolve_intake_token_tenant_id(db, token)
    if not tid_str:
        raise HTTPException(status_code=404, detail="Invalid intake token")
    tid = UUID(tid_str)
    await bind_tenant_context_to_session(db, tid)
    return db, tid


async def public_intake_status_session(
    share_token: str,
    db: AsyncSession = Depends(get_db),
) -> Tuple[AsyncSession, UUID]:
    tid_str = await resolve_status_share_token_tenant_id(db, share_token)
    if not tid_str:
        raise HTTPException(status_code=404, detail="Invalid status token")
    tid = UUID(tid_str)
    await bind_tenant_context_to_session(db, tid)
    return db, tid


async def public_intake_magic_link_redeem_session(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> Tuple[AsyncSession, UUID]:
    tid_str = await resolve_magic_link_token_tenant_id(db, token)
    if not tid_str:
        raise HTTPException(status_code=404, detail="Invalid magic link")
    tid = UUID(tid_str)
    await bind_tenant_context_to_session(db, tid)
    return db, tid


async def public_intake_storage_upload_session(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> Tuple[AsyncSession, UUID]:
    """PUT /uploads/{token}/… — token may be intake_token (apply) or status_share_token (status flow)."""
    tid_str = await resolve_intake_token_tenant_id(db, token)
    if tid_str:
        tid = UUID(tid_str)
        await bind_tenant_context_to_session(db, tid)
        return db, tid
    tid_status = await resolve_status_share_token_tenant_id(db, token)
    if tid_status:
        tid = UUID(tid_status)
        await bind_tenant_context_to_session(db, tid)
        return db, tid
    raise HTTPException(status_code=404, detail="Invalid token")
