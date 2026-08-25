"""Candidate card layout bridge — Field Registry + CandidateProfile (P3)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.field_registry.constants import DEFAULT_CANDIDATE_LAYOUT_CODE, RECRUITMENT_MODULE
from backend.app.field_registry.resolver import resolve_effective_card_layout
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.vacancy import Vacancy
from backend.app.process_engine.profile_resolver import resolve_effective_process_profile_for_candidate

DRIVER_CE_DEFAULT_CODE = "driver_ce_default"


def _legacy_field_key(field: dict[str, Any]) -> str:
    aliases = field.get("legacy_aliases") or []
    if aliases:
        return str(aliases[0])
    qualified = str(field.get("qualified_code") or "")
    return qualified.split(".")[-1].replace("[]", "")


def _profile_has_meaningful_field_configs(profile: CandidateProfile | None) -> bool:
    if profile is None:
        return False
    configs = (profile.config or {}).get("field_configs")
    if not isinstance(configs, list) or not configs:
        return False
    if profile.code == DRIVER_CE_DEFAULT_CODE:
        return False
    return True


def merge_candidate_profile_field_configs(
    layout: dict[str, Any],
    profile: CandidateProfile | None,
) -> dict[str, Any]:
    """Overlay CandidateProfile.config.field_configs onto registry layout rows."""
    if not _profile_has_meaningful_field_configs(profile):
        return layout

    assert profile is not None
    configs = profile.config.get("field_configs") or []
    by_key: dict[str, dict[str, Any]] = {}
    for row in configs:
        if not isinstance(row, dict):
            continue
        key = str(row.get("field_key") or "").strip()
        if key:
            by_key[key] = row

    merged = deepcopy(layout)
    merged_fields: list[dict[str, Any]] = []
    sections: dict[str, dict[str, Any]] = {}

    for field in merged.get("fields") or []:
        row = dict(field)
        match_key = None
        aliases = [*(row.get("legacy_aliases") or []), _legacy_field_key(row)]
        for alias in aliases:
            if alias in by_key:
                match_key = alias
                break
        if match_key:
            cfg = by_key[match_key]
            if "visible" in cfg:
                row["visible"] = cfg.get("visible") is not False
            if "required" in cfg:
                row["required"] = cfg.get("required") is True
            label = str(cfg.get("label") or "").strip()
            if label:
                row["label_override"] = label
        merged_fields.append(row)
        section_code = str(row.get("section_code") or "general")
        section = sections.setdefault(
            section_code,
            {"code": section_code, "order": row.get("sort_order") or 0, "fields": []},
        )
        section["fields"].append(row)

    merged["fields"] = merged_fields
    merged["sections"] = sorted(sections.values(), key=lambda s: s.get("order") or 0)
    merged["candidate_profile_id"] = profile.id
    merged["candidate_profile_code"] = profile.code
    merged["bridge_source"] = "candidate_profile"
    merged["layout_bridge_source"] = "candidate_profile_deprecated_overlay"
    base_source = str(layout.get("resolution_source") or "registry")
    merged["resolution_source"] = f"{base_source}+candidate_profile"
    return merged


async def _load_candidate_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_profile_id: str,
) -> CandidateProfile | None:
    return (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.id == candidate_profile_id,
                CandidateProfile.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()


async def resolve_candidate_profile_for_layout(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate | None = None,
    candidate_profile_id: Optional[str] = None,
) -> CandidateProfile | None:
    explicit_id = str(candidate_profile_id or "").strip()
    if explicit_id:
        return await _load_candidate_profile(db, tenant_id=tenant_id, candidate_profile_id=explicit_id)

    if candidate is None:
        return None

    vacancy_id = str(getattr(candidate, "vacancy_id", None) or "").strip()
    if not vacancy_id:
        return None

    vacancy = (
        await db.execute(
            select(Vacancy).where(
                Vacancy.id == vacancy_id,
                Vacancy.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if vacancy is None:
        return None

    profile_id = str(getattr(vacancy, "candidate_profile_id", None) or "").strip()
    if not profile_id:
        return None
    return await _load_candidate_profile(db, tenant_id=tenant_id, candidate_profile_id=profile_id)


def _layout_code_from_process_profile(process_profile: Any | None) -> str | None:
    if process_profile is None:
        return None
    config = dict(getattr(process_profile.profile, "config", None) or {})
    explicit = str(config.get("card_layout_code") or "").strip()
    if explicit:
        return explicit
    return None


async def resolve_effective_candidate_card_layout(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: Optional[str] = None,
    candidate_profile_id: Optional[str] = None,
    layout_code: Optional[str] = None,
    module: Optional[str] = RECRUITMENT_MODULE,
) -> dict[str, Any]:
    """Resolve candidate card layout with CandidateProfile bridge overlays."""
    tenant_scope = str(tenant_id).strip()
    candidate: Candidate | None = None
    cid = str(candidate_id or "").strip()
    if cid:
        candidate = (
            await db.execute(
                select(Candidate).where(
                    Candidate.id == cid,
                    Candidate.tenant_id == tenant_scope,
                    Candidate.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()

    profile = await resolve_candidate_profile_for_layout(
        db,
        tenant_id=tenant_scope,
        candidate=candidate,
        candidate_profile_id=candidate_profile_id,
    )

    resolved_layout_code = str(layout_code or "").strip() or None
    process_profile = None
    if candidate is not None:
        process_profile = await resolve_effective_process_profile_for_candidate(
            db,
            tenant_id=tenant_scope,
            candidate=candidate,
        )
        if not resolved_layout_code:
            resolved_layout_code = _layout_code_from_process_profile(process_profile)

    if not resolved_layout_code:
        resolved_layout_code = DEFAULT_CANDIDATE_LAYOUT_CODE

    layout = await resolve_effective_card_layout(
        db,
        tenant_id=tenant_scope,
        entity_type="candidate",
        layout_code=resolved_layout_code,
        module=module,
    )
    if layout.get("resolution_source") == "not_found":
        return layout

    if process_profile is not None:
        layout["process_profile_id"] = process_profile.profile_id
        layout["process_profile_code"] = process_profile.profile_code
        layout["process_profile_source"] = process_profile.source

    if profile is not None:
        layout = merge_candidate_profile_field_configs(layout, profile)
    elif candidate_profile_id or (candidate and profile is None):
        layout["bridge_source"] = "registry_only"

    if candidate_id:
        layout["candidate_id"] = cid
    return layout
