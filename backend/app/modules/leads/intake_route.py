"""Intake Route resolution — Meta ingest via IntakeRouter (PR-4)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.intake_routing_enums import IntakeProvider, RouteIntent
from backend.app.modules.intake_routing.meta_bridge import (
    LEAD_TARGET_CANDIDATE,
    default_pipeline_for_route_intent,
    intake_routing_v1_block,
    is_sales_route_intent,
    meta_external_key,
    meta_external_key_secondary,
    normalize_lead_target_type,
    route_intent_creates_candidate,
    route_intent_to_lead_target_type,
)
from backend.app.modules.leads.normalizer import extract_meta_lead_form_context

if TYPE_CHECKING:
    from backend.app.services.intake_router import IntakeRoutingResult

_log = logging.getLogger(__name__)

LEAD_TARGET_CLIENT = "client_lead"
LEAD_TARGET_SERVICE_ORDER = "service_order_lead"
LEAD_TARGET_PARTNER = "partner_lead"

LEAD_TARGET_TYPES = frozenset(
    {
        LEAD_TARGET_CANDIDATE,
        LEAD_TARGET_CLIENT,
        LEAD_TARGET_SERVICE_ORDER,
        LEAD_TARGET_PARTNER,
    }
)

SALES_LEAD_TARGETS = frozenset({LEAD_TARGET_CLIENT, LEAD_TARGET_SERVICE_ORDER, LEAD_TARGET_PARTNER})


def ingest_creates_candidate(lead_target_type: str, *, force: bool = False) -> bool:
    """Backward-compatible wrapper — prefer ``route_intent_creates_candidate``."""
    from backend.app.modules.intake_routing.meta_bridge import lead_target_type_to_route_intent

    return route_intent_creates_candidate(
        lead_target_type_to_route_intent(lead_target_type),
        force=force,
    )


def is_sales_intake_target(lead_target_type: str) -> bool:
    from backend.app.modules.intake_routing.meta_bridge import lead_target_type_to_route_intent

    return is_sales_route_intent(lead_target_type_to_route_intent(lead_target_type))


def lead_type_for_target(lead_target_type: str) -> str:
    return "client" if is_sales_intake_target(lead_target_type) else "candidate"


def lead_type_for_route_intent(route_intent: str) -> str:
    return "client" if is_sales_route_intent(route_intent) else "candidate"


# Re-export foundation helpers for ingest pipeline.
from backend.app.modules.intake_routing.meta_bridge import (  # noqa: E402
    is_sales_route_intent,
    route_intent_creates_candidate,
)


@dataclass(frozen=True)
class IntakeRouteContext:
    matched: bool
    fallback: bool
    failed: bool
    route_intent: str
    lead_target_type: str
    own_company_id: Optional[str]
    pipeline_preset: Optional[str]
    default_assignee_id: Optional[str]
    intake_source_profile_id: Optional[str]
    form_id: Optional[str]
    page_id: Optional[str]
    source: str
    entity_profile_code: Optional[str] = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    fallback_reason: Optional[str] = None

    def to_intake_routing_v1(self) -> Dict[str, Any]:
        preset = default_pipeline_for_route_intent(self.route_intent, self.pipeline_preset)
        return intake_routing_v1_block(
            {
                "matched": self.matched,
                "fallback": self.fallback,
                "failed": self.failed,
                "intake_source_profile_id": self.intake_source_profile_id,
                "own_company_id": self.own_company_id,
                "route_intent": self.route_intent,
                "pipeline_preset": preset,
                "default_assignee_id": self.default_assignee_id,
                "warnings": list(self.warnings),
            },
            form_id=self.form_id,
            page_id=self.page_id,
            pipeline_preset=preset,
        )

    def to_normalized_block(self) -> Dict[str, Any]:
        """Legacy Phase-0 block kept for UI/API compat during transition."""
        return {
            "matched": self.matched,
            "lead_target_type": self.lead_target_type,
            "own_company_id": self.own_company_id,
            "pipeline_preset": self.pipeline_preset,
            "default_assignee_id": self.default_assignee_id,
            "form_id": self.form_id,
            "page_id": self.page_id,
            "source": self.source,
            "fallback_reason": self.fallback_reason,
            "route_intent": self.route_intent,
        }


def _context_from_routing_result(
    *,
    routing: "IntakeRoutingResult",
    source: str,
    form_id: Optional[str],
    page_id: Optional[str],
) -> IntakeRouteContext:
    route_intent = routing.route_intent
    lead_target_type = route_intent_to_lead_target_type(route_intent)
    pipeline = default_pipeline_for_route_intent(route_intent, routing.pipeline_preset)
    fallback_reason = None
    if routing.failed:
        fallback_reason = routing.warnings[0] if routing.warnings else "routing_failed"
    elif routing.fallback:
        fallback_reason = routing.warnings[0] if routing.warnings else "legacy_fallback"
    elif not routing.matched:
        fallback_reason = "tenant_default"

    return IntakeRouteContext(
        matched=bool(routing.matched),
        fallback=bool(routing.fallback),
        failed=bool(routing.failed),
        route_intent=route_intent,
        lead_target_type=lead_target_type,
        own_company_id=routing.own_company_id,
        pipeline_preset=pipeline,
        default_assignee_id=routing.default_assignee_id,
        intake_source_profile_id=routing.intake_source_profile_id,
        entity_profile_code=str(getattr(routing, "entity_profile_code", None) or "").strip() or None,
        form_id=form_id,
        page_id=page_id,
        source=source,
        warnings=tuple(routing.warnings),
        fallback_reason=fallback_reason,
    )


async def resolve_intake_route_for_ingest(
    db: AsyncSession,
    *,
    tenant_id: str,
    source: str,
    normalized: Dict[str, Any],
    payload: Optional[Dict[str, Any]] = None,
    own_company_id_hint: Optional[str] = None,
) -> IntakeRouteContext:
    """Resolve Meta ingest via ``IntakeRouter``; other sources get unknown route."""
    src = (source or "meta").strip().lower() or "meta"
    form_ctx = extract_meta_lead_form_context(payload or {}, source=src)
    form_id = str(normalized.get("form_id") or form_ctx.get("form_id") or "").strip() or None
    page_id = str(normalized.get("page_id") or form_ctx.get("page_id") or "").strip() or None

    if src != IntakeProvider.meta.value:
        return IntakeRouteContext(
            matched=False,
            fallback=False,
            failed=True,
            route_intent=RouteIntent.unknown.value,
            lead_target_type=LEAD_TARGET_CANDIDATE,
            own_company_id=str(own_company_id_hint or "").strip() or None,
            pipeline_preset=None,
            default_assignee_id=None,
            intake_source_profile_id=None,
            entity_profile_code=None,
            form_id=form_id,
            page_id=page_id,
            source=src,
            warnings=("unsupported_provider",),
            fallback_reason="unsupported_provider",
        )

    external_key = meta_external_key(form_id or "")
    external_key_secondary = meta_external_key_secondary(page_id)

    from backend.app.services.intake_router import IntakeRouter

    routing = await IntakeRouter.resolve(
        db,
        tenant_id=tenant_id,
        provider="meta",
        external_key=external_key,
        external_key_secondary=external_key_secondary,
        own_company_hint=own_company_id_hint,
    )
    return _context_from_routing_result(
        routing=routing,
        source=src,
        form_id=form_id,
        page_id=page_id,
    )
