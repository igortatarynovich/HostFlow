"""
ADR-014 Phase 2 — candidate **owner access** for the documents-db surface.

Loads ``CandidateDocsContext`` using the same tenant visibility + candidate repo path
as the HTTP router historically used. ``DocumentAccessResolver`` calls this module only;
handlers must not bypass the resolver to reach owner loading directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.services.tenant_visibility import TenantVisibility, get_tenant_visibility


@dataclass
class CandidateDocsContext:
    candidate: Candidate
    company_name: Optional[str]
    manager_raw: Optional[str]
    manager_name: Optional[str]
    vacancy_title: Optional[str]
    recruiter_id: Optional[str]
    recruiter_name: Optional[str]
    recruiter_short: Optional[str]
    owner_tenant_id: str
    allowed_tenant_ids: set[str]


def candidate_visible_for_tenant_documents(
    candidate: Candidate,
    tenant_id: str,
    visibility: Optional[TenantVisibility],
) -> bool:
    """Whether ``candidate`` is visible to ``tenant_id`` under shared-vacancy/company rules."""
    if str(getattr(candidate, "tenant_id", "") or "") == str(tenant_id):
        return True
    if not visibility:
        return False
    vacancy_id = getattr(candidate, "vacancy_id", None)
    company_id = getattr(candidate, "company_id", None)
    if vacancy_id and str(vacancy_id) in visibility.shared_vacancy_ids:
        return True
    if company_id and str(company_id) in visibility.shared_company_ids:
        return True
    return False


async def load_candidate_documents_owner_context(
    session: AsyncSession,
    tenant_id: str,
    candidate_id: UUID,
) -> CandidateDocsContext:
    """
    Owner-access leg for candidate-bound documents: tenant scope, visibility, client/agency.

    Raises ``HTTPException(404, "Candidate not found")`` only when the candidate is not
    accessible under owner rules (not due to workspace header alone).
    """
    visibility = get_tenant_visibility(session, tenant_id)
    from backend.app.api.v1.candidates import repo as candidate_repo
    from backend.app.services.handoff import is_client_tenant

    client_tenant = await is_client_tenant(session, tenant_id)
    row = await candidate_repo.get_candidate_with_labels(
        session,
        tenant_id,
        str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
    (
        candidate,
        company_name,
        manager_raw,
        manager_name,
        vacancy_title,
        recruiter_id,
        recruiter_name,
        recruiter_short,
    ) = row
    owner_tenant_id = str(getattr(candidate, "tenant_id", None) or tenant_id)
    allowed_tenant_ids: set[str] = {owner_tenant_id, tenant_id}
    if candidate_visible_for_tenant_documents(candidate, tenant_id, visibility):
        allowed_tenant_ids.add(owner_tenant_id)

    return CandidateDocsContext(
        candidate=candidate,
        company_name=company_name,
        manager_raw=manager_raw,
        manager_name=manager_name,
        vacancy_title=vacancy_title,
        recruiter_id=recruiter_id,
        recruiter_name=recruiter_name,
        recruiter_short=recruiter_short,
        owner_tenant_id=owner_tenant_id,
        allowed_tenant_ids=allowed_tenant_ids,
    )


__all__ = [
    "CandidateDocsContext",
    "candidate_visible_for_tenant_documents",
    "load_candidate_documents_owner_context",
]
