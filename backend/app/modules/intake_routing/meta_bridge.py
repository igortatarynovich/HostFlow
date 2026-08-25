"""Bridge Meta form routes ↔ Intake Routing foundation (PR-4)."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.models.lead import MetaFormRoute
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.intake_routing.reference import normalize_route_intent

LEAD_TARGET_CANDIDATE = "candidate"
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


def normalize_lead_target_type(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value in LEAD_TARGET_TYPES:
        return value
    return LEAD_TARGET_CANDIDATE


ROUTE_INTENT_TO_LEAD_TARGET: dict[str, str] = {
    RouteIntent.candidate_application.value: "candidate",
    RouteIntent.sales_inquiry.value: "client_lead",
    RouteIntent.service_request.value: "service_order_lead",
    RouteIntent.partner_inquiry.value: "partner_lead",
    RouteIntent.unknown.value: "candidate",
}

SALES_ROUTE_INTENTS = frozenset(
    {
        RouteIntent.sales_inquiry.value,
        RouteIntent.service_request.value,
        RouteIntent.partner_inquiry.value,
    }
)


def route_intent_to_lead_target_type(route_intent: str) -> str:
    normalized = normalize_route_intent(route_intent)
    return ROUTE_INTENT_TO_LEAD_TARGET.get(normalized, "candidate")


def lead_target_type_to_route_intent(lead_target_type: str) -> str:
    return normalize_route_intent(normalize_lead_target_type(lead_target_type))


def route_intent_creates_candidate(route_intent: str, *, force: bool = False) -> bool:
    if force:
        return True
    return normalize_route_intent(route_intent) == RouteIntent.candidate_application.value


def is_sales_route_intent(route_intent: str) -> bool:
    return normalize_route_intent(route_intent) in SALES_ROUTE_INTENTS


def is_sales_intake_target(lead_target_type: str) -> bool:
    return is_sales_route_intent(lead_target_type_to_route_intent(lead_target_type))


def lead_type_for_target(lead_target_type: str) -> str:
    return "client" if is_sales_intake_target(lead_target_type) else "candidate"


def lead_type_for_route_intent(route_intent: str) -> str:
    return "client" if is_sales_route_intent(route_intent) else "candidate"


def meta_profile_code(form_id: str) -> str:
    fid = str(form_id or "").strip()
    return f"meta-form-{fid}" if fid else "meta-form-unknown"


def meta_external_key(form_id: str) -> str:
    fid = str(form_id or "").strip()
    return f"form_id:{fid}" if fid else ""


def meta_external_key_secondary(page_id: Optional[str]) -> str:
    pid = str(page_id or "").strip()
    return f"page_id:{pid}" if pid else ""


def default_pipeline_for_route_intent(route_intent: str, pipeline_preset: Optional[str]) -> Optional[str]:
    preset = str(pipeline_preset or "").strip() or None
    if preset:
        return preset
    normalized = normalize_route_intent(route_intent)
    if normalized in SALES_ROUTE_INTENTS:
        return "service_sales"
    if normalized == RouteIntent.candidate_application.value:
        return "lead_pipeline"
    return None


async def _upsert_profile_from_meta_route(
    db: AsyncSession,
    *,
    route: MetaFormRoute,
) -> IntakeSourceProfile:
    code = meta_profile_code(route.form_id)
    existing = await intake_crud.get_profile_by_code(db, tenant_id=route.tenant_id, code=code)
    route_intent = lead_target_type_to_route_intent(route.lead_target_type)
    if existing is not None:
        existing.name = existing.name or f"Meta form {route.form_id}"
        existing.provider = "meta"
        existing.channel = "paid"
        existing.own_company_id = route.own_company_id
        existing.route_intent = route_intent
        existing.pipeline_preset = route.pipeline_preset
        existing.default_assignee_id = route.default_assignee_id
        existing.is_active = bool(route.is_active)
        await db.flush()
        return existing

    return await intake_crud.create_profile(
        db,
        tenant_id=route.tenant_id,
        code=code,
        name=f"Meta form {route.form_id}",
        own_company_id=route.own_company_id,
        provider="meta",
        channel="paid",
        route_intent=route_intent,
        pipeline_preset=route.pipeline_preset,
        default_assignee_id=route.default_assignee_id,
        is_active=bool(route.is_active),
    )


async def _upsert_binding_from_meta_route(
    db: AsyncSession,
    *,
    route: MetaFormRoute,
    profile: IntakeSourceProfile,
) -> IntakeSourceBinding:
    external_key = meta_external_key(route.form_id)
    external_key_secondary = meta_external_key_secondary(route.page_id or "")
    existing = await intake_crud.get_binding(
        db,
        tenant_id=route.tenant_id,
        provider="meta",
        external_key=external_key,
        external_key_secondary=external_key_secondary,
    )
    if existing is not None:
        existing.intake_source_profile_id = profile.id
        existing.is_active = bool(route.is_active)
        await db.flush()
        return existing

    return await intake_crud.create_binding(
        db,
        tenant_id=route.tenant_id,
        intake_source_profile_id=profile.id,
        provider="meta",
        external_key=external_key,
        external_key_secondary=external_key_secondary,
        label=f"Meta form {route.form_id}",
        is_active=bool(route.is_active),
    )


async def sync_meta_form_route_to_intake_foundation(
    db: AsyncSession,
    *,
    route: MetaFormRoute,
) -> tuple[IntakeSourceProfile, IntakeSourceBinding]:
    profile = await _upsert_profile_from_meta_route(db, route=route)
    binding = await _upsert_binding_from_meta_route(db, route=route, profile=profile)
    return profile, binding


async def migrate_all_meta_form_routes(
    db: AsyncSession,
) -> int:
    rows = list((await db.execute(select(MetaFormRoute))).scalars().all())
    for route in rows:
        await sync_meta_form_route_to_intake_foundation(db, route=route)
    return len(rows)


def intake_routing_v1_block(
    routing_dict: dict[str, Any],
    *,
    form_id: Optional[str],
    page_id: Optional[str],
    pipeline_preset: Optional[str],
) -> dict[str, Any]:
    block = dict(routing_dict)
    block["form_id"] = form_id
    block["page_id"] = page_id
    if pipeline_preset:
        block["pipeline_preset"] = pipeline_preset
    return block
