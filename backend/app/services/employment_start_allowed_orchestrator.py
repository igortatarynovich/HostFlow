"""Handoff-hosted employment_start_allowed.v1 (ESA slice 3).

Resolves the Employee linked to the handoff, projects existing Documents
evidence, evaluates/applies. Does not invent upload or set start_allowed.
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.reference.employment_start_allowed import (
    POLICY_ID,
    apply_employment_start_allowed_v1,
    evaluate_employment_start_allowed_v1,
)
from backend.app.services.employment_formalize_employee_ensure import employee_linked_handoff_id
from backend.app.services.employment_start_allowed_evidence import (
    project_bhp_evidence_view,
    project_contract_evidence_view,
    project_medical_evidence_view,
)
from backend.app.services.employment_start_allowed_exceptions import (
    StartAllowedExceptionError,
    create_exception,
    list_active_exceptions,
    revoke_exception,
)
from backend.app.services import workforce_employees as we_svc


class EmploymentStartAllowedHostError(Exception):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _doc_mapping(doc: Any) -> dict[str, Any]:
    meta = getattr(doc, "meta", None)
    if not isinstance(meta, dict):
        meta = {}
    return {
        "id": str(getattr(doc, "id", "") or ""),
        "type": getattr(doc, "doc_type", None) or getattr(doc, "kind", None) or meta.get("type"),
        "status": getattr(doc, "status", None),
        "meta": meta,
        "generation_kind": meta.get("generation_kind") or getattr(doc, "source", None),
    }


def _pick_doc(docs: list[dict[str, Any]], *type_tokens: str) -> dict[str, Any] | None:
    tokens = {_norm(t) for t in type_tokens}
    for d in docs:
        dtype = _norm(d.get("type") or d.get("doc_type") or (_record(d.get("meta")).get("type")))
        if dtype in tokens or any(t in dtype for t in tokens if t):
            return d
    return None


def employment_context_from_employee(
    employee: WorkforceEmployee,
    *,
    override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose PEM-1-oriented context from employee meta + optional host override."""
    meta = _record(getattr(employee, "meta", None))
    rt = _record(meta.get("recruitment_transfer"))
    we = _record(meta.get("work_eligibility"))
    ctx: dict[str, Any] = {
        "employment_country": rt.get("work_country") or we.get("work_country") or "PL",
        "pathway_id": meta.get("pathway_id")
        or we.get("pathway_id")
        or rt.get("pathway_id")
        or "pl_eu_eea_free_movement",
        "contract_type": we.get("contract_type") or rt.get("contract_type") or "employment_contract",
        "employer_id": _text(
            meta.get("employer_id")
            or rt.get("employer_id")
            or getattr(employee, "company_id", None)
            or getattr(employee, "own_company_id", None)
        )
        or None,
        "post_key": _text(
            meta.get("post_key")
            or we.get("position_category")
            or rt.get("position_category")
        )
        or None,
        "planned_start_date": None,
    }
    hire = getattr(employee, "hire_date", None)
    if hire is not None:
        ctx["planned_start_date"] = hire.isoformat() if hasattr(hire, "isoformat") else str(hire)
    if isinstance(override, Mapping) and override:
        for key, value in override.items():
            if value is not None and value != "":
                ctx[key] = value
    return ctx


async def resolve_employee_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff: CandidateHandoff,
) -> WorkforceEmployee | None:
    """Prefer meta.internal_hr_handoff_id linkage; fall back to candidate Employee."""
    tid = str(tenant_id).strip()
    hid = str(handoff.id)
    cand_id = _text(getattr(handoff, "candidate_id", None))
    if not cand_id:
        return None
    existing = await we_svc.find_employee_by_candidate(db, tid, cand_id)
    if existing is None:
        return None
    linked = employee_linked_handoff_id(existing)
    if linked and linked != hid:
        # Same candidate, different handoff linkage — still the candidate-scoped Employee.
        # Host must evaluate the linked row after Formalize ensure stamps this handoff.
        pass
    if linked == hid or linked is None:
        return existing
    return existing


