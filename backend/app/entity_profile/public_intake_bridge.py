"""Public intake → Lead intake record bridge (P4/P5C)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.decision_layer import DecisionInput, DecisionResult, stamp_decision_blocks
from backend.app.models import Candidate, Lead
from backend.app.modules.leads import crud


async def ensure_public_intake_lead_record(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Optional[Candidate] = None,
    lead: Optional[Lead] = None,
    intake_state: dict[str, Any],
    envelope_dict: dict[str, Any],
    decision_input: DecisionInput,
    decision: DecisionResult,
) -> Lead:
    """Create or update Lead as intake record for public application submit."""
    if lead is None and candidate is None:
        raise ValueError("lead or candidate is required")
    if lead is None:
        assert candidate is not None
        external_id = f"public_intake:{candidate.id}"
    else:
        external_id = str(getattr(lead, "external_id", None) or "").strip() or f"public_intake:{lead.id}"

    normalized = dict(intake_state or {})
    normalized["ingest_envelope_v1"] = dict(envelope_dict or {})
    stamp_decision_blocks(normalized, decision_input, decision)

    own_company_id = str(getattr(lead or candidate, "own_company_id", None) or "").strip() or None
    company_id = str(getattr(lead or candidate, "company_id", None) or "").strip() or None
    vacancy_id = str(getattr(lead or candidate, "vacancy_id", None) or "").strip() or None
    if not company_id and vacancy_id:
        from backend.app.models.vacancy import Vacancy

        vacancy = await db.get(Vacancy, vacancy_id)
        if vacancy is not None:
            company_id = str(getattr(vacancy, "company_id", None) or "").strip() or None
            if not own_company_id:
                own_company_id = str(getattr(vacancy, "own_company_id", None) or "").strip() or None
    if not company_id:
        company_id = await crud.get_default_company_id(db, str(tenant_id))
    if not company_id:
        raise ValueError("company_id is required for public intake lead record")

    existing = await crud.get_lead_by_external_id(
        db,
        tenant_id=str(tenant_id),
        source="public_intake",
        external_id=external_id,
    )
    candidate_id = str(getattr(candidate, "id", None) or getattr(lead, "candidate_id", None) or "").strip() or None
    if existing is not None:
        await crud.update_lead(
            db,
            existing,
            status=str(getattr(lead, "status", None) or "processed"),
            candidate_id=candidate_id,
            vacancy_id=vacancy_id or existing.vacancy_id,
            normalized=normalized,
            error=None,
        )
        return existing

    if lead is not None and str(getattr(lead, "id", "")):
        await crud.update_lead(
            db,
            lead,
            status=str(getattr(lead, "status", None) or "processed"),
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
            normalized=normalized,
            error=None,
        )
        return lead

    assert candidate is not None
    lead_row = await crud.create_lead(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        company_id=company_id,
        vacancy_id=vacancy_id,
        payload={"candidate_id": str(candidate.id), "source": "public_intake"},
        normalized=normalized,
        source="public_intake",
        external_id=external_id,
        lead_type="candidate",
        lead_target_type="candidate",
    )
    await crud.update_lead(
        db,
        lead_row,
        status="processed",
        candidate_id=str(candidate.id),
        vacancy_id=vacancy_id,
        normalized=normalized,
        error=None,
    )
    return lead_row
