from __future__ import annotations

import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services import billing_restrictions

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.schemas.additional_services import ServiceOrderOut
from backend.app.modules.leads import (
    admin_service,
    lead_custom_fields,
    next_action_api as _next_action_api,
    next_action_enforcement,
    pipeline_hooks,
    service,
)
from backend.app.modules.leads.lead_stage_contract import batch_lead_stage_contracts
from backend.app.modules.leads.schemas import (
    BulkAutoProcessQueueItemOut,
    BulkAutoProcessQueueRequest,
    BulkAutoProcessQueueResponse,
    BulkLeadUpdateRequest,
    BulkLeadUpdateResponse,
    LeadDistributionOut,
    LeadDistributionPatch,
    LeadDistributionAlert,
    LeadDistributionFeatureGate,
    LeadDistributionNextPreview,
    LeadDistributionStats,
    LeadDistributionTeamMemberOut,
    LeadConversionFunnelResponse,
    LeadDuplicateDecisionRequest,
    LeadIntakeDecisionIn,
    LeadListResponse,
    LeadOut,
    LeadStageHealthResponse,
    LeadStageUpdate,
    LeadTimelineResponse,
    LeadVacancyConfirmIn,
    MetaLeadResponse,
    lead_vacancy_routing_aux,
)
from backend.app.services.lead_distribution import build_distribution_snapshot, patch_distribution_settings
from backend.app.services.plan_feature_gates import plan_allows_team_tier_features, resolve_tenant_plan_code
from backend.app.services.additional_services import AdditionalServicesService
from backend.app.services.lead_lifecycle import (
    apply_lead_deletion_cleanup,
    maybe_apply_lead_silence_cleanup,
)
from backend.app.models import Lead, User
from backend.app.services.audit import log_activity
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id


router = APIRouter(prefix="/leads", tags=["leads"])

# G-8 stage 2.0: per-lead "what to do next" CTA. Mounted as a sub-router so
# the implementation lives next to the lead module instead of bloating this
# already-large file. See backend/app/modules/leads/next_action_api.py.
router.include_router(_next_action_api.router)


def _signature_matches(secret: str, body: bytes, signature: str | None) -> bool:
    if not secret:
        return True
    if not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.get("/", response_model=LeadListResponse)
@router.get("", response_model=LeadListResponse, include_in_schema=False)
async def list_leads_endpoint(
    status_filter: str | None = Query(None, alias="status"),
    stage_filter: str | None = Query(None, alias="stage"),
    next_action_filter: str | None = Query(None, alias="next_action"),
    search_q: str | None = Query(None, alias="q", max_length=200),
    custom_field_key: str | None = Query(None, alias="custom_field_key"),
    custom_field_value: str | None = Query(None, alias="custom_field_value"),
    conversion_root: str | None = Query(
        None,
        alias="conversion_root",
        max_length=32,
        description="§2.12 root bucket: lead | qualified | active | final (effective mapping from funnel + legacy).",
    ),
    lost_reason_code_param: str | None = Query(
        None,
        alias="lost_reason_code",
        max_length=64,
        description="§2.12 When set: processed + lost + normalized.lead_lost_reason_v1.code match; conversion_root ignored.",
    ),
    lost_from_crm_stage_param: str | None = Query(
        None,
        alias="lost_from_crm_stage",
        max_length=32,
        description=(
            "§2.12 When set: processed + lost + ActivityLog lead.stage_changed into lost "
            "with matching payload.from_stage (or 'unknown' for empty prior stage)."
        ),
    ),
    pipeline_error_param: str | None = Query(
        None,
        alias="pipeline_error",
        max_length=64,
        description="Exact Lead.error filter (whitelist: LEAD_FIT_NO_MATCH, LEAD_FIT_NEEDS_INFO). Ignored when lost_reason_code or lost_from_crm_stage is set.",
    ),
    created_before_hours: int | None = Query(
        None,
        ge=1,
        le=8760,
        description="When set, only leads with created_at older than now minus this many hours (e.g. 24 with status=new for stale new leads).",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> LeadListResponse:
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    cf_def_id: str | None = None
    cf_match: str | None = None
    key_trim = (custom_field_key or "").strip()
    if key_trim:
        if custom_field_value is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="custom_field_value is required when custom_field_key is set",
            )
        resolved = await lead_custom_fields.resolve_lead_definition_id_by_key(db, tenant_id=tid, key=key_trim)
        if not resolved:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unknown custom_field_key for lead scope",
            )
        cf_def_id = resolved
        cf_match = custom_field_value
    elif custom_field_value is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="custom_field_key is required when custom_field_value is set",
        )

    lrc = (lost_reason_code_param or "").strip() or None
    if lrc:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", lrc):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="lost_reason_code must match [A-Za-z0-9_-]{1,64}",
            )

    lf_crm = (lost_from_crm_stage_param or "").strip().lower() or None
    if lf_crm and lf_crm != "unknown" and not re.fullmatch(r"[a-z0-9_-]{1,32}", lf_crm):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lost_from_crm_stage must be 'unknown' or match [a-z0-9_-]{1,32}",
        )

    cr_param = (conversion_root or "").strip().lower() or None
    if cr_param and cr_param not in ("lead", "qualified", "active", "final"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="conversion_root must be one of: lead, qualified, active, final",
        )
    if lrc or lf_crm:
        cr_param = None

    pe_raw = (pipeline_error_param or "").strip() or None
    if pe_raw and pe_raw not in service.LEAD_LIST_PIPELINE_ERROR_WHITELIST:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="pipeline_error must be one of: LEAD_FIT_NO_MATCH, LEAD_FIT_NEEDS_INFO",
        )
    pipeline_error = None if (lrc or lf_crm) else pe_raw

    return await service.list_leads(
        db,
        tenant_id=tid,
        own_company_id=own_company_id,
        status=status_filter,
        stage=stage_filter,
        next_action=next_action_filter,
        search=(search_q or "").strip() or None,
        custom_field_definition_id=cf_def_id,
        custom_field_match_value=cf_match,
        conversion_root=cr_param,
        lost_reason_code=lrc,
        lost_from_crm_stage=lf_crm,
        pipeline_error=pipeline_error,
        created_before_hours=created_before_hours,
        limit=limit,
        offset=offset,
    )


