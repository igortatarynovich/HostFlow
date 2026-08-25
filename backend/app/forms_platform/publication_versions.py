"""Forms Sprint 3 — publication version ledger service (append-only)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.errors import (
    FormsNotFoundError,
    FormsPublicationVersionImmutableError,
    FormsVersionNotFoundError,
    FormsVersionPinnedError,
)
from backend.app.forms_platform.contract_identity import (
    backfill_snapshot_identity,
    identity_from_snapshot,
)
from backend.app.models.form_publication_version import FormPublicationVersion
from backend.app.models.tenant_lead_form import TenantLeadForm


def version_row_to_dict(row: FormPublicationVersion) -> dict[str, Any]:
    snap = dict(row.snapshot or {})
    out: dict[str, Any] = {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "form_id": str(row.form_id),
        "version": int(row.version),
        "snapshot": snap,
        "consent_pin": dict(row.consent_pin or {}),
        "submission_pin_count": int(row.submission_pin_count or 0),
        "idempotency_key": row.idempotency_key,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "immutable": True,
        "audit_read_only": True,
    }
    if snap.get("contract_identity") is not None or snap.get("field_schema") is not None:
        out["contract_identity"] = identity_from_snapshot(snap).to_dict()
    return out


async def get_publication_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    version: int,
) -> FormPublicationVersion:
    row = await db.scalar(
        select(FormPublicationVersion).where(
            FormPublicationVersion.tenant_id == str(tenant_id),
            FormPublicationVersion.form_id == str(form_id),
            FormPublicationVersion.version == int(version),
        )
    )
    if row is None:
        raise FormsVersionNotFoundError(
            details={"tenant_id": tenant_id, "form_id": form_id, "version": version}
        )
    return row


async def list_publication_versions(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> list[dict[str, Any]]:
    form = await db.get(TenantLeadForm, str(form_id))
    if form is None or str(form.tenant_id) != str(tenant_id):
        raise FormsNotFoundError(details={"form_id": form_id})
    rows = (
        await db.scalars(
            select(FormPublicationVersion)
            .where(
                FormPublicationVersion.tenant_id == str(tenant_id),
                FormPublicationVersion.form_id == str(form_id),
            )
            .order_by(FormPublicationVersion.version.asc())
        )
    ).all()
    return [version_row_to_dict(r) for r in rows]


async def find_version_by_idempotency_key(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    idempotency_key: str,
) -> FormPublicationVersion | None:
    key = str(idempotency_key or "").strip()
    if not key:
        return None
    return await db.scalar(
        select(FormPublicationVersion).where(
            FormPublicationVersion.tenant_id == str(tenant_id),
            FormPublicationVersion.form_id == str(form_id),
            FormPublicationVersion.idempotency_key == key,
        )
    )


async def append_publication_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    version: int,
    snapshot: dict[str, Any],
    consent_pin: dict[str, Any],
    idempotency_key: str | None,
    published_at,
) -> FormPublicationVersion:
    row = FormPublicationVersion(
        tenant_id=str(tenant_id),
        form_id=str(form_id),
        version=int(version),
        snapshot=dict(snapshot or {}),
        consent_pin=dict(consent_pin or {}),
        submission_pin_count=0,
        idempotency_key=(str(idempotency_key).strip() or None) if idempotency_key else None,
        published_at=published_at,
    )
    db.add(row)
    await db.flush()
    return row


async def replace_publication_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    version: int,
    snapshot: dict[str, Any],
) -> None:
    """Forbidden: freeze is append-only. Schema/identity cannot be rewritten."""
    await get_publication_version(
        db, tenant_id=tenant_id, form_id=form_id, version=version
    )
    raise FormsPublicationVersionImmutableError(
        details={"form_id": form_id, "version": version, "attempted_keys": sorted((snapshot or {}).keys())}
    )


async def backfill_publication_version_identity(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    version: int,
) -> dict[str, Any]:
    """Last-step C2 backfill: reconstruct identity or fail-close. Never invent legacy."""
    row = await get_publication_version(
        db, tenant_id=tenant_id, form_id=form_id, version=version
    )
    new_snap, wrote = backfill_snapshot_identity(dict(row.snapshot or {}))
    if wrote:
        row.snapshot = new_snap
        await db.flush()
    out = version_row_to_dict(row)
    out["backfilled"] = wrote
    return out


async def register_submission_pin(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    version: int,
) -> FormPublicationVersion:
    """Increment pin count when a submission anchors this publication version."""
    row = await get_publication_version(
        db, tenant_id=tenant_id, form_id=form_id, version=version
    )
    row.submission_pin_count = int(row.submission_pin_count or 0) + 1
    await db.flush()
    return row


async def assert_version_deletable(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    version: int,
) -> FormPublicationVersion:
    row = await get_publication_version(
        db, tenant_id=tenant_id, form_id=form_id, version=version
    )
    if int(row.submission_pin_count or 0) > 0:
        raise FormsVersionPinnedError(
            details={
                "form_id": form_id,
                "version": version,
                "submission_pin_count": row.submission_pin_count,
            }
        )
    return row


async def delete_publication_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    version: int,
) -> None:
    """Admin/audit purge only — forbidden when submission pins exist. Never edits snapshot."""
    row = await assert_version_deletable(
        db, tenant_id=tenant_id, form_id=form_id, version=version
    )
    # Never allow deleting the current pointer version while form still points at it.
    form = await db.get(TenantLeadForm, str(form_id))
    if form is not None and int(form.published_version or 0) == int(version):
        raise FormsVersionPinnedError(
            "Cannot delete the form's current published version pointer",
            details={"form_id": form_id, "version": version, "reason": "current_pointer"},
        )
    await db.delete(row)
    await db.flush()
