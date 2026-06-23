"""P2A — Readiness consumer bridge to Requirement Rules Engine."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.vacancy_bridge import resolve_entity_profile_hints_from_vacancy
from backend.app.models.candidate import Candidate
from backend.app.modules.documents.crud import list_candidate_documents
from backend.app.requirement_rules.constants import REQUIREMENT_EVALUATION_V1
from backend.app.requirement_rules.registry import RequirementRulesNotFoundError

READINESS_CONTEXT = "readiness"

_QUALIFIED_TO_LEGACY_FIELD: dict[str, tuple[str, str]] = {
    "recruitment.candidate.first_name": ("first_name", "First name"),
    "recruitment.candidate.last_name": ("last_name", "Last name"),
    "recruitment.candidate.contacts.phone": ("phone", "Phone"),
    "recruitment.candidate.contacts.email": ("email", "Email"),
}


def _candidate_contacts(candidate: Candidate) -> dict[str, Any]:
    contacts = candidate._get_contacts() if hasattr(candidate, "_get_contacts") else {}
    return contacts if isinstance(contacts, dict) else {}


def _candidate_personal(candidate: Candidate) -> dict[str, Any]:
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    return personal if isinstance(personal, dict) else {}


def _candidate_extra(candidate: Candidate) -> dict[str, Any]:
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    return extra if isinstance(extra, dict) else {}


def _pick_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _norm_doc(code: str) -> str:
    return str(code or "").strip().lower().replace("-", "_")


def build_normalized_payload_from_candidate(candidate: Candidate) -> dict[str, Any]:
    """Build evaluation input payload from candidate fields."""
    contacts = _candidate_contacts(candidate)
    personal = _candidate_personal(candidate)
    extra = _candidate_extra(candidate)

    payload: dict[str, Any] = {}

    first_name = _pick_text(getattr(candidate, "first_name", ""), contacts.get("first_name"))
    if first_name:
        payload["recruitment.candidate.first_name"] = first_name
        payload["first_name"] = first_name

    last_name = _pick_text(getattr(candidate, "last_name", ""), contacts.get("last_name"))
    if last_name:
        payload["recruitment.candidate.last_name"] = last_name
        payload["last_name"] = last_name

    phone = _pick_text(getattr(candidate, "phone", ""), contacts.get("phone"), personal.get("phone"))
    if phone:
        payload["recruitment.candidate.contacts.phone"] = phone
        payload["phone"] = phone

    email = _pick_text(getattr(candidate, "email", ""), contacts.get("email"), personal.get("email"))
    if email:
        payload["recruitment.candidate.contacts.email"] = email
        payload["email"] = email

    citizenship = _pick_text(extra.get("citizenship"), personal.get("citizenship"))
    if citizenship:
        payload["platform.identity.citizenship"] = citizenship
        payload["citizenship"] = citizenship

    birth_date = _pick_text(extra.get("birth_date"), personal.get("birth_date"))
    if birth_date:
        payload["platform.identity.birth_date"] = birth_date
        payload["birth_date"] = birth_date

    years_ce = _pick_text(extra.get("experience_eu_years"), extra.get("years_ce"), personal.get("years_ce"))
    if years_ce:
        payload["recruitment.candidate.experience.years_ce"] = years_ce
        payload["experience_eu_years"] = years_ce

    return payload


def _document_row_to_snapshot(doc: Any) -> dict[str, Any]:
    status_raw = getattr(doc, "status", None)
    status = status_raw.value if hasattr(status_raw, "value") else str(status_raw or "")
    meta = getattr(doc, "meta", None) or {}
    if not isinstance(meta, dict):
        meta = {}
    files = getattr(doc, "files", None) or []
    doc_type = _norm_doc(getattr(doc, "doc_type", "") or "")
    return {
        "document_type_code": doc_type,
        "type": doc_type,
        "status": status,
        "readiness_state": meta.get("readiness_state"),
        "verified_at": meta.get("verified_at"),
        "has_files": bool(files),
    }


async def load_candidate_documents_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> list[dict[str, Any]]:
    rows = await list_candidate_documents(
        db,
        str(tenant_id).strip(),
        str(candidate_id).strip(),
        include_deleted=False,
    )
    return [_document_row_to_snapshot(row) for row in rows]


async def resolve_entity_profile_code_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Optional[str]:
    """Resolve entity_profile_code via vacancy → candidate_profile → registry."""
    vacancy_id = str(getattr(candidate, "vacancy_id", "") or "").strip() or None
    entity_code, _, _ = await resolve_entity_profile_hints_from_vacancy(
        db,
        tenant_id=str(tenant_id).strip(),
        vacancy_id=vacancy_id,
    )
    return entity_code


def _qualified_code_to_missing_field(qualified_code: str) -> dict[str, str]:
    code = str(qualified_code or "").strip()
    field_code, label = _QUALIFIED_TO_LEGACY_FIELD.get(
        code,
        (code.split(".")[-1] if code else "unknown", code or "Field"),
    )
    row: dict[str, str] = {"field_code": field_code, "label": label}
    if code:
        row["qualified_code"] = code
    return row


def map_requirement_evaluation_to_package_fragments(
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Map requirement_evaluation_v1 to recruitment-package / transfer-policy fragments."""
    blockers = list(evaluation.get("blockers") or [])
    warnings = list(evaluation.get("warnings") or [])

    missing_documents = sorted(
        {
            _norm_doc(row.get("document_type_code") or "")
            for row in blockers
            if row.get("document_type_code")
        }
        - {""}
    )

    missing_data_fields: list[dict[str, str]] = []
    seen_fields: set[str] = set()
    for row in blockers:
        qualified = str(row.get("qualified_code") or "").strip()
        if not qualified:
            continue
        mapped = _qualified_code_to_missing_field(qualified)
        if mapped["field_code"] in seen_fields:
            continue
        seen_fields.add(mapped["field_code"])
        missing_data_fields.append(mapped)

    blocking_reasons: list[dict[str, Any]] = []
    for row in blockers:
        doc_code = str(row.get("document_type_code") or "").strip()
        qualified = str(row.get("qualified_code") or "").strip()
        if doc_code:
            blocking_reasons.append(
                {
                    "code": str(row.get("code") or "missing_required_document"),
                    "message": str(row.get("message") or f"Required document missing: {doc_code}"),
                    "source_layer": "requirement_engine",
                    "document_type_code": _norm_doc(doc_code),
                }
            )
        elif qualified:
            mapped = _qualified_code_to_missing_field(qualified)
            blocking_reasons.append(
                {
                    "code": str(row.get("code") or "missing_data_field"),
                    "message": str(row.get("message") or f"Required field missing: {qualified}"),
                    "source_layer": "requirement_engine",
                    "field_code": mapped["field_code"],
                    "qualified_code": qualified,
                    "label": mapped["label"],
                }
            )

    requirement_warnings: list[dict[str, Any]] = []
    for row in warnings:
        doc_code = str(row.get("document_type_code") or "").strip()
        qualified = str(row.get("qualified_code") or "").strip()
        requirement_warnings.append(
            {
                "code": str(row.get("code") or "requirement_warning"),
                "message": str(row.get("message") or "Requirement warning"),
                "source_layer": "requirement_engine",
                "document_type_code": _norm_doc(doc_code) if doc_code else None,
                "qualified_code": qualified or None,
                "severity": "warning",
            }
        )

    return {
        "missing_documents": missing_documents,
        "missing_data_fields": missing_data_fields,
        "blocking_reasons": blocking_reasons,
        "warnings": requirement_warnings,
    }