def _distribution_response(snap: dict) -> LeadDistributionOut:
    cfg = snap["config"]
    np = snap.get("next_preview")
    fg = snap["feature_gate"]
    mode = str(cfg.get("mode") or "manual").strip().lower()
    if mode not in ("automatic", "manual"):
        mode = "manual"
    strategy = str(cfg.get("strategy") or "smart").strip().lower()
    if strategy not in ("smart", "round_robin", "manual_rules"):
        strategy = "smart"
    lr_raw = cfg.get("language_routing_v1")
    language_routing: dict[str, list[str]] = {}
    if isinstance(lr_raw, dict):
        for lk, ids in lr_raw.items():
            if isinstance(ids, list):
                language_routing[str(lk)] = [str(u) for u in ids if str(u).strip()]

    return LeadDistributionOut(
        mode=mode,  # type: ignore[arg-type]
        strategy=strategy,  # type: ignore[arg-type]
        criteria_order=list(cfg.get("criteria_order") or []),
        max_leads_per_person=int(cfg.get("max_leads_per_person") or 10),
        only_active_employees=bool(cfg.get("only_active_employees", True)),
        preview_language=str(cfg.get("preview_language") or "pl"),
        language_routing_v1=language_routing,
        assignment_detail_lines=list(snap.get("assignment_detail_lines") or []),
        rules_summary_lines=list(snap.get("rules_summary_lines") or []),
        next_preview=LeadDistributionNextPreview(**np) if isinstance(np, dict) else None,
        team=[LeadDistributionTeamMemberOut(**x) for x in (snap.get("team") or [])],
        flow_steps=list(snap.get("flow_steps") or []),
        alerts=[LeadDistributionAlert(**x) for x in (snap.get("alerts") or [])],
        stats=LeadDistributionStats(**(snap.get("stats") or {})),
        feature_gate=LeadDistributionFeatureGate(**fg),
    )


@router.get("/distribution", response_model=LeadDistributionOut)
async def get_lead_distribution(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.supervisor, Role.recruiter)),
):
    db, tenant_uuid = db_tenant
    snap = await build_distribution_snapshot(db, tenant_id=str(tenant_uuid))
    return _distribution_response(snap)


@router.patch("/distribution", response_model=LeadDistributionOut)
async def patch_lead_distribution(
    payload: LeadDistributionPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.supervisor)),
):
    db, tenant_uuid = db_tenant
    tid = str(tenant_uuid)
    updates = payload.model_dump(exclude_unset=True)
    await patch_distribution_settings(db, tenant_id=tid, patch=updates)
    await db.commit()
    try:
        await log_activity(
            db,
            tenant_id=tid,
            actor_id=str(current_user.sub or "").strip() or None,
            action="lead_distribution.updated",
            target_type="tenant",
            target_id=tid,
            payload={"fields": sorted(updates.keys())},
        )
        await db.commit()
    except Exception:
        pass
    snap = await build_distribution_snapshot(db, tenant_id=tid)
    return _distribution_response(snap)


