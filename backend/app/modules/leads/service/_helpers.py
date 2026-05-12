"""Small helpers for the leads service package.

Extracted from ``backend/app/modules/leads/service/__init__.py`` (Phase 1 #3
god-module split, step 2/N) — types, validators, loaders, event/reminder
helpers, processing-mode resolution, vacancy resolution, and qualification
preview/audit. Re-exported via ``service/__init__.py`` for the historical
``service.<name>`` access pattern (router, admin_service, scripts, tests).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Company, Lead, OwnCompany, Tenant, User, Vacancy
from backend.app.models.user import Role
from backend.app.modules.leads import crud
from backend.app.modules.leads.lead_criteria_eval import (
    evaluate_vacancy_for_lead,
    ordered_vacancy_ids_from_tenant_settings,
)
from backend.app.modules.leads.recruiter_validation import validate_tenant_recruiter_id
from backend.app.modules.leads.schemas import MetaLeadResponse
from backend.app.services import events, reminder_tasks
from backend.app.services.events import EventAudience
from backend.app.services.plan_feature_gates import (
    plan_allows_team_tier_features,
    resolve_tenant_plan_code,
)


@dataclass
class MetaLeadRetryOutcome:
    lead_id: str
    status_before: str
    status_after: str
    candidate_id: Optional[str]
    error_before: Optional[str]
    error_after: Optional[str]
    processed: bool
    message: Optional[str] = None


@dataclass
class MetaLeadResult:
    lead_id: str
    status: str
    vacancy_id: Optional[str]
    candidate_id: Optional[str]
    recruiter_id: Optional[str]
    business_type: Optional[str] = None
    outcome_entity_type: Optional[str] = None
    outcome_entity_id: Optional[str] = None
    outcome_entity_name: Optional[str] = None
    error: Optional[str] = None
    is_new: bool = False

    def to_schema(self) -> MetaLeadResponse:
        return MetaLeadResponse(
            lead_id=UUID(self.lead_id),
            status=self.status,  # type: ignore[arg-type]
            vacancy_id=UUID(self.vacancy_id) if self.vacancy_id else None,
            candidate_id=UUID(self.candidate_id) if self.candidate_id else None,
            recruiter_id=UUID(self.recruiter_id) if self.recruiter_id else None,
            business_type=self.business_type,
            outcome_entity_type=self.outcome_entity_type,
            outcome_entity_id=UUID(self.outcome_entity_id) if self.outcome_entity_id else None,
            outcome_entity_name=self.outcome_entity_name,
            error=self.error,
        )


def _normalize_business_type(raw_business_type: Any, tenant_type: Any) -> str:
    normalized = str(raw_business_type or "").strip().lower()
    if normalized in {"agency", "employer", "services"}:
        return normalized
    tenant_type_value = str(getattr(tenant_type, "value", tenant_type or "")).strip().lower()
    return "employer" if tenant_type_value == "company" else "agency"


async def _load_tenant_business_type(db: AsyncSession, tenant_id: str, own_company_id: Optional[str] = None) -> str:
    # Source of truth should be the active OwnCompany business type (OwnCompany.extra),
    # so the whole scenario (agency/employer/services) follows the Topbar selection.
    #
    # Backward compatibility:
    # - if `own_company_id` is not provided or OwnCompany.extra does not contain business_type,
    #   we fall back to legacy operating profile (Company.extra) and then to Tenant.settings.
    operating_company_type: Optional[str] = None
    if own_company_id:
        try:
            row = await db.execute(
                select(OwnCompany.extra)
                .where(OwnCompany.tenant_id == tenant_id, OwnCompany.id == own_company_id, OwnCompany.is_archived.is_(False))
                .limit(1)
            )
            extra = row.scalar_one_or_none()
            if isinstance(extra, dict):
                ct = (
                    extra.get("business_type")
                    or extra.get("company_type")
                    or extra.get("company_kind")
                    or extra.get("kind")
                )
                if isinstance(ct, str) and ct.strip().lower() in {"agency", "employer", "services"}:
                    operating_company_type = ct.strip().lower()
        except Exception:
            operating_company_type = None

    # Legacy fallback: operating company type from Company.extra (company_role="operating").
    # tenant.settings/business_type may be stale after legacy migrations or incomplete updates,
    # which leads to wrong leads conversion (candidate vs service order).
    try:
        if operating_company_type is None:
            # We fetch a small window of companies and select the one marked as operating in `extra`.
            # (Avoids fragile JSON querying across DB dialects.)
            rows = await db.execute(
                select(Company.extra)
                .where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
                .order_by(Company.created_at.asc())
                .limit(50)
            )
            for (extra,) in rows.all():
                if not isinstance(extra, dict):
                    continue
                role = str(extra.get("company_role") or "").strip().lower()
                if role != "operating":
                    continue
                ct = extra.get("company_type") or extra.get("business_type") or extra.get("company_kind") or extra.get("kind")
                if isinstance(ct, str) and ct.strip().lower() in {"agency", "employer", "services"}:
                    operating_company_type = ct.strip().lower()
                    break
    except Exception:
        operating_company_type = None

    row = (await db.execute(select(Tenant.settings, Tenant.type).where(Tenant.id == tenant_id).limit(1))).first()
    if not row:
        return "agency"
    settings_payload, tenant_type = row
    settings_dict = settings_payload if isinstance(settings_payload, dict) else {}
    raw = operating_company_type if operating_company_type is not None else settings_dict.get("business_type")
    return _normalize_business_type(raw, tenant_type)


def _build_lead_outcome(
    *,
    business_type: str,
    company_id: Optional[str],
    company_name: Optional[str],
    candidate_id: Optional[str],
    candidate_name: Optional[str],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if business_type == "services":
        return ("company", company_id, company_name or company_id)
    if candidate_id:
        return ("candidate", candidate_id, candidate_name or candidate_id)
    return ("company", company_id, company_name or company_id)


async def _emit_lead_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    event_type: str,
    candidate_id: Optional[str] = None,
    recruiter_id: Optional[str] = None,
    roles: Optional[List[Role | str]] = None,
    user_ids: Optional[List[str]] = None,
    error: Optional[str] = None,
    business_type: Optional[str] = None,
    outcome_entity_type: Optional[str] = None,
    outcome_entity_id: Optional[str] = None,
    outcome_entity_name: Optional[str] = None,
) -> None:
    payload = {
        "lead_id": lead.id,
        "status": lead.status,
        "business_type": business_type,
        "company_id": lead.company_id,
        "vacancy_id": lead.vacancy_id,
        "candidate_id": candidate_id,
        "recruiter_id": recruiter_id,
        "outcome_entity_type": outcome_entity_type,
        "outcome_entity_id": outcome_entity_id,
        "outcome_entity_name": outcome_entity_name,
        "error": error,
    }
    audience = EventAudience(
        user_ids=[uid for uid in (user_ids or []) if uid],
        roles=roles,
    )
    await events.emit_event(
        db,
        tenant_id=tenant_id,
        event_type=event_type,
        payload=payload,
        entity_type="lead",
        entity_id=lead.id,
        audience=audience,
    )


async def _load_supervisor_id(
    db: AsyncSession,
    recruiter_id: Optional[str],
) -> Optional[str]:
    if not recruiter_id:
        return None
    row = await db.execute(select(User.supervisor_id).where(User.id == recruiter_id))
    value = row.scalar_one_or_none()
    return value if value else None


async def _pick_lead_assignee_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    preferred_user_id: Optional[str] = None,
    normalized: Optional[Dict[str, Any]] = None,
    lead_id: Optional[str] = None,
) -> Optional[str]:
    """
    Actor for lead.processed automations and related side effects.

    Order:
    1) Automatic lead distribution (Tenant.settings.lead_distribution_v1, team/pro plan) when mode=automatic.
    2) preferred_user_id (vacancy recruiter, supervisor, meta fallback recruiter).
    3) Legacy: first active administrator/supervisor/manager on tenant.
    """
    from backend.app.services.lead_distribution import pick_assignee_user_id_for_ingest

    dist_id = await pick_assignee_user_id_for_ingest(
        db,
        tenant_id=tenant_id,
        normalized=normalized,
        lead_id=lead_id,
    )
    if dist_id:
        return dist_id
    if preferred_user_id:
        return preferred_user_id
    row = await db.execute(
        select(User.id)
        .where(
            User.is_active.is_(True),
            or_(User.tenant_id == tenant_id, User.tenant_id.is_(None)),
            User.role.in_(["administrator", "supervisor", "manager", "admin", "owner"]),
        )
        .order_by(User.created_at.asc())
        .limit(1)
    )
    return row.scalar_one_or_none()


async def _create_lead_followup_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    assignee_id: str,
    title: str,
    payload: Dict[str, Any],
) -> None:
    try:
        await reminder_tasks.create_reminder(
            db,
            tenant_id=tenant_id,
            actor_id=assignee_id,
            payload={
                "title": title,
                "type": "custom",
                "entity_type": "lead",
                "entity_id": str(lead.id),
                "assignee_id": assignee_id,
                "priority": "normal",
                "channel": "internal",
                "due_at": datetime.now(timezone.utc) + timedelta(hours=1),
                "payload": payload,
            },
        )
    except Exception:
        # best-effort: lead processing must not fail due to reminder creation
        return


class LeadProcessingError(Exception):
    def __init__(self, status: str, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def lead_processing_error_as_http(exc: LeadProcessingError) -> HTTPException:
    if exc.status == "billing_blocked":
        if exc.message == "BILLING_TRIAL_EXPIRED":
            return HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "billing_trial_expired",
                    "message": "Your trial has ended. Choose a plan in Billing to create new leads.",
                },
            )
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "billing_past_due",
                "message": "New leads are paused until subscription payment succeeds. Open Billing to retry payment.",
            },
        )
    if exc.status == "not_found":
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)


async def _validate_company_id(
    db: AsyncSession,
    tenant_id: str,
    company_id: Optional[str],
) -> Optional[str]:
    if not company_id:
        return None
    stmt = select(Company.id).where(
        Company.id == company_id,
        Company.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _load_settings(
    db: AsyncSession,
    tenant_id: str,
):
    entry = await crud.get_meta_settings(db, tenant_id=tenant_id)
    if entry:
        return entry
    return await crud.create_meta_settings(
        db,
        tenant_id=tenant_id,
        auto_create_enabled=True,
        mask_pii_in_logs=True,
    )


def _normalize_stored_leads_processing_mode_v1(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in ("manual", "assisted", "automatic"):
        return s
    return "assisted"


async def _apply_leads_processing_mode_v1_to_normalized(
    db: AsyncSession,
    *,
    tenant_id: str,
    normalized: Dict[str, Any],
    settings_row: Any,
) -> Dict[str, Any]:
    """
    Stamp configured + effective qualification mode on lead.normalized (§2.10 / §2.3).
    Automatic without Team-tier plan is downgraded to manual for this ingest only.
    """
    stored = _normalize_stored_leads_processing_mode_v1(
        getattr(settings_row, "leads_processing_mode_v1", None)
    )
    effective = stored
    downgrade: Optional[str] = None
    if stored == "automatic":
        plan = await resolve_tenant_plan_code(db, tenant_id)
        if not plan_allows_team_tier_features(plan, tenant_id=tenant_id):
            effective = "manual"
            downgrade = "team_plan_required"
    normalized["leads_processing_mode_configured_v1"] = stored
    normalized["leads_processing_mode_v1"] = effective
    if downgrade:
        normalized["leads_processing_mode_downgrade_v1"] = downgrade
    else:
        normalized.pop("leads_processing_mode_downgrade_v1", None)
    return normalized


async def _validate_recruiter_id(
    db: AsyncSession,
    tenant_id: str,
    recruiter_id: Optional[str],
) -> Optional[str]:
    return await validate_tenant_recruiter_id(db, tenant_id, recruiter_id)


def _rule_recruiter_id_from_normalized(normalized: Dict[str, Any]) -> Optional[str]:
    raw = normalized.get("lead_qualification_rule_match_v1")
    if not isinstance(raw, dict):
        return None
    rid = raw.get("recruiter_id")
    if rid is None:
        return None
    s = str(rid).strip()
    return s or None


def _vacancy_allows_auto_convert_on_fit(vacancy: Optional[Vacancy]) -> bool:
    """Vacancy.extra.leads_auto_convert_on_fit_v1 == False opts out of tenant automatic conversion (§2.4)."""
    if vacancy is None:
        return True
    raw = getattr(vacancy, "extra", None)
    if raw is None:
        return True
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except Exception:
            return True
        if not isinstance(obj, dict):
            return True
        data = obj
    elif isinstance(raw, dict):
        data = raw
    else:
        return True
    if data.get("leads_auto_convert_on_fit_v1") is False:
        return False
    return True


async def _resolve_vacancy(
    db: AsyncSession,
    tenant_id: str,
    normalized: Dict[str, Any],
    *,
    own_company_id: Optional[str] = None,
) -> Optional[Vacancy]:
    for raw_vid in (normalized.get("vacancy_id"), normalized.get("vacancy_id_hint")):
        if not raw_vid:
            continue
        try:
            vacancy_id = str(UUID(str(raw_vid).strip()))
        except ValueError:
            continue
        vacancy = await crud.resolve_vacancy_by_id(
            db, tenant_id, vacancy_id, scoped_own_company_id=own_company_id
        )
        if vacancy:
            return vacancy
        # Lead row / UI may point at a vacancy whose own_company differs from the lead's active scope.
        # Scoped lookup intentionally hides it; still resolve by tenant + id for explicit UUID routing.
        vacancy = await crud.resolve_vacancy_by_id(
            db, tenant_id, vacancy_id, scoped_own_company_id=None
        )
        if vacancy:
            return vacancy

    ad_int = normalized.get("ad_id")
    vacancy = await crud.resolve_vacancy_by_ad(
        db, tenant_id, ad_int, scoped_own_company_id=own_company_id
    )
    if vacancy:
        return vacancy
    vacancy = await crud.resolve_vacancy_by_ad(
        db, tenant_id, ad_int, scoped_own_company_id=None
    )
    if vacancy:
        return vacancy

    return None


async def resolve_vacancy_for_lead_processing(
    db: AsyncSession,
    *,
    tenant_id: str,
    normalized: Dict[str, Any],
    tenant_settings: Dict[str, Any],
    source: str = "",
    own_company_id: Optional[str] = None,
) -> Tuple[Optional[Vacancy], Optional[str], List[str]]:
    """
    Single routing path for ingest (§2.10):
    1) Explicit vacancy_id / Meta ad map — always wins; fit is evaluated for that vacancy only.
    2) Else: AutomationRule trigger `lead.qualification` (priority desc) — set_vacancy_id + fit eval;
       optional actions.set_recruiter_id (active user of tenant) stamped on match and applied at convert.
    3) Else: Tenant.settings.lead_fit_routing_v1.ordered_vacancy_ids — prefer first vacancy with
       fit or no_criteria; if none pass, attach the **first resolvable** row in that order so ingest
       does not end with VACANCY_NOT_RESOLVED when the list is configured (no_fit / needs_info flow to triage).
    4) Else: **Last resort** — oldest active open vacancy for the tenant (scoped to OwnCompany when possible);
       stamps ``vacancy_routing_fallback_v1`` on ``normalized`` and bypasses assisted/fit triage gates in
       ``process_normalized_lead`` so a candidate can still be created.
    """
    primary = await _resolve_vacancy(
        db, tenant_id, normalized, own_company_id=own_company_id
    )
    if primary is not None:
        st, rs = evaluate_vacancy_for_lead(normalized, primary.extra)
        return primary, st, rs
    from backend.app.modules.leads.lead_qualification_rules import pick_vacancy_via_qualification_rules

    picked = await pick_vacancy_via_qualification_rules(
        db,
        tenant_id=tenant_id,
        source=source,
        normalized=normalized,
        own_company_id=own_company_id,
    )
    if picked is not None:
        v, st, rs = picked
        return v, st, rs
    first_ordered_fallback: Optional[Tuple[Vacancy, str, List[str]]] = None
    for vid in ordered_vacancy_ids_from_tenant_settings(tenant_settings):
        v = await crud.resolve_vacancy_by_id(
            db, tenant_id, vid, scoped_own_company_id=own_company_id
        )
        if v is None:
            continue
        st, rs = evaluate_vacancy_for_lead(normalized, v.extra)
        if st in ("fit", "no_criteria"):
            return v, st, rs
        if first_ordered_fallback is None:
            first_ordered_fallback = (v, st, rs)
    if first_ordered_fallback is not None:
        v, st, rs = first_ordered_fallback
        return v, st, rs
    v_last = await crud.last_resort_first_open_vacancy_for_tenant(
        db,
        tenant_id=tenant_id,
        scoped_own_company_id=own_company_id,
    )
    if v_last is not None:
        normalized["vacancy_routing_fallback_v1"] = {
            "kind": "last_resort_first_active",
            "vacancy_id": str(v_last.id),
            "title": getattr(v_last, "title", None),
        }
        st, rs = evaluate_vacancy_for_lead(normalized, v_last.extra)
        return v_last, st, rs
    return None, None, []


def _triage_bypass_from_vacancy_fallback(normalized: Dict[str, Any]) -> bool:
    raw = normalized.get("vacancy_routing_fallback_v1")
    return isinstance(raw, dict) and raw.get("kind") == "last_resort_first_active"


def _stamp_lead_qualification_preview_v1(
    normalized: Dict[str, Any],
    *,
    vacancy: Optional[Vacancy],
    fit_status: Optional[str],
    fit_reasons: List[str],
    blocked_auto_convert: bool = False,
) -> None:
    normalized["lead_qualification_preview_v1"] = {
        "suggested_vacancy_id": str(vacancy.id) if vacancy else None,
        "fit_status": fit_status,
        "fit_reasons": list(fit_reasons or []),
        "blocked_auto_convert": bool(blocked_auto_convert),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _audit_lead_qualification_rule_match(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    normalized: Dict[str, Any],
) -> None:
    raw = normalized.get("lead_qualification_rule_match_v1")
    if not isinstance(raw, dict) or not raw.get("rule_id"):
        return
    from backend.app.services.audit import log_activity

    await log_activity(
        db,
        tenant_id=tenant_id,
        action="lead.qualification_rule_matched",
        target_type="lead",
        target_id=str(lead_id),
        payload={k: v for k, v in raw.items() if v is not None},
    )
