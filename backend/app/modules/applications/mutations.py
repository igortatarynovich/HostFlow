"""Delegate intake mutations to leads service; return Application read models."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx
from backend.app.models import Lead
from backend.app.modules.applications.mappers import lead_to_recruitment_application, lead_to_sales_inquiry
from backend.app.modules.applications.schemas import (
    ApplicationAssignIn,
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

    if block == "VACANCY_NOT_CONFIRMED":
        vac_id = str(getattr(lead, "vacancy_id", "") or "").strip()
        if vac_id:
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
    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if not lead or lead.lead_type != "client" or lead.lead_target_type != "client_lead":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return lead_to_sales_inquiry(lead)


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
    return await _reload_sales(db, tenant_id, own_company_id, application_id)


async def convert_sales_inquiry(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    application_id: str,
    current_user: UserCtx,
) -> ApplicationOut:
    from backend.app.modules.leads.router import convert_client_lead_to_client_endpoint

    await convert_client_lead_to_client_endpoint(
        application_id,
        db_tenant=(db, UUID(tenant_id)),
        current_user=current_user,
        own_company_id=own_company_id,
        _role="manager",
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
    from backend.app.modules.leads.router import process_lead_endpoint

    await _prepare_recruitment_application_for_process(
        db,
        tenant_id=tenant_id,
        application_id=application_id,
        current_user=current_user,
    )

    result = await process_lead_endpoint(
        application_id,
        db_tenant=(db, UUID(tenant_id)),
        current_user=current_user,
        own_company_id=own_company_id,
        _role="recruiter",
    )
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