@router.get("/stage-health", response_model=LeadStageHealthResponse)
async def lead_stage_health_endpoint(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> LeadStageHealthResponse:
    db, tenant_uuid = db_tenant
    return await service.lead_stage_health_snapshot(
        db,
        tenant_id=str(tenant_uuid),
        own_company_id=own_company_id,
    )


@router.get("/conversion-funnel", response_model=LeadConversionFunnelResponse)
async def lead_conversion_funnel_endpoint(
    funnel_source: str | None = Query(None, alias="source", max_length=64),
    funnel_vacancy_id: str | None = Query(None, alias="vacancy_id", max_length=36),
    funnel_funnel_id: str | None = Query(None, alias="funnel_id", max_length=36),
    funnel_assignee_user_id: str | None = Query(None, alias="assignee_user_id", max_length=36),
    cohort_window_days: int | None = Query(
        None,
        ge=1,
        le=90,
        description="§2.12 stretch: only leads with created_at in [now−D, now); Team+.",
    ),
    cohort_compare_prior: bool = Query(
        False,
        description="With cohort window: also compute prior period of equal length (WoW).",
    ),
    cohort_created_after: datetime | None = Query(
        None,
        description="Inclusive lower bound for Lead.created_at (alternative to cohort_window_days).",
    ),
    cohort_created_before_exclusive: datetime | None = Query(
        None,
        alias="cohort_created_before",
        description="Exclusive upper bound for Lead.created_at.",
    ),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> LeadConversionFunnelResponse:
    db, tenant_uuid = db_tenant
    tid = str(tenant_uuid)
    if cohort_window_days is not None and (
        cohort_created_after is not None or cohort_created_before_exclusive is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use either cohort_window_days or cohort_created_after/cohort_created_before, not both",
        )
    cmin: datetime | None = None
    cmax_excl: datetime | None = None
    if cohort_window_days is not None:
        cmax_excl = datetime.now(timezone.utc)
        cmin = cmax_excl - timedelta(days=int(cohort_window_days))
    elif cohort_created_after is not None or cohort_created_before_exclusive is not None:
        if cohort_created_after is None or cohort_created_before_exclusive is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="cohort_created_after and cohort_created_before must be set together",
            )
        cmin = cohort_created_after
        if cmin.tzinfo is None or cohort_created_before_exclusive.tzinfo is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="cohort bounds must be timezone-aware (UTC recommended)",
            )
        cmax_excl = cohort_created_before_exclusive
        if cmax_excl <= cmin:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="cohort_created_before must be after cohort_created_after",
            )
    sp = service.ConversionFunnelSliceParams.normalize(
        source=funnel_source,
        vacancy_id=funnel_vacancy_id,
        funnel_id=funnel_funnel_id,
        assignee_user_id=funnel_assignee_user_id,
        cohort_created_at_min=cmin,
        cohort_created_at_max_exclusive=cmax_excl,
    )
    if sp.any_set():
        plan = await resolve_tenant_plan_code(db, tid)
        if not plan_allows_team_tier_features(plan, tenant_id=str(tid)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "plan_requires_team",
                    "feature": "leads_conversion_funnel_slices",
                    "plan": plan,
                },
            )
    if sp.assignee_user_id:
        row = await db.execute(
            select(User.id).where(
                User.id == sp.assignee_user_id,
                User.tenant_id == tid,
                User.is_active.is_(True),
            ).limit(1)
        )
        if row.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="assignee_user_id is not an active user in this tenant",
            )
    return await service.lead_conversion_funnel_snapshot(
        db,
        tenant_id=tid,
        own_company_id=own_company_id,
        slice_params=sp,
        cohort_compare_prior=bool(cohort_compare_prior),
    )


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead_detail_endpoint(
    lead_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> LeadOut:
    """Full lead row (same shape as GET /leads items) for workspace / deep links."""
    db, tenant_uuid = db_tenant
    res = await service.list_leads(
        db,
        tenant_id=str(tenant_uuid),
        own_company_id=own_company_id,
        only_lead_id=lead_id,
        limit=1,
        offset=0,
    )
    if not res.items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return res.items[0]


@router.post(
    "/{lead_id}/compliance/rodo/send",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(Role.admin, Role.manager, Role.recruiter))],
)
async def send_lead_rodo_compliance_endpoint(
    lead_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> Dict[str, Any]:
    """Send art.14 RODO notice to the lead contact email; audit lives on ``lead.normalized['rodo']``."""
    from backend.app.modules.leads import crud
    from backend.app.services.lead_rodo import send_lead_rodo_email

    db, tenant_uuid = db_tenant
    tenant_id_str = str(tenant_uuid)
    lead = await crud.get_lead(db, tenant_id=tenant_id_str, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    ok, msg = await send_lead_rodo_email(
        db,
        lead=lead,
        tenant_id=tenant_id_str,
        actor_id=str(current_user.sub or "").strip() or None,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    await db.commit()
    return {"ok": True, "message": msg}


@router.post(
    "/{lead_id}/compliance/rodo/source-provided",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(Role.admin, Role.manager, Role.recruiter))],
)
async def mark_lead_rodo_source_provided_endpoint(
    lead_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    note: str | None = Query(None, max_length=2000, description="Optional operator note (why source counts as art.14)."),
) -> Dict[str, Any]:
    """Mark art.14 as satisfied via source (no outbound email). Persists ``lead.normalized['rodo']``."""
    from backend.app.modules.leads import crud
    from backend.app.services.lead_rodo import mark_lead_rodo_source_provided

    db, tenant_uuid = db_tenant
    tenant_id_str = str(tenant_uuid)
    lead = await crud.get_lead(db, tenant_id=tenant_id_str, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    mark_lead_rodo_source_provided(
        lead,
        actor_id=str(current_user.sub or "").strip() or None,
        note=note,
    )
    await db.commit()
    return {"ok": True}


@router.patch("/{lead_id}", response_model=LeadOut)
async def update_lead_stage_endpoint(
    lead_id: str,
    payload: LeadStageUpdate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
) -> LeadOut:
    """Update lead CRM stage (new, contacted, qualified, converted, lost)."""
    from backend.app.modules.leads import crud
    from uuid import UUID as PyUUID

    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    lead = await crud.get_lead(db, tenant_id=tenant_id_str, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    from backend.app.services.lead_rodo import LEAD_RODO_ACTION_CONTACTED_STAGE, lead_rodo_required_block_code

    if "stage" in payload.model_fields_set and payload.stage is not None:
        stage_will_change = str(payload.stage or "") != str(getattr(lead, "stage", None) or "")
        if stage_will_change and str(payload.stage or "").strip().lower() == "contacted":
            if lead_rodo_required_block_code(lead, LEAD_RODO_ACTION_CONTACTED_STAGE):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"code": "LEAD_RODO_REQUIRED"},
                )

    prev_stage = getattr(lead, "stage", None)
    prev_status = getattr(lead, "status", None)
    prev_candidate_id = getattr(lead, "candidate_id", None)
    tenant_row = await db.get(Tenant, tenant_id_str)
    lic_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id_str).limit(1))
    ).scalar_one_or_none()
    will_change_stage = (
        "stage" in payload.model_fields_set
        and payload.stage is not None
        and str(payload.stage or "") != str(prev_stage or "")
    )
    touches_assignment_lock = "assignment_locked" in payload.model_fields_set and payload.assignment_locked is not None
    if billing_restrictions.tenant_billing_blocks_side_effect_writes(tenant_row, lic_row) and (
        will_change_stage or touches_assignment_lock
    ):
        billing_restrictions.ensure_billing_allows_side_effects(tenant_row, lic_row)

    enforcement_mode = await next_action_enforcement.get_next_action_enforcement_mode(db, tenant_id=tenant_id_str)
    actor_for_enforcement = str(current_user.sub or "").strip() or None

    if "assignment_locked" in payload.model_fields_set:
        norm = dict(lead.normalized or {})
        lock = norm.get("assignment_lock_v1")
        if not isinstance(lock, dict):
            lock = {}
        lock["locked"] = bool(payload.assignment_locked)
        lock["updated_at"] = datetime.now(timezone.utc).isoformat()
        if actor_for_enforcement:
            lock["updated_by"] = actor_for_enforcement
        norm["assignment_lock_v1"] = lock
        lead.normalized = norm
        await db.flush()

    stage_changed = False
    if "stage" in payload.model_fields_set:
        stage_will_change = str(payload.stage or "") != str(prev_stage or "")
        if enforcement_mode in {"warn", "block"} and stage_will_change:
            has_active = await next_action_enforcement.lead_has_active_next_action_reminder(
                db, tenant_id=tenant_id_str, lead_id=str(lead.id)
            )
            if not has_active:
                await next_action_enforcement.maybe_log_missing_next_action(
                    db,
                    tenant_id=tenant_id_str,
                    actor_id=actor_for_enforcement,
                    lead_id=str(lead.id),
                    attempted_stage=payload.stage,
                    mode=enforcement_mode,
                )
                if enforcement_mode == "block":
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Next action required: create an activity before changing stage.",
                    )
        await crud.update_lead_stage(db, lead, stage=payload.stage)
        stage_changed = str(getattr(lead, "stage", None) or "") != str(prev_stage or "")

    lost_reason_code: str | None = None
    lost_reason_note: str | None = None
    if stage_changed and str(payload.stage or "") == "lost":
        lost_reason_code = payload.lost_reason_code
        lost_reason_note = payload.lost_reason_note

    if stage_changed:
        norm = dict(lead.normalized or {})
        ns = str(payload.stage or "")
        ps = str(prev_stage or "")
        if ns == "lost":
            lr_block: Dict[str, Any] = {"at": datetime.now(timezone.utc).isoformat()}
            if actor_for_enforcement:
                lr_block["set_by"] = actor_for_enforcement
            if lost_reason_code:
                lr_block["code"] = lost_reason_code
            if lost_reason_note:
                lr_block["note"] = lost_reason_note
            norm["lead_lost_reason_v1"] = lr_block
            lead.normalized = norm
        elif ps == "lost":
            norm.pop("lead_lost_reason_v1", None)
            lead.normalized = norm
        await db.flush()
        await pipeline_hooks.record_lead_stage_change(
            db,
            tenant_id=tenant_id_str,
            lead=lead,
            from_stage=prev_stage,
            to_stage=payload.stage,
            actor_id=str(current_user.sub or "").strip() or None,
            lost_reason_code=lost_reason_code,
            lost_reason_note=lost_reason_note,
        )
    await db.commit()
    await db.refresh(lead)
    if stage_changed:
        try:
            await maybe_apply_lead_silence_cleanup(
                db,
                tenant_id=tenant_id_str,
                lead_id=str(lead.id),
                old_stage=prev_stage,
                new_stage=getattr(lead, "stage", None),
                old_status=prev_status,
                new_status=getattr(lead, "status", None),
                old_candidate_id=prev_candidate_id,
                new_candidate_id=getattr(lead, "candidate_id", None),
                actor_id=str(current_user.sub or "").strip() or None,
            )
            await db.commit()
        except Exception:
            await db.rollback()
    if stage_changed:
        await pipeline_hooks.run_lead_stage_change_automations(
            db,
            tenant_id=tenant_id_str,
            lead=lead,
            from_stage=prev_stage,
            to_stage=payload.stage,
            actor_id=str(current_user.sub or "").strip() or None,
        )
    business_type = await service._load_tenant_business_type(db, tenant_id_str)
    outcome_entity_type, outcome_entity_id, outcome_entity_name = service._build_lead_outcome(
        business_type=business_type,
        company_id=lead.company_id,
        company_name=None,
        candidate_id=lead.candidate_id,
        candidate_name=None,
    )

    if business_type == "services":
        await service._emit_lead_event(
            db,
            tenant_id=tenant_id_str,
            lead=lead,
            event_type="lead.status_changed.telegram",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type=outcome_entity_type,
            outcome_entity_id=outcome_entity_id,
            outcome_entity_name=outcome_entity_name,
            user_ids=[current_user.sub] if current_user and current_user.sub else None,
        )
        await db.commit()

    sc_map = await batch_lead_stage_contracts(db, tenant_id=tenant_id_str, leads=[lead])
    stage_contract_out = sc_map.get(str(lead.id))
    cf_maps = await lead_custom_fields.batch_lead_custom_field_maps(
        db, tenant_id=tenant_id_str, lead_ids=[str(lead.id)]
    )

    _, vacancy_routing_confirmed = lead_vacancy_routing_aux(
        lead.normalized if isinstance(lead.normalized, dict) else {},
        lead.vacancy_id,
    )
    return LeadOut(
        id=PyUUID(lead.id),
        tenant_id=PyUUID(lead.tenant_id),
        business_type=business_type,
        lead_type=(getattr(lead, "lead_type", None) or "candidate"),  # type: ignore[arg-type]
        company_id=PyUUID(lead.company_id) if lead.company_id else None,
        company_name=None,
        vacancy_id=PyUUID(lead.vacancy_id) if lead.vacancy_id else None,
        vacancy_title=None,
        source=lead.source,
        ad_id=lead.ad_id,
        external_id=getattr(lead, "external_id", None),
        status=lead.status,  # type: ignore[arg-type]
        stage=lead.stage,
        funnel_id=PyUUID(lead.funnel_id) if lead.funnel_id else None,
        stage_contract=stage_contract_out,
        candidate_id=PyUUID(lead.candidate_id) if lead.candidate_id else None,
        candidate_name=None,
        outcome_entity_type=outcome_entity_type,
        outcome_entity_id=PyUUID(outcome_entity_id) if outcome_entity_id else None,
        outcome_entity_name=outcome_entity_name,
        service_order_id=PyUUID(str((lead.normalized or {}).get("service_order_id"))) if isinstance(lead.normalized, dict) and (lead.normalized or {}).get("service_order_id") else None,
        recruiter_id=None,
        error=lead.error,
        payload=lead.payload or {},
        normalized=lead.normalized,
        custom_fields=cf_maps.get(str(lead.id), {}),
        created_at=lead.created_at,
        last_routed_at=lead.last_routed_at,
        vacancy_routing_confirmed=vacancy_routing_confirmed,
    )


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead_endpoint(
    lead_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
) -> None:
    """Permanently remove a lead (e.g. test / mistaken ingest). Does not delete linked candidates."""
    from backend.app.modules.leads import crud

    db, tenant_uuid = db_tenant
    tenant_id_str = str(tenant_uuid)
    res = await service.list_leads(
        db,
        tenant_id=tenant_id_str,
        own_company_id=own_company_id,
        only_lead_id=lead_id,
        limit=1,
        offset=0,
    )
    if not res.items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    actor_id = str(current_user.sub or "").strip() or None
    try:
        await apply_lead_deletion_cleanup(
            db,
            tenant_id=tenant_id_str,
            lead_id=lead_id,
            actor_id=actor_id,
        )
    except Exception:
        await db.rollback()
    deleted = await crud.delete_lead(db, tenant_id=tenant_id_str, lead_id=lead_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    try:
        await log_activity(
            db,
            tenant_id=tenant_id_str,
            actor_id=actor_id,
            action="lead.delete",
            target_type="lead",
            target_id=str(lead_id),
            payload={"source": res.items[0].source if res.items else None},
        )
    except Exception:
        pass
    await db.commit()


@router.post("/bulk/auto-process-queue", response_model=BulkAutoProcessQueueResponse)
async def bulk_auto_process_meta_queue_endpoint(
    body: BulkAutoProcessQueueRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
) -> BulkAutoProcessQueueResponse:
    """
    §2.3 Auto-fix: re-run lead processing for Meta **and csv_import** leads stuck in needs_routing / failed
    (up to max_items). Same Team-tier gate as other bulk lead automation helpers.
    """
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    plan = await resolve_tenant_plan_code(db, tenant_id_str)
    if not plan_allows_team_tier_features(plan, tenant_id=tenant_id_str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "plan_requires_team",
                "feature": "leads_bulk_auto_process_queue",
                "plan": plan,
            },
        )
    tenant_row = await db.get(Tenant, tenant_id_str)
    lic_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id_str).limit(1))
    ).scalar_one_or_none()
    billing_restrictions.ensure_billing_allows_side_effects(tenant_row, lic_row)
    raw = await service.bulk_auto_process_meta_lead_queue(
        db,
        tenant_id=tenant_id_str,
        own_company_id=own_company_id or None,
        max_items=body.max_items,
        only_without_candidate=body.only_without_candidate,
        error_equals=body.error_equals,
        concurrency=body.concurrency,
        force_candidate_conversion=body.force_candidate_conversion,
    )
    items = [BulkAutoProcessQueueItemOut(**row) for row in raw["results"]]
    return BulkAutoProcessQueueResponse(
        results=items,
        attempted=int(raw["attempted"]),
        succeeded=int(raw["succeeded"]),
        failed=int(raw["failed"]),
    )


