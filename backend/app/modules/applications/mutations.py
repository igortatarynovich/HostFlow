"""Delegate intake mutations to leads service; return Application read models."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.auth.deps import UserCtx
from backend.app.models import Lead
from backend.app.modules.applications.mappers import (
    lead_to_recruitment_application,
    sales_inquiry_to_application,
)
from backend.app.modules.applications.sales_resolve import resolve_sales_inquiry_and_lead
from backend.app.modules.applications.schemas import (
    ApplicationAssignIn,
    ApplicationCommentIn,
    ApplicationFollowUpIn,
    ApplicationIntakeDecisionIn,
    ApplicationOut,
    ApplicationProcessResult,
    ApplicationStagePatch,
    ApplicationVacancyConfirmIn,
)
from backend.app.modules.leads import crud, service
from backend.app.modules.leads.schemas import LeadStageUpdate
from backend.app.modules.leads.service.intake_decision import INTAKE_DECISION_QUALIFY


async def _vacancy_id_from_meta_ad_map(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> Optional[str]:
    """Resolve vacancy from Meta ad→vacancy map when the operator has not bound one yet."""
    raw_ad = getattr(lead, "ad_id", None)
    if raw_ad is None:
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        raw_ad = norm.get("ad_id")
    if raw_ad is None or str(raw_ad).strip() == "":
        return None
    try:
        ad_id = int(str(raw_ad).strip())
    except (TypeError, ValueError):
        return None
    entry = await crud.get_meta_ads_entry(db, tenant_id=tenant_id, ad_id=ad_id)
    if entry is None or not getattr(entry, "vacancy_id", None):
        return None
    return str(entry.vacancy_id).strip() or None


async def _prepare_recruitment_application_for_process(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
    current_user: UserCtx,
) -> None:
    """Clear common intake gates when recruiter explicitly creates a candidate from Отклики."""
    actor_id = str(current_user.sub or "").strip() or None
    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    block = await service.manual_process_block_code(db, tenant_id, lead)
    if block == "INTAKE_INFO_REQUESTED":
        try:
            await service.apply_lead_intake_decision(
                db,
                tenant_id=tenant_id,
                lead_id=application_id,
                decision=INTAKE_DECISION_QUALIFY,
                actor_sub=actor_id,
            )
        except service.LeadProcessingError as exc:
            raise service.lead_processing_error_as_http(exc) from exc
        lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        block = await service.manual_process_block_code(db, tenant_id, lead)

    # Prefer explicit lead.vacancy_id; otherwise apply Meta ads map before pool/routing gates.
    vac_id = str(getattr(lead, "vacancy_id", "") or "").strip()
    if not vac_id:
        vac_id = (await _vacancy_id_from_meta_ad_map(db, tenant_id=tenant_id, lead=lead)) or ""

    lead_has_vacancy = bool(str(getattr(lead, "vacancy_id", "") or "").strip())
    should_confirm = bool(vac_id) and (
        not lead_has_vacancy
        or block
        in {
            "VACANCY_NOT_CONFIRMED",
            "INTAKE_POOL_PATH_REQUIRED",
            "INTAKE_ROUTING_INCOMPLETE",
        }
    )
    if should_confirm:
        try:
            await service.confirm_lead_vacancy(
                db,
                tenant_id=tenant_id,
                lead_id=application_id,
                vacancy_id=vac_id,
                actor_sub=actor_id,
            )
        except service.LeadProcessingError as exc:
            raise service.lead_processing_error_as_http(exc) from exc
        lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
        if not lead:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        block = await service.manual_process_block_code(db, tenant_id, lead)

    if block:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": block},
        )


async def _reload_sales(db: AsyncSession, tenant_id: str, own_company_id: str, application_id: str) -> ApplicationOut:
    try:
        inquiry, lead = await resolve_sales_inquiry_and_lead(
            db,
            tenant_id=tenant_id,
            application_id=application_id,
            ensure_if_lead=True,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found") from exc
    return sales_inquiry_to_application(inquiry, lead)


async def _reload_recruitment(db: AsyncSession, tenant_id: str, application_id: str) -> ApplicationOut:
    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if not lead or (lead.lead_type == "client" and lead.lead_target_type == "client_lead"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return lead_to_recruitment_application(lead)


async def patch_sales_stage(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    application_id: str,
    payload: ApplicationStagePatch,
    current_user: UserCtx,
) -> ApplicationOut:
    from backend.app.modules.leads.router import update_lead_stage_endpoint

    try:
        inquiry, lead = await resolve_sales_inquiry_and_lead(
            db,
            tenant_id=tenant_id,
            application_id=application_id,
            ensure_if_lead=True,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found") from exc

    stage_payload = LeadStageUpdate(
        stage=payload.stage,
        lost_reason_code=payload.lost_reason_code,
        lost_reason_note=payload.lost_reason_note,
    )
    # Lead stage remains the operational projection until SI owns status fully.
    await update_lead_stage_endpoint(
        str(lead.id),
        stage_payload,
        db_tenant=(db, UUID(tenant_id)),
        current_user=current_user,
        _role="recruiter",
    )
    return await _reload_sales(db, tenant_id, own_company_id, str(inquiry.id))


async def run_product_convert_via_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    application_id: str,
    current_user: UserCtx,
    missing_detail: str = "Application not found",
) -> str:
    """Single product convert engine for all HTTP entrypoints.

    Resolves SalesInquiry from the transport Lead facade key (or SI id), runs
    ``convert_sales_inquiry_mapping`` (Review SoT + mapping + lineage + audit),
    and commits. Returns ``sales_inquiry_id``.
    """
    from backend.app.modules.sales.services.capability_spine_read import (
        load_sales_inquiry_for_spine,
    )
    from backend.app.modules.sales.services.convert_mapping import (
        ConvertMappingError,
        convert_sales_inquiry_mapping,
        resolve_convert_provenance_for_inquiry,
    )

    inquiry = await load_sales_inquiry_for_spine(
        db, tenant_id=tenant_id, application_id=application_id
    )
    if inquiry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=missing_detail)

    inquiry_oc = str(getattr(inquiry, "own_company_id", "") or "").strip()
    if own_company_id and inquiry_oc and inquiry_oc != str(own_company_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=missing_detail)

    actor_id = str(current_user.sub or "").strip() or None
    try:
        destination, flights_ledger_id = await resolve_convert_provenance_for_inquiry(
            db,
            tenant_id=tenant_id,
            inquiry=inquiry,
        )
        await convert_sales_inquiry_mapping(
            db,
            tenant_id=tenant_id,
            sales_inquiry_id=str(inquiry.id),
            destination=destination,
            flights_ledger_id=flights_ledger_id,
            actor_id=actor_id,
        )
        await db.commit()
    except ConvertMappingError as exc:
        await db.rollback()
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        if exc.reason in {"invalid_inquiry_state", "missing_flights_reference"}:
            # Missing SI / ledger looks like a bad product target from the facade.
            if exc.reason == "invalid_inquiry_state" and "not found" in exc.message.lower():
                status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": exc.code,
                "reason": exc.reason,
                "message": exc.message,
                "details": exc.details,
            },
        ) from exc

    return str(inquiry.id)


async def convert_sales_inquiry(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    application_id: str,
    current_user: UserCtx,
) -> ApplicationOut:
    """Product convert — SalesInquiry SoT via ``convert_sales_inquiry_mapping``.

    Transport Lead id remains the Sales HTTP facade key; domain write path is
    Convert Mapping (review gate + Review SoT + immutable mapping + lineage).
    """
    await run_product_convert_via_mapping(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        application_id=application_id,
        current_user=current_user,
        missing_detail="Application not found",
    )
    return await _reload_sales(db, tenant_id, own_company_id, application_id)


async def patch_recruitment_stage(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
    payload: ApplicationStagePatch,
    current_user: UserCtx,
) -> ApplicationOut:
    from backend.app.modules.leads.router import update_lead_stage_endpoint

    stage_payload = LeadStageUpdate(
        stage=payload.stage,
        lost_reason_code=payload.lost_reason_code,
        lost_reason_note=payload.lost_reason_note,
    )
    await update_lead_stage_endpoint(
        application_id,
        stage_payload,
        db_tenant=(db, UUID(tenant_id)),
        current_user=current_user,
        _role="recruiter",
    )
    return await _reload_recruitment(db, tenant_id, application_id)


async def recruitment_intake_decision(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    application_id: str,
    payload: ApplicationIntakeDecisionIn,
    current_user: UserCtx,
) -> ApplicationOut:
    actor_id = str(current_user.sub or "").strip() or None
    try:
        await service.apply_lead_intake_decision(
            db,
            tenant_id=tenant_id,
            lead_id=application_id,
            decision=str(payload.decision),
            actor_sub=actor_id,
            reason_code=str(payload.reason_code).strip() if payload.reason_code else None,
            note=payload.note,
            funnel_id=str(payload.funnel_id) if payload.funnel_id else None,
        )
    except service.LeadProcessingError as exc:
        raise service.lead_processing_error_as_http(exc) from exc
    return await _reload_recruitment(db, tenant_id, application_id)


async def recruitment_confirm_vacancy(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
    payload: ApplicationVacancyConfirmIn,
    current_user: UserCtx,
) -> ApplicationOut:
    actor_id = str(current_user.sub or "").strip() or None
    try:
        await service.confirm_lead_vacancy(
            db,
            tenant_id=tenant_id,
            lead_id=application_id,
            vacancy_id=str(payload.vacancy_id),
            actor_sub=actor_id,
        )
    except service.LeadProcessingError as exc:
        raise service.lead_processing_error_as_http(exc) from exc
    return await _reload_recruitment(db, tenant_id, application_id)


async def recruitment_process_application(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    application_id: str,
    current_user: UserCtx,
) -> ApplicationProcessResult:
    """Create a candidate from Отклики after vacancy binding.

    Explicit operator action must not re-fail on Meta acquisition routing
    (``no_intake_context``): vacancy was already confirmed in the UI / prepare step.
    """
    await _prepare_recruitment_application_for_process(
        db,
        tenant_id=tenant_id,
        application_id=application_id,
        current_user=current_user,
    )

    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    lead_src = str(getattr(lead, "source", "") or "").strip().lower()
    if lead_src not in {"meta", "csv_import"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "LEAD_SOURCE_INTAKE_DECISION_UNSUPPORTED"},
        )
    if not getattr(lead, "payload", None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INTAKE_ROUTING_INCOMPLETE", "message": "Lead payload is missing"},
        )

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
            tenant_id=tenant_id,
            payload=lead.payload,
            own_company_id=own_company_id or None,
            source=lead_src,
            force_existing=force_existing,
            external_id_hint=(str(lead.external_id).strip() if getattr(lead, "external_id", None) else None),
            prior_normalized=prior_norm,
            # Operator already bound/confirmed vacancy — skip acquisition flight matrix.
            force_candidate_conversion=True,
            stored_db_vacancy_id=(str(lead.vacancy_id).strip() if getattr(lead, "vacancy_id", None) else None)
            or None,
            stored_db_ad_id=getattr(lead, "ad_id", None),
            stored_lead_id=str(lead.id),
        )
    except service.LeadProcessingError as exc:
        raise service.lead_processing_error_as_http(exc) from exc

    await db.commit()
    app = await _reload_recruitment(db, tenant_id, application_id)
    candidate_id = str(result.candidate_id) if getattr(result, "candidate_id", None) else None
    return ApplicationProcessResult(application=app, candidate_id=candidate_id, message=getattr(result, "error", None))


async def recruitment_follow_up(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
    payload: ApplicationFollowUpIn,
    current_user: UserCtx,
) -> ApplicationOut:
    from backend.app.services import reminder_tasks

    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    due_raw = (payload.due_at or "").strip()
    if due_raw:
        try:
            due_at = datetime.fromisoformat(due_raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid due_at") from exc
    else:
        due_at = datetime.now(timezone.utc) + timedelta(days=1)

    actor_id = str(current_user.sub or "").strip() or None
    await reminder_tasks.create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id or tenant_id,
        payload={
            "title": payload.title.strip(),
            "description": payload.note,
            "type": "follow_up",
            "entity_type": "lead",
            "entity_id": application_id,
            "due_at": due_at,
            "source": "recruitment_application",
        },
    )
    await db.flush()
    return await _reload_recruitment(db, tenant_id, application_id)


async def recruitment_assign(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
    payload: ApplicationAssignIn,
    current_user: UserCtx,
) -> ApplicationOut:
    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    norm = dict(getattr(lead, "normalized", None) or {})
    meta = dict(norm.get("meta") or {})
    meta["assigned_manager_id"] = payload.assignee_id.strip()
    norm["meta"] = meta
    lead.normalized = norm
    await db.flush()
    return await _reload_recruitment(db, tenant_id, application_id)


async def _recruitment_lead_or_404(db: AsyncSession, tenant_id: str, application_id: str) -> Lead:
    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if not lead or (lead.lead_type == "client" and lead.lead_target_type == "client_lead"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return lead


async def recruitment_add_comment(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
    payload: ApplicationCommentIn,
    current_user: UserCtx,
) -> ApplicationOut:
    lead = await _recruitment_lead_or_404(db, tenant_id, application_id)
    note = str(payload.note or "").strip()
    if not note:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="note is required")
    norm = dict(getattr(lead, "normalized", None) or {})
    comments = list(norm.get("application_comments_v1") or [])
    comments.append(
        {
            "id": str(uuid4()),
            "text": note,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "author_id": str(current_user.sub or "").strip() or None,
            "author_name": str(current_user.email or "").strip() or None,
        }
    )
    norm["application_comments_v1"] = comments
    lead.normalized = norm
    flag_modified(lead, "normalized")
    await db.flush()
    return await _reload_recruitment(db, tenant_id, application_id)
