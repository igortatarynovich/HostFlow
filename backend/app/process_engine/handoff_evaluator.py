"""Process Engine handoff rule evaluation (P5).

Canonical handoff routing: PE Handoff Rule Registry + process profile handoff_mode
+ tenant_link as compatibility destination config (not sole routing source).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.process_engine import (
    PLATFORM_TENANT_SCOPE,
    REGISTRY_STATUS_ACTIVE,
    PeHandoffRule,
    PeProcessProfile,
)
from backend.app.models.tenant import TenantLink
from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.manifests.recruitment import HANDOFF_MODES
from backend.app.process_engine.profile_resolver import resolve_effective_process_profile_for_candidate_id
from backend.app.services.tenant_links import get_tenant_link, list_links_for_agency

RoutingSource = Literal["process_engine_handoff_rules", "tenant_link_legacy"]

DESTINATION_INTERNAL_HR = "internal_hr"
DESTINATION_CLIENT = "client"


@dataclass(frozen=True)
class HandoffEvaluation:
    destinations_allowed: list[str]
    tenant_link: TenantLink | None
    handoff_mode: str
    active_handoff_rules: list[str] = field(default_factory=list)
    routing_source: RoutingSource = "process_engine_handoff_rules"
    installed_modules: frozenset[str] = frozenset()
    warnings: list[dict[str, Any]] = field(default_factory=list)


def handoff_evaluation_to_dict(result: HandoffEvaluation) -> dict[str, Any]:
    return {
        "destinations_allowed": list(result.destinations_allowed),
        "handoff_mode": result.handoff_mode,
        "active_handoff_rules": list(result.active_handoff_rules),
        "routing_source": result.routing_source,
        "installed_modules": sorted(result.installed_modules),
        "warnings": list(result.warnings),
        "tenant_link": {
            "handoff_enabled": bool(result.tenant_link.get_handoff_enabled()) if result.tenant_link else False,
            "handoff_to_client": bool(result.tenant_link.get_handoff_to_client()) if result.tenant_link else False,
            "handoff_to_internal_hr": bool(result.tenant_link.get_handoff_to_internal_hr()) if result.tenant_link else False,
        },
    }


async def get_installed_modules(db: AsyncSession, tenant_id: str) -> set[str]:
    """Return product modules installed/enabled for tenant (registry-first, legacy fallback)."""
    from backend.app.module_registry.resolver import list_available_module_codes

    if db is None:
        return {RECRUITMENT_MODULE}
    return await list_available_module_codes(
        db,
        tenant_id=str(tenant_id).strip(),
        module_codes=(RECRUITMENT_MODULE, "hr", "client_portal"),
    )


def resolve_handoff_mode_from_profile(
    profile: PeProcessProfile | None,
    *,
    system_stage: str,
) -> str:
    """Effective handoff_mode from process profile config (stage override wins)."""
    default_mode = "both"
    if profile is None:
        return default_mode
    config = dict(profile.config or {})
    overrides = config.get("stage_overrides")
    if isinstance(overrides, dict):
        stage_cfg = overrides.get(system_stage)
        if isinstance(stage_cfg, dict):
            mode = str(stage_cfg.get("handoff_mode") or "").strip().lower()
            if mode in HANDOFF_MODES:
                return mode
    mode = str(config.get("handoff_mode") or "").strip().lower()
    if mode in HANDOFF_MODES:
        return mode
    return default_mode


def _rule_applies(
    rule: PeHandoffRule,
    *,
    system_stage: str,
    installed_modules: set[str],
) -> bool:
    if str(rule.status or "") != REGISTRY_STATUS_ACTIVE:
        return False
    config = dict(rule.config or {})
    enabled_when = config.get("enabled_when") or {}
    required = enabled_when.get("modules_installed") or [RECRUITMENT_MODULE]
    if not all(str(mod).strip() in installed_modules for mod in required):
        return False
    source = config.get("source") or {}
    rule_stage = str(source.get("system_stage") or "").strip().lower()
    if rule_stage and rule_stage != str(system_stage or "").strip().lower():
        return False
    return True


async def load_handoff_rules(
    db: AsyncSession,
    *,
    tenant_id: str,
    module: str = RECRUITMENT_MODULE,
) -> list[PeHandoffRule]:
    tenant_scope = str(tenant_id).strip()
    rows = (
        await db.execute(
            select(PeHandoffRule)
            .where(
                PeHandoffRule.module == module,
                PeHandoffRule.tenant_id.in_([tenant_scope, PLATFORM_TENANT_SCOPE]),
                PeHandoffRule.status == REGISTRY_STATUS_ACTIVE,
            )
            .order_by(PeHandoffRule.tenant_id.desc(), PeHandoffRule.code.asc())
        )
    ).scalars().all()
    seen_codes: set[str] = set()
    out: list[PeHandoffRule] = []
    for row in rows:
        code = str(row.code or "").strip()
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)
        out.append(row)
    return out


def _destination_types_for_mode(
    handoff_mode: str,
    *,
    installed_modules: set[str],
) -> set[str]:
    mode = str(handoff_mode or "").strip().lower()
    if mode == "none":
        return set()
    if mode == "client_portal":
        return {DESTINATION_CLIENT}
    if mode == "internal_hr":
        if "hr" not in installed_modules:
            return set()
        return {DESTINATION_INTERNAL_HR}
    if mode == "both":
        out = {DESTINATION_CLIENT}
        if "hr" in installed_modules:
            out.add(DESTINATION_INTERNAL_HR)
        return out
    return set()


def _legacy_destinations_from_link(link: TenantLink | None) -> list[str]:
    """Compatibility-only tenant_link routing when PE handoff rules are absent."""
    if link is None or not link.get_handoff_enabled():
        return []
    out: list[str] = []
    if link.get_handoff_to_internal_hr():
        out.append(DESTINATION_INTERNAL_HR)
    if link.get_handoff_to_client():
        out.append(DESTINATION_CLIENT)
    return out


async def _resolve_tenant_link_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> TenantLink | None:
    company_id = str(getattr(candidate, "company_id", "") or "").strip() or None
    own_company_id = str(getattr(candidate, "own_company_id", "") or "").strip() or None
    client_company_id = company_id or own_company_id

    link: TenantLink | None = None
    if client_company_id:
        link = await get_tenant_link(
            db,
            agency_tenant_id=tenant_id,
            client_company_id=client_company_id,
        )
    if link is None:
        links = await list_links_for_agency(db, tenant_id)
        for row in links:
            if row.get_handoff_enabled():
                link = row
                break
    return link


def _apply_tenant_link_destination_flags(
    pe_destination_types: set[str],
    link: TenantLink | None,
) -> list[str]:
    if link is None or not link.get_handoff_enabled():
        return []
    out: list[str] = []
    if DESTINATION_INTERNAL_HR in pe_destination_types and link.get_handoff_to_internal_hr():
        out.append(DESTINATION_INTERNAL_HR)
    if DESTINATION_CLIENT in pe_destination_types and link.get_handoff_to_client():
        out.append(DESTINATION_CLIENT)
    return out


async def evaluate_handoff_destinations(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    system_stage: str = "ready_for_handoff",
    module: str = RECRUITMENT_MODULE,
) -> HandoffEvaluation:
    """Evaluate active handoff destinations for a candidate (PE rules + tenant_link compat)."""
    tenant_link = await _resolve_tenant_link_for_candidate(
        db, tenant_id=str(tenant_id), candidate=candidate
    )

    rules = await load_handoff_rules(db, tenant_id=str(tenant_id), module=module)
    if not rules:
        # Compatibility: registry empty → legacy tenant_link-only routing.
        return HandoffEvaluation(
            destinations_allowed=_legacy_destinations_from_link(tenant_link),
            tenant_link=tenant_link,
            handoff_mode="tenant_link_legacy",
            active_handoff_rules=[],
            routing_source="tenant_link_legacy",
            installed_modules=frozenset(await get_installed_modules(db, str(tenant_id))),
        )

    installed = await get_installed_modules(db, str(tenant_id))
    profile = await resolve_effective_process_profile_for_candidate_id(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate.id),
        module=module,
    )
    handoff_mode = resolve_handoff_mode_from_profile(
        profile.profile if profile else None,
        system_stage=system_stage,
    )

    active_rules = [
        str(rule.code)
        for rule in rules
        if str(rule.handoff_mode or "").strip().lower() == handoff_mode
        and _rule_applies(rule, system_stage=system_stage, installed_modules=installed)
    ]

    pe_types = _destination_types_for_mode(handoff_mode, installed_modules=installed)
    warnings: list[dict[str, Any]] = []
    if handoff_mode in {"internal_hr", "both"} and DESTINATION_INTERNAL_HR not in pe_types:
        warnings.append(
            {
                "code": "handoff_target_module_not_installed",
                "message": "Internal HR handoff is inactive because HR module is not installed",
                "source_layer": "process_engine_handoff_rules",
                "severity": "warning",
            }
        )

    destinations = _apply_tenant_link_destination_flags(pe_types, tenant_link)

    return HandoffEvaluation(
        destinations_allowed=destinations,
        tenant_link=tenant_link,
        handoff_mode=handoff_mode,
        active_handoff_rules=active_rules,
        routing_source="process_engine_handoff_rules",
        installed_modules=frozenset(installed),
        warnings=warnings,
    )


async def evaluate_handoff_destinations_for_candidate_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    system_stage: str = "ready_for_handoff",
    module: str = RECRUITMENT_MODULE,
) -> HandoffEvaluation | None:
    candidate = (
        await db.execute(
            select(Candidate).where(
                Candidate.id == str(candidate_id).strip(),
                Candidate.tenant_id == str(tenant_id).strip(),
                Candidate.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if candidate is None:
        return None
    return await evaluate_handoff_destinations(
        db,
        tenant_id=str(tenant_id),
        candidate=candidate,
        system_stage=system_stage,
        module=module,
    )