@router.post("/bulk/process-new-queue", response_model=BulkAutoProcessQueueResponse)
async def bulk_process_new_meta_queue_endpoint(
    body: BulkAutoProcessQueueRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
) -> BulkAutoProcessQueueResponse:
    """
    §2.10 NBA: batch-run Meta pipeline for leads still in status=new (up to max_items, FIFO by created_at).
    Same Team-tier gate as /bulk/auto-process-queue.
    """
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    plan = await resolve_tenant_plan_code(db, tenant_id_str)
    if not plan_allows_team_tier_features(plan, tenant_id=tenant_id_str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "plan_requires_team",
                "feature": "leads_bulk_process_new_queue",
                "plan": plan,
            },
        )
    tenant_row = await db.get(Tenant, tenant_id_str)
    lic_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id_str).limit(1))
    ).scalar_one_or_none()
    billing_restrictions.ensure_billing_allows_side_effects(tenant_row, lic_row)
    raw = await service.bulk_auto_process_meta_lead_queue(
        db,
        tenant_id=tenant_id_str,
        own_company_id=own_company_id or None,
        max_items=body.max_items,
        statuses=("new",),
        prefer_oldest_first=True,
        concurrency=body.concurrency,
        force_candidate_conversion=body.force_candidate_conversion,
    )
    items = [BulkAutoProcessQueueItemOut(**row) for row in raw["results"]]
    return BulkAutoProcessQueueResponse(
        results=items,
        attempted=int(raw["attempted"]),
        succeeded=int(raw["succeeded"]),
        failed=int(raw["failed"]),
    )


