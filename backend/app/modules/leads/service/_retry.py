"""Meta-Leads retry orchestration.

Extracted from ``backend/app/modules/leads/service/__init__.py`` (Phase 1 #3
step 7/N): the ``retry_meta_leads`` job that scans recent failures and
retries them through the Meta normalize pipeline.

Re-exported via ``service/__init__.py`` so callers
(scheduler / arq worker / API) keep using ``service.retry_meta_leads``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.leads import crud, pipeline

from ._bulk import process_meta_lead
from ._helpers import LeadProcessingError, MetaLeadRetryOutcome, _load_settings


async def retry_meta_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str] = None,
    lead_ids: Optional[List[str]] = None,
    statuses: Optional[List[str]] = None,
    limit: Optional[int] = None,
    refresh_graph: bool = True,
) -> List[MetaLeadRetryOutcome]:
    settings_row = await _load_settings(db, tenant_id)
    min_hours = getattr(settings_row, "reroute_after_hours", None)
    now_marker = datetime.now(timezone.utc)
    targets = await crud.list_leads_for_retry(
        db,
        tenant_id=tenant_id,
        statuses=statuses,
        lead_ids=lead_ids,
        limit=limit,
    )
    if not targets:
        return []

    outcomes: List[MetaLeadRetryOutcome] = []
    import json

    existing_map = {
        lead.external_id: lead
        for lead in targets
        if getattr(lead, "external_id", None)
    }

    for lead in targets:
        if isinstance(min_hours, int) and min_hours > 0 and lead.last_routed_at:
            # Rate-limit retries to avoid thrashing integrations.
            delta = now_marker - (lead.last_routed_at if lead.last_routed_at.tzinfo else lead.last_routed_at.replace(tzinfo=timezone.utc))
            if delta.total_seconds() < min_hours * 3600:
                outcomes.append(
                    MetaLeadRetryOutcome(
                        lead_id=lead.id,
                        status_before=lead.status,
                        status_after=lead.status,
                        candidate_id=lead.candidate_id,
                        error_before=lead.error,
                        error_after=lead.error,
                        processed=False,
                        message=f"Retry skipped: reroute_after_hours={min_hours}",
                    )
                )
                continue
        status_before = lead.status
        error_before = lead.error
        payload_raw = lead.payload
        if not payload_raw:
            outcomes.append(
                MetaLeadRetryOutcome(
                    lead_id=lead.id,
                    status_before=status_before,
                    status_after=status_before,
                    candidate_id=lead.candidate_id,
                    error_before=error_before,
                    error_after=error_before,
                    processed=False,
                    message="Lead payload is empty",
                )
            )
            continue

        if isinstance(payload_raw, str):
            try:
                payload_dict = json.loads(payload_raw)
            except json.JSONDecodeError as exc:
                outcomes.append(
                    MetaLeadRetryOutcome(
                        lead_id=lead.id,
                        status_before=status_before,
                        status_after=status_before,
                        candidate_id=lead.candidate_id,
                        error_before=error_before,
                        error_after=error_before,
                        processed=False,
                        message=f"Stored payload decode error: {exc}",
                    )
                )
                continue
        else:
            payload_dict = dict(payload_raw)

        try:
            hydrated = await pipeline.hydrate_webhook_payload(
                db,
                tenant_id,
                payload_dict,
                existing_leads=existing_map,
                refresh_graph=refresh_graph,
            )
        except ValueError as exc:
            outcomes.append(
                MetaLeadRetryOutcome(
                    lead_id=lead.id,
                    status_before=status_before,
                    status_after=status_before,
                    candidate_id=lead.candidate_id,
                    error_before=error_before,
                    error_after=error_before,
                    processed=False,
                    message=str(exc),
                )
            )
            continue

        try:
            result = await process_meta_lead(
                db=db,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                payload=hydrated,
            )
            status_after = result.status
            candidate_id = result.candidate_id
            error_after = result.error
            processed_flag = status_after in {"processed", "duplicated"}
        except LeadProcessingError as exc:
            status_after = status_before
            candidate_id = lead.candidate_id
            error_after = error_before
            processed_flag = False
            outcomes.append(
                MetaLeadRetryOutcome(
                    lead_id=lead.id,
                    status_before=status_before,
                    status_after=status_after,
                    candidate_id=candidate_id,
                    error_before=error_before,
                    error_after=error_after,
                    processed=processed_flag,
                    message=exc.message,
                )
            )
            continue

        try:
            await db.refresh(lead)
            status_after = lead.status
            candidate_id = lead.candidate_id
            error_after = lead.error
        except Exception:
            pass

        outcomes.append(
            MetaLeadRetryOutcome(
                lead_id=lead.id,
                status_before=status_before,
                status_after=status_after,
                candidate_id=candidate_id,
                error_before=error_before,
                error_after=error_after,
                processed=processed_flag,
                message=None,
            )
        )

    return outcomes