def build_requirement_engine_section(evaluation: dict[str, Any]) -> dict[str, Any]:
    """Embed requirement engine evaluation on recruitment-package response."""
    return {
        "applied": True,
        "entity_profile_code": evaluation.get("entity_profile_code"),
        "evaluation_version": evaluation.get("evaluation_version") or REQUIREMENT_EVALUATION_V1,
        "satisfied": bool(evaluation.get("satisfied")),
        "blockers": list(evaluation.get("blockers") or []),
        "warnings": list(evaluation.get("warnings") or []),
        "required_fields": list(evaluation.get("required_fields") or []),
        "required_documents": list(evaluation.get("required_documents") or []),
        "rule_sources_applied": list(evaluation.get("rule_sources_applied") or []),
        "context": evaluation.get("context") or READINESS_CONTEXT,
    }


async def evaluate_candidate_requirements(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    context: str,
) -> Optional[dict[str, Any]]:
    """Evaluate requirements via Requirement Engine; None → legacy fallback."""
    entity_profile_code = await resolve_entity_profile_code_for_candidate(
        db,
        tenant_id=str(tenant_id).strip(),
        candidate=candidate,
    )
    if not entity_profile_code:
        return None

    from backend.app.requirement_rules.facade import evaluate_entity_requirements

    try:
        normalized_payload = build_normalized_payload_from_candidate(candidate)
        documents = await load_candidate_documents_snapshot(
            db,
            tenant_id=str(tenant_id).strip(),
            candidate_id=str(candidate.id),
        )
        return await evaluate_entity_requirements(
            db,
            tenant_id=str(tenant_id).strip(),
            entity_profile_code=entity_profile_code,
            context=str(context or READINESS_CONTEXT).strip().lower(),
            normalized_payload=normalized_payload,
            documents=documents,
            entity_type="candidate",
            entity_id=str(candidate.id),
        )
    except RequirementRulesNotFoundError:
        return None


async def evaluate_candidate_readiness_requirements(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Optional[dict[str, Any]]:
    """Evaluate readiness requirements via Requirement Engine; None → legacy fallback."""
    return await evaluate_candidate_requirements(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
        context=READINESS_CONTEXT,
    )