@router.patch("/bulk", response_model=BulkLeadUpdateResponse)
async def bulk_update_leads_endpoint(
    payload: BulkLeadUpdateRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
) -> BulkLeadUpdateResponse:
    from backend.app.modules.leads import crud

    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    lead_ids = [str(item) for item in payload.lead_ids]
    actor_id = str(current_user.sub or "").strip() or None

    if payload.stage is not None or payload.status is not None:
        tenant_row = await db.get(Tenant, tenant_id_str)
        lic_row = (
            await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id_str).limit(1))
        ).scalar_one_or_none()
        billing_restrictions.ensure_billing_allows_side_effects(tenant_row, lic_row)

    stage_transitions: list[tuple[str, Any, Any]] = []
    status_transitions: list[tuple[str, Any, Any]] = []
    prev_candidate_by_lead: dict[str, Any] = {}
    if payload.stage is not None and lead_ids:
        prev_rows = await db.execute(
            select(Lead.id, Lead.stage, Lead.status, Lead.candidate_id).where(
                Lead.tenant_id == tenant_id_str,
                Lead.id.in_(lead_ids),
            )
        )
        new_stage_s = str(payload.stage)
        for row in prev_rows.all():
            lid, prev, prev_status, prev_candidate_id = row[0], row[1], row[2], row[3]
            prev_candidate_by_lead[str(lid)] = prev_candidate_id
            if str(prev or "") != new_stage_s:
                stage_transitions.append((str(lid), prev, prev_status))
    if payload.status is not None and lead_ids:
        prev_rows_status = await db.execute(
            select(Lead.id, Lead.stage, Lead.status, Lead.candidate_id).where(
                Lead.tenant_id == tenant_id_str,
                Lead.id.in_(lead_ids),
            )
        )
        new_status_s = str(payload.status)
        for row in prev_rows_status.all():
            lid, prev_stage, prev_status, prev_candidate_id = row[0], row[1], row[2], row[3]
            prev_candidate_by_lead.setdefault(str(lid), prev_candidate_id)
            if str(prev_status or "") != new_status_s:
                status_transitions.append((str(lid), prev_stage, prev_status))

    enforcement_mode = await next_action_enforcement.get_next_action_enforcement_mode(db, tenant_id=tenant_id_str)
    if enforcement_mode in {"warn", "block"} and payload.stage is not None and stage_transitions:
        for lid, _prev, _prev_status in stage_transitions:
            if await next_action_enforcement.lead_has_active_next_action_reminder(
                db, tenant_id=tenant_id_str, lead_id=lid
            ):
                continue
            await next_action_enforcement.maybe_log_missing_next_action(
                db,
                tenant_id=tenant_id_str,
                actor_id=actor_id,
                lead_id=lid,
                attempted_stage=payload.stage,
                mode=enforcement_mode,
            )
            if enforcement_mode == "block":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Next action required: create an activity before changing stage (one or more selected leads).",
                )

    updated = await crud.bulk_update_leads(
        db,
        tenant_id=tenant_id_str,
        lead_ids=lead_ids,
        stage=payload.stage,
        status=payload.status,
    )

    lost_rc: str | None = None
    lost_rn: str | None = None
    if payload.stage is not None and str(payload.stage) == "lost":
        lost_rc = payload.lost_reason_code
        lost_rn = payload.lost_reason_note

    for lid, prev_stage, _prev_status in stage_transitions:
        lead_row = await crud.get_lead(db, tenant_id=tenant_id_str, lead_id=lid)
        if not lead_row:
            continue
        if payload.stage is not None:
            ns = str(payload.stage)
            ps = str(prev_stage or "")
            norm = dict(lead_row.normalized or {})
            if ns == "lost":
                lr_block: Dict[str, Any] = {"at": datetime.now(timezone.utc).isoformat()}
                if actor_id:
                    lr_block["set_by"] = actor_id
                if lost_rc:
                    lr_block["code"] = lost_rc
                if lost_rn:
                    lr_block["note"] = lost_rn
                norm["lead_lost_reason_v1"] = lr_block
                lead_row.normalized = norm
            elif ps == "lost":
                norm.pop("lead_lost_reason_v1", None)
                lead_row.normalized = norm
            await db.flush()
        await pipeline_hooks.record_lead_stage_change(
            db,
            tenant_id=tenant_id_str,
            lead=lead_row,
            from_stage=prev_stage,
            to_stage=payload.stage,
            actor_id=actor_id,
            lost_reason_code=lost_rc if str(payload.stage or "") == "lost" else None,
            lost_reason_note=lost_rn if str(payload.stage or "") == "lost" else None,
        )
    try:
        await log_activity(
            db,
            tenant_id=tenant_id_str,
            actor_id=actor_id,
            action="lead.bulk_update",
            target_type="lead",
            target_id="bulk",
            payload={
                "count": len(lead_ids),
                "updated": updated,
                "stage": payload.stage,
                "status": payload.status,
                "stage_hook_count": len(stage_transitions),
                **(
                    {
                        "lost_reason_code": lost_rc,
                        "lost_reason_note": lost_rn,
                    }
                    if str(payload.stage or "") == "lost"
                    else {}
                ),
            },
        )
    except Exception:
        pass
    await db.commit()
    cleanup_targets: dict[str, tuple[Any, Any]] = {}
    for lid, prev_stage, prev_status in stage_transitions:
        cleanup_targets[lid] = (prev_stage, prev_status)
    for lid, prev_stage, prev_status in status_transitions:
        cleanup_targets.setdefault(lid, (prev_stage, prev_status))

    for lid, (prev_stage, prev_status) in cleanup_targets.items():
        lead_row = await crud.get_lead(db, tenant_id=tenant_id_str, lead_id=lid)
        if lead_row:
            try:
                await maybe_apply_lead_silence_cleanup(
                    db,
                    tenant_id=tenant_id_str,
                    lead_id=lid,
                    old_stage=prev_stage,
                    new_stage=getattr(lead_row, "stage", None),
                    old_status=prev_status,
                    new_status=getattr(lead_row, "status", None),
                    old_candidate_id=prev_candidate_by_lead.get(lid),
                    new_candidate_id=getattr(lead_row, "candidate_id", None),
                    actor_id=actor_id,
                )
                await db.commit()
            except Exception:
                await db.rollback()
        if lead_row and payload.stage is not None and any(t[0] == lid for t in stage_transitions):
            await pipeline_hooks.run_lead_stage_change_automations(
                db,
                tenant_id=tenant_id_str,
                lead=lead_row,
                from_stage=prev_stage,
                to_stage=payload.stage,
                actor_id=actor_id,
            )
    return BulkLeadUpdateResponse(updated=updated)


