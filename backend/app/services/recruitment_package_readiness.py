"""PR16 — recruitment package readiness aligned with HR dossier blocks."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.field_registry.requirement_evaluator import evaluate_field_requirements_for_candidate
from backend.app.services.hr_verified_field_catalog import (
    DATA_ONLY_VERIFICATION_KEYS,
    OPTIONAL_FILE_VERIFICATION_KEYS,
)
from backend.app.services.hr_verification_plan import CATALOG_TO_DOCUMENT_KEY, VERIFICATION_SLOT_DEFS
from backend.app.services.workforce_eligibility_delivery_contract import (
    WorkforceEligibilityContext,
    resolve_workforce_eligibility_via_contract,
)

_HANDOFF_REQUIRED_DATA_BLOCKS = frozenset({"Contacts & address"})
_HANDOFF_OPTIONAL_DOC_BLOCKS = frozenset(OPTIONAL_FILE_VERIFICATION_KEYS)
READY_FOR_HANDOFF_STAGE = "ready_for_handoff"


def _norm_doc(code: str) -> str:
    return str(code or "").strip().lower().replace("-", "_")


def _block_catalog_types(document_key: str) -> frozenset[str]:
    for slot in VERIFICATION_SLOT_DEFS:
        if slot.document_key == document_key:
            return slot.catalog_types
    return frozenset()


def _candidate_contacts(candidate: Candidate) -> dict[str, Any]:
    contacts = candidate._get_contacts() if hasattr(candidate, "_get_contacts") else {}
    return contacts if isinstance(contacts, dict) else {}


def _candidate_personal(candidate: Candidate) -> dict[str, Any]:
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    return personal if isinstance(personal, dict) else {}


def _candidate_extra(candidate: Candidate) -> dict[str, Any]:
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    return extra if isinstance(extra, dict) else {}


async def _missing_contact_fields(db: AsyncSession, tenant_id: str, candidate: Candidate) -> list[dict[str, str]]:
    """P4: contact completeness via Field Registry + PE field requirements."""
    result = await evaluate_field_requirements_for_candidate(
        db,
        tenant_id=str(tenant_id),
        candidate=candidate,
        context="transition",
        system_stage=READY_FOR_HANDOFF_STAGE,
    )
    return list(result.get("missing_fields") or [])


def _missing_contact_fields_legacy(candidate: Candidate) -> list[dict[str, str]]:
    contacts = _candidate_contacts(candidate)
    personal = _candidate_personal(candidate)
    extra = _candidate_extra(candidate)
    missing: list[dict[str, str]] = []

    phone = str(candidate.phone or contacts.get("phone") or personal.get("phone") or "").strip()
    if not phone:
        missing.append({"field_code": "phone", "label": "Phone"})

    email = str(candidate.email or contacts.get("email") or personal.get("email") or "").strip()
    if not email:
        missing.append({"field_code": "email", "label": "Email"})

    address_raw = personal.get("address") or extra.get("address") or getattr(candidate, "address", None)
    address_ok = False
    if isinstance(address_raw, str):
        address_ok = bool(address_raw.strip())
    elif isinstance(address_raw, dict):
        from backend.app.services.hr_profile_address import address_dict_complete

        address_ok = address_dict_complete(address_raw)
    if not address_ok:
        missing.append({"field_code": "address_street", "label": "Street"})

    return missing


def _block_status_from_docs(
    document_key: str,
    missing_doc_codes: set[str],
    pending_doc_codes: set[str],
) -> str:
    if document_key in DATA_ONLY_VERIFICATION_KEYS:
        return "data"
    types = {_norm_doc(t) for t in _block_catalog_types(document_key)}
    if not types:
        return "optional"
    if any(t in missing_doc_codes for t in types):
        return "missing"
    if any(t in pending_doc_codes for t in types):
        return "issue"
    return "ready"


async def evaluate_recruitment_package(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    relaxed_doc_types: Optional[set[str]] = None,
) -> dict[str, Any]:
    """Evaluate dossier-aligned package for recruitment handoff gate + UI."""
    from backend.app.requirement_rules.readiness_bridge import (
        build_requirement_engine_section,
        evaluate_candidate_readiness_requirements,
        map_requirement_evaluation_to_package_fragments,
    )

    cand = (
        await db.execute(
            select(Candidate).where(
                Candidate.id == str(candidate_id).strip(),
                Candidate.tenant_id == str(tenant_id).strip(),
            )
        )
    ).scalar_one_or_none()
    if not cand:
        return {"ready": False, "blocks": [], "missing_documents": [], "missing_data_fields": []}

    extra = _candidate_extra(cand)
    personal = _candidate_personal(cand)

    decision = await resolve_workforce_eligibility_via_contract(
        db,
        context=WorkforceEligibilityContext(
            tenant_id=str(tenant_id).strip(),
            candidate_id=str(candidate_id).strip(),
            citizenship=extra.get("citizenship") or personal.get("citizenship"),
            work_country=extra.get("work_country") or personal.get("work_country"),
            residence_status=extra.get("poland_stay_basis") or personal.get("residency_status"),
            position_category=extra.get("position_category") or extra.get("profession"),
            employment_type=extra.get("employment_type"),
            stage=str(getattr(cand, "stage", "") or "").strip().lower() or None,
            client_id=str(getattr(cand, "own_company_id", "") or "").strip() or None,
            vacancy_id=str(getattr(cand, "vacancy_id", "") or "").strip() or None,
        ),
    )

    relaxed = {_norm_doc(x) for x in (relaxed_doc_types or set())}
    missing_docs = {_norm_doc(x) for x in (decision.get("missing_documents") or []) if _norm_doc(x)} - relaxed
    pending_docs = {_norm_doc(x) for x in (decision.get("pending_verification_documents") or []) if _norm_doc(x)} - relaxed

    requirement_evaluation = await evaluate_candidate_readiness_requirements(
        db,
        tenant_id=str(tenant_id).strip(),
        candidate=cand,
    )
    requirement_engine: dict[str, Any] | None = None
    req_fragments: dict[str, Any] | None = None
    if requirement_evaluation is not None:
        requirement_engine = build_requirement_engine_section(requirement_evaluation)
        req_fragments = map_requirement_evaluation_to_package_fragments(requirement_evaluation)
        for doc_code in req_fragments.get("missing_documents") or []:
            norm = _norm_doc(doc_code)
            if norm:
                missing_docs.add(norm)
        missing_docs -= relaxed

    seen_keys: set[str] = set()
    blocks: list[dict[str, Any]] = []
    missing_data_fields: list[dict[str, str]] = []

    for slot in VERIFICATION_SLOT_DEFS:
        key = slot.document_key
        if key in seen_keys:
            continue
        seen_keys.add(key)

        if key in DATA_ONLY_VERIFICATION_KEYS:
            if key == "Contacts & address":
                if req_fragments is not None:
                    missing_fields = list(req_fragments.get("missing_data_fields") or [])
                    legacy_address = [
                        row
                        for row in _missing_contact_fields_legacy(cand)
                        if row.get("field_code") == "address"
                    ]
                    seen_field_codes = {row.get("field_code") for row in missing_fields}
                    missing_fields.extend(
                        row for row in legacy_address if row.get("field_code") not in seen_field_codes
                    )
                else:
                    missing_fields = await _missing_contact_fields(db, tenant_id, cand)
            else:
                missing_fields = []
            status = "ready" if not missing_fields else "data"
            if missing_fields:
                missing_data_fields.extend(missing_fields)
            blocks.append(
                {
                    "document_key": key,
                    "label": key,
                    "status": status,
                    "block_kind": "data_only",
                    "missing_fields": missing_fields,
                    "missing_doc_types": [],
                }
            )
            continue

        status = _block_status_from_docs(key, missing_docs, pending_docs)
        block_missing_types = sorted(
            t for t in {_norm_doc(x) for x in _block_catalog_types(key)} if t in missing_docs
        )
        blocks.append(
            {
                "document_key": key,
                "label": key,
                "status": status,
                "block_kind": "optional_file" if key in _HANDOFF_OPTIONAL_DOC_BLOCKS else "document",
                "missing_fields": [],
                "missing_doc_types": block_missing_types,
            }
        )

    blocking_blocks: list[str] = []
    for b in blocks:
        key = str(b["document_key"])
        st = str(b["status"])
        if key in _HANDOFF_REQUIRED_DATA_BLOCKS and st != "ready":
            blocking_blocks.append(key)
        elif key in _HANDOFF_OPTIONAL_DOC_BLOCKS:
            continue
        elif key in DATA_ONLY_VERIFICATION_KEYS:
            continue
        elif st in ("missing", "issue"):
            blocking_blocks.append(key)

    ops = dict(decision.get("allowed_operations") or {})
    handoff_allowed = bool(ops.get("handoff_to_hr", ops.get("hr_handoff", True)))
    ready = handoff_allowed and not blocking_blocks and not missing_data_fields

    result: dict[str, Any] = {
        "ready": ready,
        "handoff_allowed": handoff_allowed,
        "blocking_blocks": blocking_blocks,
        "blocks": blocks,
        "missing_documents": sorted(missing_docs),
        "pending_verification_documents": sorted(pending_docs),
        "missing_data_fields": missing_data_fields,
        "eligibility_status": decision.get("eligibility_status"),
        "readiness_profiles": decision.get("readiness_profiles") or {},
    }
    if requirement_engine is not None:
        result["requirement_engine"] = requirement_engine
    return result


async def assert_recruitment_package_ready_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    relaxed_doc_types: Optional[set[str]] = None,
) -> dict[str, Any]:
    """Return error detail dict when not ready; empty dict when OK."""
    from backend.app.process_engine.constants import RECRUITMENT_MODULE
    from backend.app.process_engine.evaluator_adapter import TransitionEvaluatorAdapter

    _ = relaxed_doc_types  # overrides resolved inside transfer policy (via adapter)
    err = await TransitionEvaluatorAdapter.assert_transition_allowed(
        db,
        tenant_id=tenant_id,
        module=RECRUITMENT_MODULE,
        entity_type="candidate",
        entity_id=candidate_id,
        target_system_stage=READY_FOR_HANDOFF_STAGE,
        require_destination=True,
    )
    if not err:
        return {}

    missing_types = sorted(set(err.get("missing_types") or []))
    return {
        "code": "handoff_docs_incomplete",
        "message": "Recruitment package is incomplete for handoff",
        "missing_types": missing_types,
        "missing_data_fields": err.get("missing_data_fields") or [],
        "blocking_blocks": err.get("blocking_blocks") or [],
        "required_confirmations": err.get("required_confirmations") or [],
        "package_blocks": err.get("package_blocks") or [],
        "eligibility_status": err.get("eligibility_status"),
        "blocking_reasons": err.get("blocking_reasons") or [],
        "destinations_allowed": err.get("destinations_allowed") or [],
        "transfer_policy": {
            "policy_version": err.get("policy_version"),
            "source_layers": err.get("source_layers") or [],
        },
    }