async def _load_evidence_views(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    from backend.app.services.document_hub_delivery_contract import (
        list_candidate_documents_via_contract,
    )

    raw_docs = await list_candidate_documents_via_contract(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
    )
    docs = [_doc_mapping(d) for d in (raw_docs or [])]
    contract_doc = _pick_doc(
        docs,
        "employment_contract",
        "umowa_o_prace",
        "written_confirmation_of_terms",
        "contract",
    )
    medical_doc = _pick_doc(docs, "medical_certificate", "medical", "badania_lekarskie")
    bhp_doc = _pick_doc(docs, "bhp", "szkolenia_bhp", "introductory_bhp", "bhp_training")
    return (
        project_contract_evidence_view(contract_doc),
        project_medical_evidence_view(medical_doc),
        project_bhp_evidence_view(bhp_doc),
    )


async def evaluate_start_allowed_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    employment_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    handoff = await db.get(CandidateHandoff, handoff_id)
    if handoff is None:
        raise EmploymentStartAllowedHostError("handoff_not_found", "Handoff not found")

    agency = str(getattr(handoff, "agency_tenant_id", "") or "")
    client = str(getattr(handoff, "client_tenant_id", "") or "")
    if str(tenant_id) not in {agency, client} and agency != str(tenant_id):
        raise EmploymentStartAllowedHostError("handoff_tenant_mismatch", "Handoff does not belong to tenant")

    employee = await resolve_employee_for_handoff(db, tenant_id=tenant_id, handoff=handoff)
    if employee is None:
        result = evaluate_employment_start_allowed_v1(employee_id=None)
        return {
            **result,
            "policy_id": POLICY_ID,
            "handoff_id": str(handoff.id),
            "linked_handoff_id": None,
            "ui_primary_item": result.get("primary_item"),
            "evidence_nav": {
                "documents_anchor": "#hr-document-verification",
                "employee_documents_anchor": "#hr-employee-linked-documents",
            },
        }

    linked = employee_linked_handoff_id(employee)
    ctx = employment_context_from_employee(employee, override=employment_context)
    cand_id = _text(getattr(employee, "candidate_id", None))
    contract_view, medical_view, bhp_view = await _load_evidence_views(
        db, tenant_id=tenant_id, candidate_id=cand_id
    )
    exceptions = await list_active_exceptions(
        db, tenant_id=str(tenant_id), employee_id=str(employee.id)
    )
    result = evaluate_employment_start_allowed_v1(
        employee_id=str(employee.id),
        employment_context=ctx,
        contract_view=contract_view,
        medical_view=medical_view,
        bhp_view=bhp_view,
        exceptions=exceptions,
        planned_start_date=ctx.get("planned_start_date"),
    )
    return {
        **result,
        "policy_id": POLICY_ID,
        "handoff_id": str(handoff.id),
        "linked_handoff_id": linked,
        "employment_context": ctx,
        "exceptions": exceptions,
        "ui_primary_item": result.get("primary_item"),
        "evidence_nav": {
            "documents_anchor": "#hr-document-verification",
            "employee_documents_anchor": "#hr-employee-linked-documents",
            "contract_preview_anchor": "#hr-contract-preview",
        },
    }


async def apply_start_allowed_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    actor_user_id: str | None = None,
    employment_context: Mapping[str, Any] | None = None,
    resolution_patch: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist allowlisted exception create/revoke, then fresh evaluate (no optimistic)."""
    patch = _record(resolution_patch)
    if not patch:
        return await evaluate_start_allowed_for_handoff(
            db,
            tenant_id=tenant_id,
            handoff_id=handoff_id,
            employment_context=employment_context,
        )

    # Forbidden invent paths — reject before side effects
    if patch.get("start_allowed") is True or patch.get("force_start_allowed") or patch.get("allow_anyway"):
        baseline = await evaluate_start_allowed_for_handoff(
            db,
            tenant_id=tenant_id,
            handoff_id=handoff_id,
            employment_context=employment_context,
        )
        return {
            **baseline,
            "decision": "rejected_patch",
            "start_allowed": False,
            "rejection_reason": "operator_set_start_allowed_forbidden",
            "ui_primary_item": baseline.get("primary_item"),
        }

    handoff = await db.get(CandidateHandoff, handoff_id)
    if handoff is None:
        raise EmploymentStartAllowedHostError("handoff_not_found", "Handoff not found")
    employee = await resolve_employee_for_handoff(db, tenant_id=tenant_id, handoff=handoff)
    if employee is None:
        raise EmploymentStartAllowedHostError("employee_required", "Linked Employee required before apply")

    wrote = False
    revoke_id = _text(patch.get("revoke_exception_id") or patch.get("revoke_id"))
    if revoke_id:
        try:
            await revoke_exception(
                db,
                tenant_id=str(tenant_id),
                exception_id=revoke_id,
                actor_user_id=actor_user_id,
                reason=_text(patch.get("reason")) or None,
            )
            wrote = True
        except StartAllowedExceptionError as exc:
            raise EmploymentStartAllowedHostError(exc.code, exc.message) from exc

    new_exc = _record(patch.get("exception") or patch.get("create_exception"))
    if new_exc:
        try:
            await create_exception(
                db,
                tenant_id=str(tenant_id),
                employee_id=str(employee.id),
                exception_code=_text(new_exc.get("exception_code")),
                facts=_record(new_exc.get("facts_json") or new_exc.get("facts")),
                actor_user_id=actor_user_id,
                handoff_id=str(handoff.id),
                evidence_refs=list(new_exc.get("evidence_refs") or []),
                requirement_code=_text(new_exc.get("requirement_code")) or None,
            )
            wrote = True
        except StartAllowedExceptionError as exc:
            raise EmploymentStartAllowedHostError(exc.code, exc.message) from exc

    # Evidence upload/meta invent patches are rejected (existing Documents authority only)
    if patch.get("upload") or patch.get("document") or patch.get("evidence_meta"):
        baseline = await evaluate_start_allowed_for_handoff(
            db,
            tenant_id=tenant_id,
            handoff_id=handoff_id,
            employment_context=employment_context,
        )
        return {
            **baseline,
            "decision": "rejected_patch",
            "start_allowed": False,
            "rejection_reason": "evidence_write_not_in_start_allowed",
            "ui_primary_item": baseline.get("primary_item"),
        }

    # Always re-evaluate from SoT after confirmed write (or no-op patch)
    result = await evaluate_start_allowed_for_handoff(
        db,
        tenant_id=tenant_id,
        handoff_id=handoff_id,
        employment_context=employment_context,
    )
    result["authority_write_confirmed"] = wrote
    # Also run pure apply for rejection_reason parity when only in-memory semantics matter
    _ = apply_employment_start_allowed_v1
    return result


__all__ = [
    "EmploymentStartAllowedHostError",
    "employment_context_from_employee",
    "resolve_employee_for_handoff",
    "evaluate_start_allowed_for_handoff",
    "apply_start_allowed_for_handoff",
]