@router.post("/{lead_id}/service-order", response_model=ServiceOrderOut)
async def create_service_order_from_lead(
    lead_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
):
    from backend.app.modules.leads import crud

    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    lead = await crud.get_lead(db, tenant_id=tenant_id_str, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    business_type = await service._load_tenant_business_type(db, tenant_id_str)
    if business_type != "services":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Service order conversion is only available for services tenants")

    normalized = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    existing_order_id = str(normalized.get("service_order_id") or "").strip() or None
    svc = AdditionalServicesService(db, tenant_id_str)
    if existing_order_id:
        order = await svc.get_order(existing_order_id)
        return ServiceOrderOut.model_validate(order, from_attributes=True)

    if not lead.company_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Lead company is not resolved")

    contact_bits = [
        str(normalized.get("full_name") or "").strip(),
        str(normalized.get("email") or "").strip(),
        str(normalized.get("phone") or "").strip(),
    ]
    note_lines = [
        "Created from services lead",
        f"Lead ID: {lead.id}",
        f"Source: {lead.source}",
    ]
    compact_contact = " · ".join([value for value in contact_bits if value])
    if compact_contact:
        note_lines.append(f"Contact: {compact_contact}")

    order = await svc.create_order(
        {
            "company_id": lead.company_id,
            "currency": "PLN",
            "notes": "\n".join(note_lines),
            "requested_by": str(getattr(current_user, "sub", "") or ""),
            "audit": {
                "source": "lead_conversion",
                "lead_id": lead.id,
                "lead_status": lead.status,
                "lead_stage": lead.stage,
            },
        },
        [],
    )

    normalized["service_order_id"] = order.id
    normalized["service_order_created_at"] = order.created_at.isoformat() if getattr(order, "created_at", None) else None
    lead.normalized = normalized
    await db.commit()
    order = await svc.get_order(order.id)
    return ServiceOrderOut.model_validate(order, from_attributes=True)


@router.post("/{lead_id}/duplicate-decision", response_model=LeadOut)
async def lead_duplicate_decision_endpoint(
    lead_id: str,
    payload: LeadDuplicateDecisionRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
) -> LeadOut:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    actor_id = str(current_user.sub or "").strip() or None

    from backend.app.modules.leads import duplicate_decision as _duplicate_decision

    try:
        await _duplicate_decision.apply_lead_duplicate_decision(
            db,
            tenant_id=tenant_id_str,
            lead_id=lead_id,
            actor_id=actor_id,
            decision=str(payload.decision),
            note=payload.note,
        )
    except HTTPException:
        raise

    res = await service.list_leads(
        db,
        tenant_id=tenant_id_str,
        own_company_id=own_company_id,
        only_lead_id=lead_id,
        limit=1,
        offset=0,
    )
    if not res.items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return res.items[0]


@router.post("/{lead_id}/confirm-vacancy", response_model=LeadOut)
async def confirm_lead_vacancy_endpoint(
    lead_id: str,
    payload: LeadVacancyConfirmIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
) -> LeadOut:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    actor_id = str(current_user.sub or "").strip() or None
    try:
        await service.confirm_lead_vacancy(
            db,
            tenant_id=tenant_id_str,
            lead_id=lead_id,
            vacancy_id=str(payload.vacancy_id),
            actor_sub=actor_id,
        )
    except service.LeadProcessingError as exc:
        raise service.lead_processing_error_as_http(exc) from exc

    res = await service.list_leads(
        db,
        tenant_id=tenant_id_str,
        own_company_id=own_company_id,
        only_lead_id=lead_id,
        limit=1,
        offset=0,
    )
    if not res.items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return res.items[0]


@router.post("/{lead_id}/intake-decision", response_model=LeadOut)
async def lead_intake_decision_endpoint(
    lead_id: str,
    payload: LeadIntakeDecisionIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
) -> LeadOut:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    actor_id = str(current_user.sub or "").strip() or None
    try:
        await service.apply_lead_intake_decision(
            db,
            tenant_id=tenant_id_str,
            lead_id=lead_id,
            decision=str(payload.decision),
            actor_sub=actor_id,
            reason_code=str(payload.reason_code).strip() if payload.reason_code else None,
            note=payload.note,
            funnel_id=str(payload.funnel_id) if payload.funnel_id else None,
        )
    except service.LeadProcessingError as exc:
        raise service.lead_processing_error_as_http(exc) from exc

    res = await service.list_leads(
        db,
        tenant_id=tenant_id_str,
        own_company_id=own_company_id,
        only_lead_id=lead_id,
        limit=1,
        offset=0,
    )
    if not res.items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return res.items[0]


@router.post("/{lead_id}/process", response_model=MetaLeadResponse)
async def process_lead_endpoint(
    lead_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: str = Depends(resolve_active_own_company_id),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter)),
) -> MetaLeadResponse:
    """
    Manually process (route/convert) a stored lead.

    Supported sources: ``meta``, ``csv_import`` (same pipeline as Meta; source must match the row).
    """
    from backend.app.modules.leads import crud

    _MANUAL_PROCESS_SOURCES = frozenset({"meta", "csv_import"})

    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    lead = await crud.get_lead(db, tenant_id=tenant_id_str, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    lead_src = str(getattr(lead, "source", "") or "").strip().lower()
    if lead_src not in _MANUAL_PROCESS_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Lead processing is only available for Meta or CSV-import leads",
        )
    if not getattr(lead, "payload", None):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Lead payload is missing")

    block = service.manual_process_block_code(lead)
    if block:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": block},
        )

    try:
        await log_activity(
            db,
            tenant_id=tenant_id_str,
            actor_id=str(current_user.sub or "").strip() or None,
            action="lead.manual_process",
            target_type="lead",
            target_id=str(lead.id),
            payload={
                "lead_id": str(lead.id),
                "source": lead_src,
                "status_before": getattr(lead, "status", None),
                "stage_before": getattr(lead, "stage", None),
            },
        )
    except Exception:
        pass

    # If the lead is marked as processed but has no resulting candidate,
    # we must force re-processing. Otherwise the service will skip the pipeline.
    force_existing = bool(getattr(lead, "candidate_id", None) is None) and getattr(lead, "status", None) in {
        "processed",
        "duplicated",
        "duplicate_review",
    }

    prior_norm = getattr(lead, "normalized", None)
    if not isinstance(prior_norm, dict):
        prior_norm = None

    try:
        result = await service.reprocess_stored_lead_payload(
            db=db,
            tenant_id=tenant_id_str,
            payload=lead.payload,
            own_company_id=own_company_id,
            source=lead_src,
            force_existing=force_existing,
            external_id_hint=(str(lead.external_id).strip() if getattr(lead, "external_id", None) else None),
            prior_normalized=prior_norm,
            stored_db_vacancy_id=(str(lead.vacancy_id).strip() if getattr(lead, "vacancy_id", None) else None)
            or None,
            stored_db_ad_id=getattr(lead, "ad_id", None),
            stored_lead_id=str(lead.id),
        )
    except service.LeadProcessingError as exc:
        raise service.lead_processing_error_as_http(exc) from exc

    try:
        await log_activity(
            db,
            tenant_id=tenant_id_str,
            actor_id=str(current_user.sub or "").strip() or None,
            action="lead.manual_process.done",
            target_type="lead",
            target_id=str(lead.id),
            payload={
                "lead_id": str(lead.id),
                "status_after": result.status,
                "candidate_id": result.candidate_id,
                "recruiter_id": result.recruiter_id,
                "outcome_entity_type": result.outcome_entity_type,
                "outcome_entity_id": result.outcome_entity_id,
            },
        )
    except Exception:
        pass

    await db.commit()
    return result.to_schema()


