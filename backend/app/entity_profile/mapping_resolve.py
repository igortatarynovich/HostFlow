"""Mapping Authority resolver (MA-2).

Exactly one store answers “which rule applies to this source?”:
``intake_source_profiles.mapping_rules``.

Leftover Meta form / tenant mapping is read-through into that store when
the authority is empty. Ingest must not implement a second fallback.

Not MA-3 (one editor). Not MA-4 (vocabulary cutover). Not a fourth store.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.lead import MetaLeadFormMapping, MetaLeadSettings
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.intake_routing.meta_bridge import (
    meta_external_key,
    meta_external_key_secondary,
    meta_profile_code,
)
from backend.app.modules.leads.normalizer import extract_meta_lead_form_context
from backend.app.reference.mapping_authority import RULES_SOURCE_AUTHORITY, WRITE_AUTHORITY

RESOLVER_API = "resolve_mapping_authority"


def coerce_mapping_rules(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, dict):
        rules = raw.get("rules")
        return [item for item in rules if isinstance(item, dict)] if isinstance(rules, list) else []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


@dataclass(frozen=True)
class MappingResolveResult:
    rules: list[dict[str, Any]]
    rules_source: str
    intake_source_profile_id: Optional[str]
    profile_updated_at: Optional[str]
    migrated: bool

    @property
    def write_authority(self) -> str:
        return WRITE_AUTHORITY


def _profile_updated_at(profile: Optional[IntakeSourceProfile]) -> Optional[str]:
    if profile is None:
        return None
    updated = getattr(profile, "updated_at", None)
    if updated is not None and hasattr(updated, "isoformat"):
        return updated.isoformat()
    return None


async def _load_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_source_profile_id: Optional[str],
    form_id: Optional[str],
    page_id: Optional[str],
) -> Optional[IntakeSourceProfile]:
    tid = str(tenant_id)
    if intake_source_profile_id:
        profile = await intake_crud.get_profile_by_id(
            db, tenant_id=tid, profile_id=str(intake_source_profile_id)
        )
        if profile is not None:
            return profile
    fid = str(form_id or "").strip()
    if not fid:
        return None
    by_code = await intake_crud.get_profile_by_code(
        db, tenant_id=tid, code=meta_profile_code(fid)
    )
    if by_code is not None:
        return by_code
    binding = await intake_crud.get_binding(
        db,
        tenant_id=tid,
        provider="meta",
        external_key=meta_external_key(fid),
        external_key_secondary=meta_external_key_secondary(page_id),
    )
    if binding is None and page_id:
        binding = await intake_crud.get_binding(
            db,
            tenant_id=tid,
            provider="meta",
            external_key=meta_external_key(fid),
            external_key_secondary="",
        )
    if binding is None:
        return None
    return await intake_crud.get_profile_by_id(
        db, tenant_id=tid, profile_id=str(binding.intake_source_profile_id)
    )


async def _leftover_rules(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: Optional[str],
    page_id: Optional[str],
    source: str,
    settings_row: Optional[Any],
) -> list[dict[str, Any]]:
    """Private read-through of leftover stores. Not an ingest fallback chain."""
    tid = str(tenant_id)
    src = (source or "meta").strip().lower() or "meta"
    fid = str(form_id or "").strip()
    pid = str(page_id or "").strip()
    if fid:
        row = (
            await db.execute(
                select(MetaLeadFormMapping).where(
                    MetaLeadFormMapping.tenant_id == tid,
                    MetaLeadFormMapping.source == src,
                    MetaLeadFormMapping.form_id == fid,
                    MetaLeadFormMapping.page_id == pid,
                )
            )
        ).scalar_one_or_none()
        if row is None and pid:
            row = (
                await db.execute(
                    select(MetaLeadFormMapping).where(
                        MetaLeadFormMapping.tenant_id == tid,
                        MetaLeadFormMapping.source == src,
                        MetaLeadFormMapping.form_id == fid,
                        MetaLeadFormMapping.page_id == "",
                    )
                )
            ).scalar_one_or_none()
        if row is not None:
            rules = coerce_mapping_rules(getattr(row, "mapping_rules", None))
            if rules:
                return rules
    settings = settings_row
    if settings is None:
        settings = (
            await db.execute(select(MetaLeadSettings).where(MetaLeadSettings.tenant_id == tid))
        ).scalar_one_or_none()
    return coerce_mapping_rules(getattr(settings, "field_mapping", None) if settings is not None else None)


def persist_authority_rules(profile: IntakeSourceProfile, rules: list[dict[str, Any]]) -> None:
    profile.mapping_rules = [dict(item) for item in rules]
    flag_modified(profile, "mapping_rules")


async def write_through_authority_for_meta_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    page_id: Optional[str],
    rules: list[dict[str, Any]],
) -> Optional[str]:
    """Copy leftover Meta-admin writes onto the surviving store when a profile exists."""
    profile = await _load_profile(
        db,
        tenant_id=str(tenant_id),
        intake_source_profile_id=None,
        form_id=form_id,
        page_id=page_id,
    )
    if profile is None:
        return None
    persist_authority_rules(profile, coerce_mapping_rules(rules))
    await db.flush()
    return str(profile.id)


async def resolve_mapping_authority(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_source_profile_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    source: str = "meta",
    settings_row: Optional[Any] = None,
    form_id: Optional[str] = None,
    page_id: Optional[str] = None,
) -> MappingResolveResult:
    src = (source or "meta").strip().lower() or "meta"
    ctx = extract_meta_lead_form_context(payload or {}, source=src) if payload else {}
    fid = str(form_id or ctx.get("form_id") or "").strip() or None
    pid = str(page_id or ctx.get("page_id") or "").strip() or None

    profile = await _load_profile(
        db,
        tenant_id=str(tenant_id),
        intake_source_profile_id=intake_source_profile_id,
        form_id=fid,
        page_id=pid,
    )
    if profile is None:
        return MappingResolveResult(
            rules=[],
            rules_source=RULES_SOURCE_AUTHORITY,
            intake_source_profile_id=None,
            profile_updated_at=None,
            migrated=False,
        )

    rules = coerce_mapping_rules(getattr(profile, "mapping_rules", None))
    migrated = False
    if not rules:
        leftover = await _leftover_rules(
            db,
            tenant_id=str(tenant_id),
            form_id=fid,
            page_id=pid,
            source=src,
            settings_row=settings_row,
        )
        if leftover:
            persist_authority_rules(profile, leftover)
            await db.flush()
            rules = coerce_mapping_rules(getattr(profile, "mapping_rules", None))
            migrated = True

    return MappingResolveResult(
        rules=list(rules),
        rules_source=RULES_SOURCE_AUTHORITY,
        intake_source_profile_id=str(profile.id),
        profile_updated_at=_profile_updated_at(profile),
        migrated=migrated,
    )


__all__ = [
    "MappingResolveResult",
    "RESOLVER_API",
    "coerce_mapping_rules",
    "persist_authority_rules",
    "resolve_mapping_authority",
    "write_through_authority_for_meta_form",
]
