"""Document Hub delivery façade — `documents.hub_adapter_v1`.

Candidate-centric adapter over `modules.documents`. This is **not** the
ADR-009 Document Link SoT. E2 binds public-contract / adapter ids onto this
façade; a later named E slice may replace the candidate-owned row with links.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.documents.crud import ensure_ruleset_seed, list_candidate_documents
from backend.app.modules.documents.crud import list_document_types as list_document_types_crud
from backend.app.modules.documents.owner_summary import compute_owner_summary
from backend.app.modules.documents.owner_summary import EQUIVALENT_SATISFACTION
from backend.app.modules.documents.pack_projection import project_document_packs_from_expected
from backend.app.modules.documents.reminder_candidate_projection import project_reminder_candidates_from_packs
from backend.app.modules.documents.reminder_work_queue_projection import project_reminder_work_queue
from backend.app.modules.documents.rules_engine import compute_candidate_checklist
from backend.app.modules.documents.router import _build_synthetic_documents
from backend.app.modules.documents.storage import get_uploads_root, sanitize_filename
from backend.app.services.document_catalog import DOCUMENT_TYPE_DEFAULTS

PUBLIC_CONTRACT_ID = "documents.public_contract.v1"
ADAPTER_ID = "documents.hub_adapter_v1"
PUBLIC_OPERATIONS = (
    "list",
    "resolve",
    "set_resolution",
    "owner_summary",
    "verification_status",
    "list_types",
)


async def list_candidate_documents_via_contract(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    status: str | None = None,
    type_filter: str | None = None,
    include_deleted: bool = False,
    limit: int | None = None,
    offset: int | None = None,
    active_own_company_id: str | None = None,
) -> list[Any]:
    """Document Hub delivery contract adapter for candidate document reads."""
    return await list_candidate_documents(
        db,
        tenant_id,
        candidate_id,
        status=status,
        type_filter=type_filter,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
        active_own_company_id=active_own_company_id,
    )


async def ensure_ruleset_seed_via_contract(
    db: AsyncSession,
    *,
    tenant_id: str,
    ruleset_payload: dict[str, Any],
    own_company_id: str | None = None,
) -> Any:
    """Document Hub delivery contract adapter for ruleset seed resolution."""
    return await ensure_ruleset_seed(
        db,
        tenant_id,
        ruleset_payload,
        own_company_id=own_company_id,
    )


def compute_owner_summary_via_contract(
    owner_context: dict[str, Any],
    ruleset_payload: dict[str, Any],
    docs_payload: list[dict[str, Any]],
) -> dict[str, Any]:
    """Document Hub delivery contract adapter for owner-summary projection."""
    return compute_owner_summary(owner_context, ruleset_payload, docs_payload)


def project_document_packs_via_contract(
    *,
    owner_context: dict[str, Any],
    ruleset_payload: dict[str, Any],
    docs_payload: list[dict[str, Any]],
    expected_documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Document Hub delivery contract adapter for pack gap projection."""
    return project_document_packs_from_expected(
        ctx=owner_context,
        ruleset=ruleset_payload,
        docs=docs_payload,
        expected_documents=expected_documents,
    )


def project_reminder_candidates_via_contract(
    packs_payload: list[dict[str, Any]],
    *,
    owner_type: str = "candidate",
) -> list[dict[str, Any]]:
    """Document Hub delivery contract adapter for reminder candidate projection."""
    normalized_owner = owner_type if owner_type in {"candidate", "employee"} else "candidate"
    return project_reminder_candidates_from_packs(packs_payload, owner_type=normalized_owner)  # type: ignore[arg-type]


def project_reminder_work_queue_via_contract(
    reminder_candidates: list[dict[str, Any]],
    *,
    owner_type: str,
    owner_id: str,
) -> list[dict[str, Any]]:
    """Document Hub delivery contract adapter for reminder work queue projection."""
    return project_reminder_work_queue(
        reminder_candidates,
        owner_type=owner_type,
        owner_id=owner_id,
    )


def list_canonical_document_type_codes_via_contract() -> set[str]:
    """Canonical document type codes exposed via delivery contract."""
    return set(DOCUMENT_TYPE_DEFAULTS.keys())


async def list_document_types_via_contract(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> Any:
    """Document Hub delivery contract adapter for document type catalog reads."""
    return await list_document_types_crud(db, tenant_id)


def compute_candidate_checklist_via_contract(
    owner_context: dict[str, Any],
    ruleset_payload: dict[str, Any],
) -> dict[str, Any]:
    """Document Hub delivery contract adapter for checklist computation."""
    return compute_candidate_checklist(owner_context, ruleset_payload)


def list_equivalent_satisfaction_map_via_contract() -> dict[str, list[str]]:
    """Document Hub delivery contract adapter for equivalent document-type map."""
    return dict(EQUIVALENT_SATISFACTION or {})


def build_synthetic_documents_via_contract(
    tenant_id: str,
    candidate_id: Any,
    checklist: dict[str, Any],
    existing_docs: list[dict[str, Any]],
) -> list[Any]:
    """Document Hub delivery contract adapter for synthetic checklist rows."""
    return _build_synthetic_documents(tenant_id, candidate_id, checklist, existing_docs)


def get_uploads_root_via_contract() -> str:
    """Document Hub delivery contract adapter for uploads root resolution."""
    return str(get_uploads_root())


def sanitize_filename_via_contract(filename: str) -> str:
    """Document Hub delivery contract adapter for filename sanitization."""
    return sanitize_filename(filename)


async def evaluate_document_hub_requirements_via_contract(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Any,
) -> dict[str, Any] | None:
    """Document Hub delivery contract adapter for Requirement Engine document requirements."""
    from backend.app.requirement_rules.document_hub_bridge import (
        evaluate_candidate_document_hub_requirements,
    )

    return await evaluate_candidate_document_hub_requirements(
        db,
        tenant_id=str(tenant_id).strip(),
        candidate=candidate,
    )


def merge_document_hub_requirements_into_summary_via_contract(
    summary: dict[str, Any],
    hub_section: dict[str, Any] | None,
) -> dict[str, Any]:
    """Document Hub delivery contract adapter for Requirement Engine summary overlay."""
    if not hub_section:
        return summary
    from backend.app.requirement_rules.document_hub_bridge import (
        merge_requirement_engine_into_owner_summary,
    )

    return merge_requirement_engine_into_owner_summary(summary, hub_section)
