"""IntakeRouter — canonical routing decision (PR-3, read-only)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.intake_routing_enums import IntakeProvider, RouteIntent
from backend.app.models.tenant import Tenant
from backend.app.modules.intake_routing import crud
from backend.app.modules.intake_routing.reference import (
    normalize_external_key_secondary,
    normalize_provider,
    normalize_route_intent,
)
from backend.app.modules.leads.service._helpers import _load_tenant_business_type

_log = logging.getLogger(__name__)

TENANT_DEFAULT_SETTINGS_KEY = "intake_routing_v1"
TENANT_DEFAULT_PROFILE_KEY = "default_profile_id"


@dataclass(frozen=True)
class IntakeRoutingResult:
    """Normalized routing decision — no side effects on Lead/Candidate/Client."""

    matched: bool = False
    fallback: bool = False
    failed: bool = False
    intake_source_profile_id: Optional[str] = None
    own_company_id: Optional[str] = None
    route_intent: str = RouteIntent.unknown.value
    pipeline_preset: Optional[str] = None
    default_assignee_id: Optional[str] = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "fallback": self.fallback,
            "failed": self.failed,
            "intake_source_profile_id": self.intake_source_profile_id,
            "own_company_id": self.own_company_id,
            "route_intent": self.route_intent,
            "pipeline_preset": self.pipeline_preset,
            "default_assignee_id": self.default_assignee_id,
            "warnings": list(self.warnings),
        }


def _result_from_profile(
    profile: IntakeSourceProfile,
    *,
    matched: bool = True,
    fallback: bool = False,
    failed: bool = False,
    warnings: tuple[str, ...] = (),
) -> IntakeRoutingResult:
    return IntakeRoutingResult(
        matched=matched,
        fallback=fallback,
        failed=failed,
        intake_source_profile_id=str(profile.id),
        own_company_id=str(profile.own_company_id),
        route_intent=normalize_route_intent(profile.route_intent),
        pipeline_preset=str(profile.pipeline_preset or "").strip() or None,
        default_assignee_id=str(profile.default_assignee_id or "").strip() or None,
        warnings=warnings,
    )


def _failed(*, warnings: tuple[str, ...] = ()) -> IntakeRoutingResult:
    return IntakeRoutingResult(
        matched=False,
        fallback=False,
        failed=True,
        route_intent=RouteIntent.unknown.value,
        warnings=warnings,
    )


def _fallback_result(
    *,
    route_intent: str,
    own_company_id: Optional[str] = None,
    warnings: tuple[str, ...] = (),
) -> IntakeRoutingResult:
    return IntakeRoutingResult(
        matched=False,
        fallback=True,
        failed=False,
        own_company_id=own_company_id,
        route_intent=normalize_route_intent(route_intent),
        warnings=warnings,
    )


def _meta_missing_form_id(provider: str, external_key: str) -> bool:
    if normalize_provider(provider) != IntakeProvider.meta.value:
        return False
    ek = str(external_key or "").strip()
    return not ek or not ek.startswith("form_id:")


def _fallback_route_intent(business_type: Optional[str]) -> str:
    if str(business_type or "").strip().lower() == "services":
        return RouteIntent.sales_inquiry.value
    if str(business_type or "").strip().lower() in {"agency", "employer"}:
        return RouteIntent.candidate_application.value
    return RouteIntent.unknown.value


async def _load_tenant_default_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> Optional[IntakeSourceProfile]:
    row = (
        await db.execute(select(Tenant.settings).where(Tenant.id == tenant_id).limit(1))
    ).scalar_one_or_none()
    settings = row if isinstance(row, dict) else {}
    routing = settings.get(TENANT_DEFAULT_SETTINGS_KEY)
    if not isinstance(routing, dict):
        return None
    profile_id = str(routing.get(TENANT_DEFAULT_PROFILE_KEY) or "").strip()
    if not profile_id:
        return None
    profile = await crud.get_profile_by_id(db, tenant_id=tenant_id, profile_id=profile_id)
    if profile is None or not profile.is_active:
        return None
    if not str(profile.own_company_id or "").strip():
        return None
    return profile


async def _resolve_active_binding(
    db: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
    external_key: str,
    external_key_secondary: str,
) -> tuple[IntakeSourceBinding, IntakeSourceProfile] | None:
    binding = await crud.get_binding(
        db,
        tenant_id=tenant_id,
        provider=provider,
        external_key=external_key,
        external_key_secondary=external_key_secondary,
    )
    if binding is None or not binding.is_active:
        return None
    profile = await crud.get_profile_by_id(
        db,
        tenant_id=tenant_id,
        profile_id=str(binding.intake_source_profile_id),
    )
    if profile is None or not profile.is_active:
        return None
    if binding.tenant_id != profile.tenant_id:
        return None
    return binding, profile


class IntakeRouter:
    """Resolve intake source profile and route intent from foundation tables only."""

    @staticmethod
    async def resolve(
        db: AsyncSession,
        *,
        tenant_id: str,
        provider: str,
        external_key: str,
        external_key_secondary: str | None = None,
        own_company_hint: str | None = None,
    ) -> IntakeRoutingResult:
        tid = str(tenant_id or "").strip()
        prov = normalize_provider(provider)
        ek = str(external_key or "").strip()
        sec = normalize_external_key_secondary(external_key_secondary)
        oc_hint = str(own_company_hint or "").strip() or None

        if not tid:
            return _failed(warnings=("tenant_id_required",))

        # 1) Exact active binding (+ secondary-relaxed for page-less Meta match).
        if ek:
            for secondary in (sec, "") if sec else ("",):
                resolved = await _resolve_active_binding(
                    db,
                    tenant_id=tid,
                    provider=prov,
                    external_key=ek,
                    external_key_secondary=secondary,
                )
                if resolved is not None:
                    _binding, profile = resolved
                    warnings: tuple[str, ...] = ()
                    if secondary == "" and sec:
                        warnings = ("secondary_relaxed_binding",)
                    return _result_from_profile(profile, warnings=warnings)

        # 2) Tenant default source profile.
        default_profile = await _load_tenant_default_profile(db, tenant_id=tid)
        if default_profile is not None:
            return _result_from_profile(
                default_profile,
                warnings=("tenant_default_profile",),
            )

        # 3) Legacy fallback route (transitional; no profile binding).
        if _meta_missing_form_id(prov, ek):
            _log.warning(
                "intake_routing_failed",
                extra={
                    "event": "intake_routing_failed",
                    "tenant_id": tid,
                    "provider": prov,
                    "external_key": ek,
                    "reason": "meta_missing_form_id",
                },
            )
            return _failed(warnings=("meta_missing_form_id",))

        business_type = await _load_tenant_business_type(db, tid, oc_hint)
        route_intent = _fallback_route_intent(business_type)
        if route_intent == RouteIntent.unknown.value:
            _log.warning(
                "intake_routing_failed",
                extra={
                    "event": "intake_routing_failed",
                    "tenant_id": tid,
                    "provider": prov,
                    "external_key": ek,
                    "reason": "no_route",
                },
            )
            return _failed(warnings=("no_route",))

        _log.warning(
            "intake_routing_fallback",
            extra={
                "event": "intake_routing_fallback",
                "tenant_id": tid,
                "provider": prov,
                "external_key": ek,
                "fallback_route_intent": route_intent,
                "fallback_reason": "legacy_business_type",
                "business_type": business_type,
            },
        )
        return _fallback_result(
            route_intent=route_intent,
            own_company_id=oc_hint,
            warnings=("legacy_business_type_fallback",),
        )


async def resolve(
    db: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
    external_key: str,
    external_key_secondary: str | None = None,
    own_company_hint: str | None = None,
) -> IntakeRoutingResult:
    """Module-level alias for ``IntakeRouter.resolve``."""
    return await IntakeRouter.resolve(
        db,
        tenant_id=tenant_id,
        provider=provider,
        external_key=external_key,
        external_key_secondary=external_key_secondary,
        own_company_hint=own_company_hint,
    )


__all__ = ["IntakeRouter", "IntakeRoutingResult", "resolve"]