@router.post("/meta", response_model=MetaLeadResponse)
async def ingest_meta_lead(
    request: Request,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> MetaLeadResponse:
    body = await request.body()
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)

    header_signature = request.headers.get("X-Hub-Signature-256")
    signatures = await admin_service.get_active_secret_candidates(db, tenant_id)
    signature_status = "not_configured"

    if signatures:
        if not header_signature:
            await admin_service.mark_signature_status(db, tenant_id, "missing_header")
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature header")

        matched = False
        matched_credential = None
        for credential_id, credential_obj, secret in signatures:
            if _signature_matches(secret, body, header_signature):
                matched = True
                matched_credential = credential_obj
                break

        if not matched:
            await admin_service.mark_signature_status(db, tenant_id, "mismatch")
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature mismatch")

        signature_status = "ok"
        await admin_service.mark_credential_verified(db, matched_credential)
    else:
        signature_status = "not_configured"

    try:
        payload = await request.json()
    except Exception as exc:  # pragma: no cover - invalid payload
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    try:
        result = await service.process_meta_lead(
            db=db,
            tenant_id=str(tenant_id),
            payload=payload,
        )
    except service.LeadProcessingError as exc:
        raise service.lead_processing_error_as_http(exc) from exc

    await admin_service.mark_signature_status(db, tenant_id, signature_status)
    await db.commit()

    return result.to_schema()


@router.get("/{lead_id}/timeline", response_model=LeadTimelineResponse)
async def get_lead_timeline_endpoint(
    lead_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> LeadTimelineResponse:
    """Unified lead timeline for side-panel History tab."""
    db, tenant_id = db_tenant
    return await service.get_lead_timeline(
        db,
        tenant_id=str(tenant_id),
        lead_id=lead_id,
    )
