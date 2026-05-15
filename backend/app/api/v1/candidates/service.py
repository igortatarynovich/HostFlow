"""
Service layer for Candidate operations.

This module encapsulates business logic for the Candidate domain:
- creating and updating candidates;
- applying business rules (status transitions, document dependencies, reminders);
- post-processing after DB operations (sync with documents, notifications);
- providing enriched data to the API layer.

All database access must go through candidates.repo to keep separation of concerns.
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid as _uuid
from types import SimpleNamespace
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_assignee_history import CandidateAssigneeHistory
from backend.app.models.candidate_stage_history import CandidateStageHistory
from backend.app.api.v1.candidates import repo
from backend.app.api.v1.candidates.acl import CandidateACL
from uuid import UUID
from sqlalchemy import select, update, insert, or_
from fastapi import HTTPException
from backend.app.constants.stages_adapter import DEFAULT_STAGE_CODE
from backend.app.constants.stages import LABELS as STAGE_LABELS, STATUS_REASON_CHOICES, STAGE_META
from backend.app.models import Vacancy
from backend.app.models.company import Company
from backend.app.models.user import User
from backend.app.models.mixins import now_utc as _now_utc
from backend.app.api.v1.candidates.helpers import (
    _ensure_langs,
    _normalize_stage_to_code,
    _validate_stage_transition,
    _dump_json_str,
    _as_dict_safe,
    _merge_dict,
    _generate_unique_short_id,
    _ensure_short_id,
)
from backend.app.services.pipeline_sync import sync_candidate_links
from backend.app.services.tenant_quota import ensure_active_records_quota
from backend.app.services.recruiter_assignment import (
    AssignmentDecision,
    assign_recruiter as assign_recruiter_service,
    record_candidate_reassignment,
)
from backend.app.services.audit import log_activity
from backend.app.services import events
from backend.app.services.events import EventAudience
from backend.app.services.automation_rules import run_rules as run_automation_rules
from backend.app.services.source_labels import normalize_candidate_source
from backend.app.services.rodo import send_rodo_email as _send_rodo_email
from backend.app.services.rodo import candidate_rodo_compliance_satisfied as _candidate_rodo_compliance_satisfied
from backend.app.services import candidate_telegram_notifications as candidate_tg_notifications
from backend.app.services.handoff import is_client_tenant as _is_client_tenant
from backend.app.services.recruitment_handoff_write_guard import (
    AgencyRecruitmentWriteBypass,
    agency_candidate_has_internal_hr_handoff_lane,
    agency_recruitment_lock_bulk_error,
    require_agency_recruitment_write_allowed,
)
from backend.app.services.candidate_hr_internal_lane_patch import (
    assert_hr_internal_lane_patch_keys_allowed,
)
from backend.app.services.candidate_lifecycle import (
    apply_candidate_deletion_cleanup,
    maybe_apply_candidate_operationally_terminal_cleanup,
)
from backend.app.api.v1.candidates.repo import _candidate_scope_clause
from backend.app.services.tenant_visibility import TenantVisibility
from backend.app.modules.documents import crud as documents_crud
from backend.app.modules.documents.rules_engine import compute_candidate_checklist
from backend.app.services.document_orders import missing_base_requirements
from backend.app.services.document_ruleset import load_default_ruleset
from backend.app.services.ruleset_versioning import normalize_ruleset_payload
from backend.app.services.candidate_doc_pipeline_guard import (
    enforce_pipeline_contact_attempt_forward_block,
    enforce_pipeline_doc_forward_block,
    enforce_pipeline_vacancy_forward_block,
)
from backend.app.services.candidate_risk_stage_gate import enforce_critical_risk_forward_stage_gate
from backend.app.services.hiring_pipeline_gates import resolve_hiring_pipeline_gates

_UNSET = object()


def _now_naive() -> datetime:
    """Return current UTC timestamp without tzinfo for legacy naive columns."""
    return _now_utc().replace(tzinfo=None)


# RODO must be sent before recruiter starts direct contact/screening workflow.
_RODO_CONTACT_START_STAGES = {"contacted", "no_answer"}
_READY_FOR_HANDOFF_STAGE = "ready_for_handoff"


async def _candidate_row_exists(db: AsyncSession, candidate_id: str) -> bool:
    """True if a candidate row is already persisted (not the pre-insert create path)."""
    row = await db.execute(select(Candidate.id).where(Candidate.id == candidate_id).limit(1))
    return row.scalar_one_or_none() is not None


async def _enforce_rodo_before_contact_stage(
    db: AsyncSession,
    *,
    candidate_id: str,
    target_stage_code: Optional[str],
) -> None:
    stage_code = str(target_stage_code or "").strip().lower()
    if stage_code not in _RODO_CONTACT_START_STAGES:
        return
    # Create path runs this before INSERT: there is no row and no RODO yet; auto-send runs after commit.
    if not await _candidate_row_exists(db, candidate_id):
        return
    if await _candidate_rodo_compliance_satisfied(db, candidate_id):
        return
    raise HTTPException(
        status_code=409,
        detail="RODO must be sent to candidate before moving to contact/screening stage",
    )


def _effective_vacancy_id_from_patch_payload(c: Candidate, payload: dict) -> Optional[str]:
    """Vacancy as seen when validating a stage change in PATCH (may come from payload or DB)."""
    if "vacancy_id" in payload:
        v = payload["vacancy_id"]
        if v is None:
            return None
        s = str(v).strip()
        return s or None
    return getattr(c, "vacancy_id", None)


def _candidate_owner_context_for_docs(
    *,
    candidate_id: str,
    extra: Dict[str, Any] | None,
    personal: Dict[str, Any] | None,
) -> Dict[str, Any]:
    extra_data = extra if isinstance(extra, dict) else {}
    personal_data = personal if isinstance(personal, dict) else {}
    docs_raw = extra_data.get("documents")
    docs_ctx = {
        key: bool(value)
        for key, value in (docs_raw.items() if isinstance(docs_raw, dict) else [])
        if isinstance(value, bool)
    }
    ctx: Dict[str, Any] = {
        "candidate_id": str(candidate_id),
        "citizenship": extra_data.get("citizenship") or personal_data.get("citizenship"),
        "residency_status": extra_data.get("poland_stay_basis") or personal_data.get("residency_status"),
        "has_adr": extra_data.get("has_adr"),
        "documents": docs_ctx,
    }
    return {k: v for k, v in ctx.items() if v is not None}


async def _enforce_docs_ready_for_handoff_stage(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    target_stage_code: Optional[str],
    extra: Dict[str, Any] | None = None,
    personal: Dict[str, Any] | None = None,
) -> None:
    stage_code = str(target_stage_code or "").strip().lower()
    if stage_code != _READY_FOR_HANDOFF_STAGE:
        return
    # Same as RODO: on create we run before INSERT — checklist/docs are empty by definition.
    if not await _candidate_row_exists(db, candidate_id):
        return

    owner_context = _candidate_owner_context_for_docs(
        candidate_id=candidate_id,
        extra=extra,
        personal=personal,
    )
    oc_row = await db.execute(
        select(Candidate.own_company_id).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
        ).limit(1)
    )
    oc = oc_row.scalar_one_or_none()
    own_company_id = str(oc).strip() if oc else None
    ruleset_version = await documents_crud.ensure_ruleset_seed(
        db,
        tenant_id,
        load_default_ruleset(),
        own_company_id=own_company_id,
    )
    ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
    checklist = compute_candidate_checklist(owner_context, ruleset_payload)
    existing_docs = await documents_crud.list_candidate_documents(
        db,
        tenant_id,
        candidate_id,
        active_own_company_id=own_company_id,
    )
    active_docs = [doc for doc in existing_docs if getattr(doc, "deleted_at", None) is None]
    missing = missing_base_requirements(checklist, active_docs)
    from backend.app.api.v1.candidates.pipeline_overrides_service import (
        approved_handoff_relaxed_types,
    )

    relaxed = await approved_handoff_relaxed_types(
        db, tenant_id=tenant_id, candidate_id=candidate_id
    )
    if relaxed:
        missing = [m for m in missing if m not in relaxed]
    if missing:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "handoff_docs_incomplete",
                "message": "Required documents checklist is incomplete for ready_for_handoff stage",
                "missing_types": missing,
            },
        )


async def _get_supervisor_id(db: AsyncSession, recruiter_id: Optional[str]) -> Optional[str]:
    if not recruiter_id:
        return None
    row = await db.execute(
        select(User.supervisor_id).where(
            User.id == recruiter_id,
            User.is_active.is_(True),
        )
    )
    supervisor_id = row.scalar_one_or_none()
    return supervisor_id if supervisor_id else None


def _candidate_matches_acl(
    acl: CandidateACL | None,
    *,
    manager: Optional[str],
    company: Optional[str],
    vacancy: Optional[str],
    recruiter_id: Optional[str] = None,
) -> bool:
    if acl is None or acl.unrestricted:
        return True

    manager_val = str(manager) if manager else None
    recruiter_val = str(recruiter_id) if recruiter_id else None
    company_val = str(company) if company else None
    vacancy_val = str(vacancy) if vacancy else None

    mids = acl.manager_ids
    if manager_val and manager_val in mids:
        return True
    if recruiter_val and recruiter_val in mids:
        return True
    if company_val and company_val in acl.company_ids:
        return True
    if vacancy_val and vacancy_val in acl.vacancy_ids:
        return True
    return False


def _make_stage_history(
    tenant_id: str,
    candidate_id: str,
    *,
    from_code: Optional[str],
    to_code: str,
    actor_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> CandidateStageHistory:
    return CandidateStageHistory(
        id=str(_uuid.uuid4()),
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        from_code=from_code,
        to_code=to_code,
        actor=actor_id,
        reason=reason,
        at=_now_utc(),
    )


async def create_candidate(
    db: AsyncSession,
    tenant_id: str,
    data: Dict[str, Any],
    *,
    actor_id: Optional[str] = None,
) -> Candidate:
    """Create a new candidate (tenant-scoped)."""
    return await create_candidate_full(db, tenant_id, data, actor_id=actor_id)

async def update_candidate(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    data: Dict[str, Any],
    *,
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    reason: Any = _UNSET,
    agency_recruitment_bypass: Optional[AgencyRecruitmentWriteBypass] = None,
) -> Optional[Candidate]:
    """Update candidate fields and apply domain rules (tenant-scoped)."""
    return await update_candidate_full(
        db,
        tenant_id,
        candidate_id,
        data,
        actor_id=actor_id,
        actor_role=actor_role,
        status_reason_override=reason,
        agency_recruitment_bypass=agency_recruitment_bypass,
    )

async def get_candidate(db: AsyncSession, tenant_id: str, candidate_id: str) -> Optional[Candidate]:
    """Retrieve candidate with linked info for detail view (tenant-scoped)."""
    row = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
            Candidate.deleted_at.is_(None),
        )
    )
    c = row.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return c

async def list_candidates(
    db: AsyncSession,
    tenant_id: str,
    filters: Dict[str, Any],
) -> List[Candidate]:
    """Return filtered list of candidates for list view (tenant-scoped)."""
    stmt = select(Candidate).where(
        Candidate.tenant_id == tenant_id,
        Candidate.deleted_at.is_(None),
    )
    # Basic ordering by created_at desc to match UI expectations
    res = await db.execute(stmt.order_by(Candidate.created_at.desc()))
    return list(res.scalars().all())

async def delete_candidate(db: AsyncSession, tenant_id: str, candidate_id: str) -> None:
    """Soft-delete candidate and related references (tenant-scoped)."""
    await delete_candidate_full(db, tenant_id, candidate_id)


async def create_candidate_full(
    db: AsyncSession,
    tenant_id: str,
    payload: Dict[str, Any],
    *,
    actor_id: Optional[str] = None,
    acl: CandidateACL | None = None,
    source_lead: Any = None,
) -> Candidate:
    payload = dict(payload or {})
    await ensure_active_records_quota(db, tenant_id)

    source_update_present = "source" in payload
    origin_update_present = "origin" in payload
    source_update_value: Optional[str] = None
    if source_update_present:
        raw_source = payload.pop("source")
        normalized_source = normalize_candidate_source(str(raw_source) if raw_source is not None else None)
        source_update_value = normalized_source[:64] if normalized_source else None

    origin_update_value = None
    if origin_update_present:
        raw_origin = payload.pop("origin")
        if raw_origin is None:
            origin_update_value = None
        elif isinstance(raw_origin, dict):
            origin_update_value = raw_origin
        else:
            origin_update_value = {"value": raw_origin}

    languages = _ensure_langs(payload.get("languages"))
    
    # Нормализация тегов: убираем пустые, делаем уникальными, сортируем
    tags_raw = payload.get("tags")
    tags: list[str] = []
    if tags_raw is not None:
        if isinstance(tags_raw, (list, tuple)):
            tags = sorted(list(set(str(x).strip() for x in tags_raw if str(x).strip())))
        elif isinstance(tags_raw, str):
            tags_parts = [p.strip() for p in tags_raw.replace(",", " ").split() if p.strip()]
            tags = sorted(list(set(tags_parts)))
    
    is_favorite = payload.get("is_favorite", False)

    source_val: Optional[str] = source_update_value

    origin_payload = payload.pop("origin", None)
    if origin_payload is not None and not isinstance(origin_payload, dict):
        origin_payload = {"value": origin_payload}

    cand_id = str(payload.get("id") or _uuid.uuid4())

    stage_input = payload.get("stage") or payload.get("status")
    if stage_input is None or str(stage_input).strip() == "":
        stage_code = DEFAULT_STAGE_CODE
    else:
        normalized = _normalize_stage_to_code(str(stage_input))
        if not normalized:
            raise HTTPException(status_code=422, detail=f"Unknown stage '{stage_input}'")
        stage_code = normalized

    # Для клиентских тенантов запрещаем устанавливать внутренние агентские стадии
    if await _is_client_tenant(db, tenant_id) and not _stage_visible_for_client(stage_code):
        raise HTTPException(
            status_code=403,
            detail=f"Stage '{stage_code}' is not allowed for client tenant",
        )

    _validate_stage_transition(None, stage_code)
    await _enforce_rodo_before_contact_stage(
        db,
        candidate_id=cand_id,
        target_stage_code=stage_code,
    )
    await _enforce_docs_ready_for_handoff_stage(
        db,
        tenant_id=tenant_id,
        candidate_id=cand_id,
        target_stage_code=stage_code,
        extra=_as_dict_safe(payload.get("extra")),
        personal=_as_dict_safe(payload.get("personal_data")),
    )
    status_reason_raw = payload.pop("status_reason", None)
    status_reason_codes = _normalize_status_reason_input(status_reason_raw)
    status_reason_values: list[str] = []
    if stage_code in _REASON_REQUIRED_STAGES:
        status_reason_values = _validate_status_reasons(stage_code, status_reason_codes)
    elif status_reason_codes:
        status_reason_values = _validate_status_reasons(stage_code, status_reason_codes)
    history_reason_text = _format_status_reason_labels(stage_code, status_reason_values)

    company_id_val: Optional[str] = str(payload.get("company_id")) if payload.get("company_id") else None
    vacancy_id_val: Optional[str] = str(payload.get("vacancy_id")) if payload.get("vacancy_id") else None
    own_company_id_val: Optional[str] = str(payload.get("own_company_id")) if payload.get("own_company_id") else None

    if vacancy_id_val:
        vrow = await db.execute(
            select(Vacancy).where(
                Vacancy.id == vacancy_id_val,
                Vacancy.tenant_id == tenant_id,
            )
        )
        v = vrow.scalar_one_or_none()
        if not v:
            raise HTTPException(status_code=404, detail="Vacancy not found")
        vacancy_id_val = v.id
        company_id_val = v.company_id
        if not own_company_id_val:
            own_company_id_val = getattr(v, "own_company_id", None)
        if acl and not acl.unrestricted:
            if v.company_id and str(v.company_id) not in acl.company_ids:
                raise HTTPException(status_code=403, detail="Forbidden vacancy for recruiter")
            # vacancy из допустимой компании — добавляем в набор для последующей проверки
            acl.vacancy_ids.add(str(v.id))

    _mgr_in = payload.get("manager") if payload.get("manager") is not None else payload.get("manager_id")
    manager_val: Optional[str] = (str(_mgr_in or "").strip() or None)
    if manager_val:
        try:
            manager_val = str(UUID(manager_val))
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid manager UUID")
        # Phase 2.6.G-5 Stage D — validate the manager user exists in
        # this tenant so we can safely shadow-write it into
        # ``Candidate.recruiter_id`` (FK to ``users.id``). Without this
        # guard, a payload-supplied ``manager`` UUID that doesn't exist
        # as a user row would pass validation here (legacy behaviour)
        # and then FK-fail when we mirror it into ``recruiter_id``.
        _mgr_check = await db.execute(
            select(User.id).where(
                User.id == manager_val,
                or_(User.tenant_id.is_(None), User.tenant_id == tenant_id),
                User.is_active.is_(True),
            )
        )
        if _mgr_check.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Manager user not found")
    if acl and not acl.unrestricted:
        if manager_val is None:
            manager_val = actor_id
        if manager_val is None or manager_val not in acl.manager_ids:
            raise HTTPException(status_code=403, detail="Forbidden manager for recruiter")
        if company_id_val and str(company_id_val) not in acl.company_ids:
            raise HTTPException(status_code=403, detail="Forbidden company for recruiter")

    assignment: AssignmentDecision | None = None
    if vacancy_id_val or company_id_val:
        assignment = await assign_recruiter_service(
            db=db,
            tenant_id=tenant_id,
            vacancy_id=vacancy_id_val,
            company_id=company_id_val,
        )

    extra_payload: Dict[str, Any] = {}
    raw_extra = payload.pop("extra", None)
    personal_data = payload.pop("personal_data", None)
    contacts_data = payload.pop("contacts", None)
    metadata_fields: Dict[str, Any] = {}
    for key in ("country_code", "city", "address", "birth_date"):
        if key in payload:
            metadata_fields[key] = payload.pop(key)
    if isinstance(raw_extra, dict):
        extra_payload.update(raw_extra)
    if personal_data is not None:
        extra_payload["personal_data"] = personal_data
    if contacts_data is not None:
        extra_payload["contacts"] = contacts_data
    personal_data_payload: Dict[str, Any] = {}
    if isinstance(personal_data, dict):
        personal_data_payload.update(personal_data)
    contacts_payload: Dict[str, Any] = {}
    if isinstance(contacts_data, dict):
        contacts_payload.update(contacts_data)

    if "birth_date" in metadata_fields and isinstance(metadata_fields["birth_date"], date):
        metadata_fields["birth_date"] = metadata_fields["birth_date"].isoformat()

    for key in ("birth_date", "country_code", "city", "address"):
        if key in metadata_fields:
            value = metadata_fields[key]
            if value is None:
                personal_data_payload.pop(key, None)
            else:
                personal_data_payload[key] = value

    for key, value in metadata_fields.items():
        extra_payload[key] = value

    if payload.get("phone") is not None:
        if payload["phone"]:
            contacts_payload["phone"] = payload["phone"]
        else:
            contacts_payload.pop("phone", None)
    if payload.get("phone_country_code") is not None:
        if payload["phone_country_code"]:
            contacts_payload["phone_country_code"] = payload["phone_country_code"]
        else:
            contacts_payload.pop("phone_country_code", None)
    if payload.get("email") is not None:
        if payload["email"]:
            contacts_payload["email"] = payload["email"]
        else:
            contacts_payload.pop("email", None)

    fn = str(payload.get("first_name") or "").strip()
    ln = str(payload.get("last_name") or "").strip()
    city_val = personal_data_payload.get("city") or metadata_fields.get("city")
    addr_val = personal_data_payload.get("address") or metadata_fields.get("address")
    from backend.app.services.normalization import ensure_latin_fields

    latin = ensure_latin_fields(first_name=fn, last_name=ln, city=city_val, address=addr_val)
    if latin.get("city_latin") is not None:
        personal_data_payload["city_latin"] = latin["city_latin"]
    if latin.get("address_latin") is not None:
        personal_data_payload["address_latin"] = latin["address_latin"]

    values: Dict[str, Any] = {
        "id": cand_id,
        "tenant_id": tenant_id,
        "first_name": fn,
        "last_name": ln,
        "first_name_latin": latin.get("first_name_latin"),
        "last_name_latin": latin.get("last_name_latin"),
        "phone": payload.get("phone"),
        "languages": languages,
        "tags": tags,
        "is_favorite": is_favorite,
        "stage": stage_code,
        "email": payload.get("email"),
        "note": payload.get("note"),
        "manager": manager_val,
        "short_id": None,
        "docs_progress": _dump_json_str(payload.get("docs_progress")),
        "extra": _dump_json_str(extra_payload),
        "personal_data": personal_data_payload or None,
        "contacts": contacts_payload or None,
        "status": stage_code,
        "status_reason": status_reason_values,
        "company_id": company_id_val,
        "vacancy_id": vacancy_id_val,
        # UI visibility depends on own_company_id (resolved from Topbar).
        # If not set explicitly, list endpoints will filter it out.
        "own_company_id": own_company_id_val,
        "created_at": _now_naive(),
        "updated_at": _now_naive(),
    }
    if source_val is not None:
        values["source"] = source_val
    if origin_payload is not None:
        values["origin"] = origin_payload
    # Phase 2.6.G-5 Stage D — shadow-write parity at INSERT time. The
    # canonical column is ``recruiter_id``; ``manager`` must mirror it.
    # Precedence: ``assignment.recruiter_id`` (from the vacancy/tenant
    # cascade in ``assign_recruiter_service``) wins over a payload-supplied
    # ``manager`` because the former is the system's deterministic choice
    # and the latter is a legacy UX hint. When no assignment ran we fall
    # back to ``manager_val`` (already validated against ``users`` above).
    if assignment and assignment.assigned:
        values["recruiter_id"] = assignment.recruiter_id
        values["manager"] = assignment.recruiter_id
    elif manager_val:
        values["recruiter_id"] = manager_val

    await db.execute(insert(Candidate).values(**values))

    history_entry = _make_stage_history(
        tenant_id,
        cand_id,
        from_code=None,
        to_code=stage_code,
        actor_id=actor_id,
        reason=history_reason_text,
    )
    db.add(history_entry)

    await db.commit()

    row = await db.execute(
        select(Candidate).where(Candidate.id == cand_id, Candidate.tenant_id == tenant_id)
    )
    c = row.scalar_one()
    await _ensure_short_id(db, c)

    # Auto-send RODO when candidate has email (art.14 GDPR)
    if (c.email or "").strip():
        try:
            await _send_rodo_email(db, candidate_id=c.id, tenant_id=tenant_id, actor_id=actor_id)
        except Exception:
            pass  # Don't fail creation; user can retry manually

    if assignment and assignment.assigned:
        await log_activity(
            db,
            tenant_id=tenant_id,
            action="candidate_assigned",
            actor_id=actor_id,
            target_type="candidate",
            target_id=c.id,
            payload={
                "candidate_id": c.id,
                "vacancy_id": vacancy_id_val,
                "company_id": company_id_val,
                "recruiter_id": assignment.recruiter_id,
                "strategy": assignment.strategy,
            },
        )
        # Phase 2.6.G-5 Stage C — emit audit-trail row for the initial
        # recruiter assignment. The INSERT statement above already wrote
        # ``recruiter_id = assignment.recruiter_id`` atomically, so we pass
        # ``write=False`` to avoid a redundant (no-op) UPDATE while still
        # appending the history row with ``from_user_id=NULL`` +
        # ``to_user_id=assignment.recruiter_id``. Explainability popover
        # (G-10) reads this row to render «первое назначение, стратегия X».
        try:
            await record_candidate_reassignment(
                db,
                c,
                new_recruiter_id=assignment.recruiter_id,
                reason="candidate_create",
                actor=actor_id,
                actor_kind="user" if actor_id else "system",
                note=f"strategy={assignment.strategy}",
                write=False,
                skip_if_unchanged=False,
            )
            await db.commit()
        except Exception:
            # Never fail candidate creation because of audit-row write —
            # the assignment itself already succeeded at INSERT time.
            await db.rollback()
            logging.getLogger(__name__).exception(
                "candidate_assignee_history create failed "
                "tenant=%s candidate=%s", tenant_id, c.id,
            )
    elif manager_val:
        # Phase 2.6.G-5 Stage D — INSERT-time shadow-write used
        # ``manager_val`` as the canonical recruiter (no vacancy/tenant
        # cascade fired). Emit the matching ``candidate_create`` history
        # row so the audit trail reflects the real first assignment.
        try:
            await record_candidate_reassignment(
                db,
                c,
                new_recruiter_id=manager_val,
                reason="candidate_create",
                actor=actor_id,
                actor_kind="user" if actor_id else "system",
                note="strategy=payload_manager",
                write=False,
                skip_if_unchanged=False,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logging.getLogger(__name__).exception(
                "candidate_assignee_history create failed (manager-only) "
                "tenant=%s candidate=%s", tenant_id, c.id,
            )
    recipient_ids: List[str] = []
    if c.recruiter_id:
        recipient_ids.append(c.recruiter_id)
        supervisor_id = await _get_supervisor_id(db, c.recruiter_id)
        if supervisor_id:
            recipient_ids.append(supervisor_id)
    if recipient_ids:
        await events.emit_event(
            db,
            tenant_id=tenant_id,
            event_type="candidate.created",
            payload={
                "candidate_id": c.id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "vacancy_id": c.vacancy_id,
                "company_id": c.company_id,
                "stage": c.stage,
                "recruiter_id": c.recruiter_id,
            },
            entity_type="candidate",
            entity_id=c.id,
            audience=EventAudience(user_ids=recipient_ids),
        )
    await db.commit()
    await db.refresh(c)

    await sync_candidate_links(
        db=db, tenant_id=UUID(tenant_id), candidate_id=UUID(c.id), candidate_stage=c.stage
    )

    # Minimal rules builder (R2.2): trigger candidate.created automation rules.
    try:
        await run_automation_rules(
            db,
            tenant_id=tenant_id,
            trigger="candidate.created",
            actor_id=actor_id,
            context={
                "entity_type": "candidate",
                "entity_id": c.id,
                "stage": c.stage,
                "company_id": c.company_id,
                "vacancy_id": c.vacancy_id,
                "assignee_id": c.recruiter_id or c.manager or actor_id,
            },
        )
        await db.commit()
    except Exception:
        await db.rollback()
    # UOS: default “call candidate” activity (deduped; tenant may disable via settings.uos_auto_activities_v1).
    try:
        from backend.app.services import uos_auto_activities

        await uos_auto_activities.ensure_candidate_created_call_task(
            db, tenant_id, actor_id, c, source_lead=source_lead
        )
        await db.commit()
    except Exception:
        await db.rollback()
    # `commit()` expires ORM instances; callers in async code must not touch columns
    # via implicit lazy load (MissingGreenlet). Reload before return.
    await db.refresh(c)
    return c


async def update_candidate_full(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    payload: Dict[str, Any],
    *,
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    status_reason_override: Any = _UNSET,
    acl: CandidateACL | None = None,
    agency_recruitment_bypass: Optional[AgencyRecruitmentWriteBypass] = None,
) -> Candidate:
    # ВАЖНО: доступ к кандидату уже проверен на уровне API (ensure_candidate_access,
    # can_client_edit / can_agency_edit, TenantVisibility и т.п.).
    # Здесь не дублируем сложный scope, чтобы не получать ложные 404 для
    # кросс-tenant кандидатов по handoff'у. Ищем только по id + soft-delete.
    row = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.deleted_at.is_(None),
        )
    )
    c = row.scalar_one_or_none()
    if not c:
        logger = logging.getLogger(__name__)
        logger.warning(
            "update_candidate_full: candidate not found candidate_id=%s (check if exists and deleted_at is null)",
            candidate_id,
        )
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate_home_tenant = str(getattr(c, "tenant_id", "") or "").strip()
    if candidate_home_tenant and not await _is_client_tenant(db, candidate_home_tenant):
        await require_agency_recruitment_write_allowed(
            db,
            agency_tenant_id=candidate_home_tenant,
            candidate_id=str(candidate_id),
            bypass=agency_recruitment_bypass,
        )

    payload = dict(payload or {})

    role_lane = str(actor_role or "").strip().lower()
    if role_lane == "hr_officer" and candidate_home_tenant and not await _is_client_tenant(db, candidate_home_tenant):
        if await agency_candidate_has_internal_hr_handoff_lane(
            db, agency_tenant_id=candidate_home_tenant, candidate_id=str(candidate_id)
        ):
            assert_hr_internal_lane_patch_keys_allowed(set(payload.keys()))

    source_update_present = "source" in payload
    origin_update_present = "origin" in payload
    source_update_value: Optional[str] = None
    if source_update_present:
        raw_source = payload.pop("source")
        normalized_source = normalize_candidate_source(str(raw_source) if raw_source is not None else None)
        source_update_value = normalized_source[:64] if normalized_source else None

    origin_update_value: Optional[Dict[str, Any]] = None
    if origin_update_present:
        raw_origin = payload.pop("origin")
        if raw_origin is None:
            origin_update_value = None
        elif isinstance(raw_origin, dict):
            origin_update_value = raw_origin
        else:
            origin_update_value = {"value": raw_origin}

    changes: Dict[str, Any] = {}
    history_entry: Optional[CandidateStageHistory] = None
    history_reason_text: Optional[str] = None
    new_stage_code: Optional[str] = None
    old_stage_code = str(getattr(c, "stage", None) or "").strip() or None
    old_status_code = str(getattr(c, "status", None) or "").strip() or None
    candidate_refresh_after_write = False
    status_reason_raw = payload.pop("status_reason", _UNSET)
    if status_reason_raw is _UNSET:
        status_reason_raw = status_reason_override
        status_reason_explicit = status_reason_override is not _UNSET
    else:
        status_reason_explicit = True
    status_reason_codes = (
        _normalize_status_reason_input(status_reason_raw)
        if status_reason_explicit
        else []
    )

    raw_extra_payload = payload.pop("extra", None)
    personal_data_payload = payload.pop("personal_data", None) if "personal_data" in payload else None
    contacts_payload = payload.pop("contacts", None) if "contacts" in payload else None
    metadata_fields: Dict[str, Any] = {}
    for key in ("country_code", "city", "address", "birth_date"):
        if key in payload:
            metadata_fields[key] = payload.pop(key)

    if "status" in payload and payload["status"] is not None and "stage" not in payload:
        payload["stage"] = payload["status"]

    if "first_name" in payload and payload["first_name"] is not None:
        changes["first_name"] = str(payload["first_name"]).strip()
    if "last_name" in payload and payload["last_name"] is not None:
        changes["last_name"] = str(payload["last_name"]).strip()

    if "first_name" in changes or "last_name" in changes:
        fn = changes.get("first_name") or getattr(c, "first_name", "")
        ln = changes.get("last_name") or getattr(c, "last_name", "")
        from backend.app.services.normalization import ensure_latin_fields

        latin = ensure_latin_fields(first_name=fn, last_name=ln)
        changes["first_name_latin"] = latin.get("first_name_latin")
        changes["last_name_latin"] = latin.get("last_name_latin")

    if "phone" in payload and payload["phone"] is not None:
        changes["phone"] = str(payload["phone"]).strip() or None
    if "phone_country_code" in payload and payload["phone_country_code"] is not None:
        prefix = str(payload["phone_country_code"]).strip()
        changes["phone_country_code"] = prefix or None
    if "email" in payload and payload["email"] is not None:
        changes["email"] = payload["email"]
    if "note" in payload and payload["note"] is not None:
        changes["note"] = payload["note"]

    # Phase 2.6.G-5 Stage D — ``Candidate.manager`` and ``Candidate.recruiter_id``
    # must stay in lock-step (see ``docs/specs/manager-assignment.md`` §1.2.1).
    # We parse both payload keys here and funnel them to a single validated
    # UUID; ``recruiter_id`` is the canonical column (FK to ``users.id``) and
    # wins when both are present with different values.
    _mgr_present = (payload.get("manager") is not None) or (payload.get("manager_id") is not None)
    _mgr_raw = (
        payload.get("manager") if payload.get("manager") is not None else payload.get("manager_id")
    )
    _rec_present = "recruiter_id" in payload
    _rec_raw = payload.get("recruiter_id") if _rec_present else None

    # Determine which field (if any) the PATCH is attempting to set, and to what.
    _assignment_provided = False
    _assignment_value: Optional[str] = None  # validated UUID string, or ``None`` to unassign
    if _rec_present:
        _assignment_provided = True
        if _rec_raw in (None, ""):
            _assignment_value = None
        else:
            try:
                _assignment_value = str(UUID(str(_rec_raw).strip()))
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid recruiter UUID")
    elif _mgr_present:
        _mgr_str = str(_mgr_raw or "").strip()
        if _mgr_str == "":
            # Legacy behaviour: empty ``manager`` string was a no-op (not an
            # unassign). Preserve that to avoid changing PATCH semantics for
            # callers that send empty strings.
            pass
        else:
            _assignment_provided = True
            try:
                _assignment_value = str(UUID(_mgr_str))
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid manager UUID")

    if _assignment_provided:
        # Validate the target user exists and belongs to the tenant before
        # we mirror the value into both columns (``recruiter_id`` has an FK
        # to ``users.id``; ``manager`` has none but we apply the same check
        # for consistency so the UI never lands on a ghost user).
        if _assignment_value is not None:
            recruiter_row = await db.execute(
                select(User).where(
                    User.id == _assignment_value,
                    or_(User.tenant_id.is_(None), User.tenant_id == tenant_id),
                    User.is_active.is_(True),
                )
            )
            if recruiter_row.scalar_one_or_none() is None:
                raise HTTPException(status_code=404, detail="Recruiter not found")

        # Shadow-write — write to both columns. When the payload provided
        # both ``manager`` and ``recruiter_id`` with different values we
        # canonicalise on ``recruiter_id`` (see branch ordering above).
        changes["recruiter_id"] = _assignment_value
        changes["manager"] = _assignment_value

    if "languages" in payload and payload["languages"] is not None:
        changes["languages"] = _ensure_langs(payload["languages"])
    
    if "tags" in payload and payload["tags"] is not None:
        tags_raw = payload["tags"]
        tags: list[str] = []
        if isinstance(tags_raw, (list, tuple)):
            tags = sorted(list(set(str(x).strip() for x in tags_raw if str(x).strip())))
        elif isinstance(tags_raw, str):
            tags_parts = [p.strip() for p in tags_raw.replace(",", " ").split() if p.strip()]
            tags = sorted(list(set(tags_parts)))
        changes["tags"] = tags

    if "is_favorite" in payload and payload["is_favorite"] is not None:
        changes["is_favorite"] = bool(payload["is_favorite"])

    if "birth_date" in metadata_fields and isinstance(metadata_fields["birth_date"], date):
        metadata_fields["birth_date"] = metadata_fields["birth_date"].isoformat()

    current_personal = getattr(c, "personal_data", None)
    personal_merge_needed = personal_data_payload is not None or bool(metadata_fields)
    if personal_merge_needed:
        merged_personal = dict(current_personal or {})
        if isinstance(personal_data_payload, dict):
            merged_personal.update(personal_data_payload)
        for key in ("birth_date", "country_code", "city", "address"):
            if key in metadata_fields:
                val = metadata_fields[key]
                if val is None or val == "":
                    merged_personal.pop(key, None)
                else:
                    merged_personal[key] = val
        city_val = merged_personal.get("city")
        addr_val = merged_personal.get("address")
        from backend.app.services.normalization import ensure_latin_fields

        latin = ensure_latin_fields(city=city_val, address=addr_val)
        if latin.get("city_latin") is not None:
            merged_personal["city_latin"] = latin["city_latin"]
        if latin.get("address_latin") is not None:
            merged_personal["address_latin"] = latin["address_latin"]
        if merged_personal != (current_personal or {}):
            changes["personal_data"] = merged_personal

    current_contacts = getattr(c, "contacts", None)
    contacts_merge_needed = contacts_payload is not None or any(
        key in payload for key in ("phone", "phone_country_code", "email")
    )
    if contacts_merge_needed:
        merged_contacts = dict(current_contacts or {})
        if isinstance(contacts_payload, dict):
            merged_contacts.update(contacts_payload)
        if "phone" in payload:
            phone_val = None
            if payload["phone"] is not None:
                phone_val = str(payload["phone"]).strip()
            if phone_val:
                merged_contacts["phone"] = phone_val
            else:
                merged_contacts.pop("phone", None)
        if "phone_country_code" in payload:
            prefix_val = None
            if payload["phone_country_code"] is not None:
                prefix_val = str(payload["phone_country_code"]).strip()
            if prefix_val:
                merged_contacts["phone_country_code"] = prefix_val
            else:
                merged_contacts.pop("phone_country_code", None)
        if "email" in payload:
            email_val = payload["email"]
            if email_val:
                merged_contacts["email"] = email_val
            else:
                merged_contacts.pop("email", None)
        if merged_contacts != (current_contacts or {}):
            changes["contacts"] = merged_contacts

    if source_update_present:
        changes["source"] = source_update_value
    if origin_update_present:
        changes["origin"] = origin_update_value

    extra_merge: Dict[str, Any] = {}
    if isinstance(raw_extra_payload, dict):
        extra_merge.update(raw_extra_payload)
    if personal_data_payload is not None:
        extra_merge["personal_data"] = personal_data_payload
    if contacts_payload is not None:
        extra_merge["contacts"] = contacts_payload
    for key, value in metadata_fields.items():
        extra_merge[key] = value
    if extra_merge:
        current = _as_dict_safe(getattr(c, "extra", None))
        merged = _merge_dict(current, extra_merge)
        changes["extra"] = _dump_json_str(merged)

    if "docs_progress" in payload and payload["docs_progress"] is not None:
        current = _as_dict_safe(getattr(c, "docs_progress", None))
        merged = _merge_dict(current, dict(payload["docs_progress"] or {}))
        changes["docs_progress"] = _dump_json_str(merged)

    stage_changed = False
    if "stage" in payload and payload["stage"] is not None:
        s_raw = str(payload["stage"] or "").strip()
        if s_raw:
            normalized = _normalize_stage_to_code(s_raw)
            if not normalized:
                raise HTTPException(status_code=422, detail=f"Unknown stage '{s_raw}'")
            new_stage_code = normalized

            # Для клиентских тенантов запрещаем перевод на стадии,
            # которые не помечены как visible_for_client.
            if await _is_client_tenant(db, tenant_id) and not _stage_visible_for_client(new_stage_code):
                raise HTTPException(
                    status_code=403,
                    detail=f"Stage '{new_stage_code}' is not allowed for client tenant",
                )

            _validate_stage_transition(getattr(c, "stage", None), new_stage_code)
            await _enforce_rodo_before_contact_stage(
                db,
                candidate_id=candidate_id,
                target_stage_code=new_stage_code,
            )
            effective_extra = (
                _as_dict_safe(changes.get("extra"))
                if "extra" in changes
                else _as_dict_safe(getattr(c, "extra", None))
            )
            effective_personal = (
                _as_dict_safe(changes.get("personal_data"))
                if "personal_data" in changes
                else _as_dict_safe(getattr(c, "personal_data", None))
            )
            hiring_gates = await resolve_hiring_pipeline_gates(db, tenant_id)
            await enforce_pipeline_doc_forward_block(
                db,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                old_stage=getattr(c, "stage", None),
                new_stage=new_stage_code,
                extra=effective_extra,
                personal=effective_personal,
                gates=hiring_gates,
            )
            enforce_pipeline_vacancy_forward_block(
                old_stage=getattr(c, "stage", None),
                new_stage=new_stage_code,
                vacancy_id=_effective_vacancy_id_from_patch_payload(c, payload),
                gates=hiring_gates,
            )
            await enforce_pipeline_contact_attempt_forward_block(
                db,
                tenant_id=tenant_id,
                candidate=c,
                old_stage=getattr(c, "stage", None),
                new_stage=new_stage_code,
                gates=hiring_gates,
            )
            await enforce_critical_risk_forward_stage_gate(
                db,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                old_stage=getattr(c, "stage", None),
                new_stage=new_stage_code,
            )
            await _enforce_docs_ready_for_handoff_stage(
                db,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                target_stage_code=new_stage_code,
                extra=effective_extra,
                personal=effective_personal,
            )
            changes["stage"] = new_stage_code
            changes["status"] = new_stage_code
            stage_changed = True

    validated_status_reasons: list[str] = []
    target_stage_for_reason = new_stage_code if stage_changed else getattr(c, "stage", None)
    if stage_changed or status_reason_explicit:
        if target_stage_for_reason in _REASON_REQUIRED_STAGES:
            validated_status_reasons = _validate_status_reasons(target_stage_for_reason, status_reason_codes)
            changes["status_reason"] = validated_status_reasons
        elif status_reason_explicit:
            validated_status_reasons = _validate_status_reasons(target_stage_for_reason, status_reason_codes)
            changes["status_reason"] = validated_status_reasons
    if (
        stage_changed
        and target_stage_for_reason not in _REASON_REQUIRED_STAGES
        and not status_reason_explicit
        and getattr(c, "status_reason", None)
    ):
        changes["status_reason"] = []
    if validated_status_reasons:
        history_reason_text = _format_status_reason_labels(target_stage_for_reason, validated_status_reasons)

    if "vacancy_id" in payload and payload["vacancy_id"] is not None:
        if str(payload["vacancy_id"]) == "":
            changes["vacancy_id"] = None
            changes["company_id"] = None
        else:
            # Look up by id only: candidate access already enforced at API layer;
            # vacancy may belong to agency (e.g. handoff) when current tenant is client.
            vrow = await db.execute(
                select(Vacancy).where(Vacancy.id == str(payload["vacancy_id"]))
            )
            v = vrow.scalar_one_or_none()
            if not v:
                raise HTTPException(status_code=404, detail="Vacancy not found")
            if acl and not acl.unrestricted:
                if v.company_id and str(v.company_id) not in acl.company_ids:
                    raise HTTPException(status_code=403, detail="Forbidden vacancy for recruiter")
                acl.vacancy_ids.add(str(v.id))
            changes["vacancy_id"] = str(v.id)
            changes["company_id"] = str(v.company_id)
            changes["tenant_id"] = str(v.tenant_id)

    if "company_id" in payload and payload.get("vacancy_id") is None:
        company_val = str(payload["company_id"]) if payload["company_id"] else None
        if company_val and acl and not acl.unrestricted and company_val not in acl.company_ids:
            raise HTTPException(status_code=403, detail="Forbidden company for recruiter")
        changes["company_id"] = company_val
        if company_val:
            company_row = await db.execute(select(Company).where(Company.id == company_val))
            company = company_row.scalar_one_or_none()
            if not company:
                raise HTTPException(status_code=404, detail="Company not found")
            changes["tenant_id"] = str(company.tenant_id)

    if not c.short_id:
        changes["short_id"] = await _generate_unique_short_id(db)

    target_manager = changes.get("manager", getattr(c, "manager", None))
    target_company = changes.get("company_id", getattr(c, "company_id", None))
    target_vacancy = changes.get("vacancy_id", getattr(c, "vacancy_id", None))
    target_recruiter = changes.get("recruiter_id", getattr(c, "recruiter_id", None))
    if acl and not _candidate_matches_acl(
        acl,
        manager=target_manager,
        company=target_company,
        vacancy=target_vacancy,
        recruiter_id=target_recruiter,
    ):
        raise HTTPException(status_code=403, detail="Forbidden candidate scope for recruiter")

    if changes:
        try:
            # Change log (candidate.updated): record meaningful diffs for the Candidate card.
            # This is intentionally best-effort and must never break the update.
            try:
                diff_items: list[dict[str, Any]] = []
                changed_keys: list[str] = []

                def _safe_value(key: str, val: Any) -> Any:
                    if val is None:
                        return None
                    if key in {"password", "password_hash"}:
                        return None
                    if key in {"email", "phone", "address"}:
                        s = str(val)
                        if len(s) <= 4:
                            return "***"
                        return s[:2] + "***" + s[-2:]
                    if isinstance(val, (str, int, float, bool)):
                        return val
                    if isinstance(val, (list, dict)):
                        return val
                    return str(val)

                def _json_dict_or_empty(v: Any) -> dict:
                    if v is None:
                        return {}
                    if isinstance(v, dict):
                        return v
                    if isinstance(v, str):
                        s = v.strip()
                        if not s:
                            return {}
                        try:
                            parsed = json.loads(s)
                            return parsed if isinstance(parsed, dict) else {}
                        except Exception:
                            return {}
                    return {}

                # Column-level diffs (shallow)
                for key, new_val in changes.items():
                    if key in {"updated_at"}:
                        continue
                    if key in {"extra", "docs_progress"}:
                        continue
                    old_val = getattr(c, key, None)
                    if old_val != new_val:
                        changed_keys.append(key)
                        diff_items.append(
                            {
                                "field": key,
                                "from": _safe_value(key, old_val),
                                "to": _safe_value(key, new_val),
                            }
                        )

                # JSON diffs: store changed top-level keys only (avoid huge payloads)
                for json_key in {"extra", "docs_progress"}:
                    if json_key not in changes:
                        continue
                    old_dict = _json_dict_or_empty(getattr(c, json_key, None))
                    new_dict = _json_dict_or_empty(changes.get(json_key))
                    touched: list[str] = []
                    for k in set(old_dict.keys()) | set(new_dict.keys()):
                        if old_dict.get(k) != new_dict.get(k):
                            touched.append(str(k))
                    if touched:
                        touched.sort()
                        changed_keys.append(json_key)
                        diff_items.append(
                            {
                                "field": json_key,
                                "changed_keys": touched[:80],
                                "changed_keys_count": len(touched),
                            }
                        )

                if changed_keys:
                    await log_activity(
                        db,
                        tenant_id=tenant_id,
                        action="candidate.updated",
                        actor_id=actor_id,
                        target_type="candidate",
                        target_id=candidate_id,
                        payload={
                            "changed_keys": sorted(list(set(changed_keys))),
                            "diff": diff_items[:80],
                            "source": "candidate_card",
                        },
                    )
            except Exception:
                logging.getLogger(__name__).exception(
                    "candidate.updated activity log failed tenant=%s candidate=%s",
                    tenant_id,
                    candidate_id,
                )

            changes["updated_at"] = _now_naive()
            # Phase 2.6.G-5 Stage C — capture the pre-UPDATE recruiter_id so
            # we can emit an audit row after the UPDATE commits. The row is
            # appended with ``write=False`` because the ``update(Candidate)``
            # statement below already applies the new value.
            recruiter_id_changed = "recruiter_id" in changes
            recruiter_id_before: Optional[str] = None
            recruiter_id_after: Optional[str] = None
            if recruiter_id_changed:
                recruiter_id_before = (
                    str(getattr(c, "recruiter_id", None) or "").strip() or None
                )
                _raw_after = changes.get("recruiter_id")
                recruiter_id_after = (
                    str(_raw_after).strip() if _raw_after else None
                ) or None
            await db.execute(
                update(Candidate)
                .where(Candidate.id == candidate_id, Candidate.deleted_at.is_(None))
                .values(**changes)
            )

            if stage_changed and new_stage_code:
                history_entry = _make_stage_history(
                    tenant_id,
                    candidate_id,
                    from_code=getattr(c, "stage", None),
                    to_code=new_stage_code,
                    actor_id=actor_id,
                    reason=history_reason_text,
                )
                db.add(history_entry)

            await db.commit()
            await db.refresh(c)
            candidate_refresh_after_write = True
            email_after = str(getattr(c, "email", "") or "").strip()

            # Phase 2.6.G-5 Stage C — emit audit-trail row for
            # ``Candidate.recruiter_id`` reassignments driven by the single-
            # candidate PATCH endpoint. We write the row AFTER the UPDATE
            # has committed so the audit trail only reflects persisted
            # changes; a failed commit rolls back above and never reaches
            # this block. ``write=False`` because the UPDATE already applied
            # the new value; ``skip_if_unchanged=False`` because the old
            # value is supplied explicitly (the refreshed candidate now
            # holds the new value — if we let the helper auto-detect from
            # ``candidate.recruiter_id`` it would compare ``new == new`` and
            # skip).
            if recruiter_id_changed and recruiter_id_before != recruiter_id_after:
                try:
                    history_row = CandidateAssigneeHistory(
                        id=str(_uuid.uuid4()),
                        tenant_id=str(tenant_id),
                        candidate_id=str(candidate_id),
                        from_user_id=recruiter_id_before,
                        to_user_id=recruiter_id_after,
                        reason="manual_single",
                        actor_user_id=(str(actor_id) if actor_id else None),
                        actor_kind="user" if actor_id else "system",
                        note=None,
                        changed_at=_now_utc(),
                    )
                    db.add(history_row)
                    await db.commit()
                except Exception:
                    await db.rollback()
                    logging.getLogger(__name__).exception(
                        "candidate_assignee_history update failed "
                        "tenant=%s candidate=%s",
                        tenant_id,
                        candidate_id,
                    )

        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Update failed: {e}")

        # Side-effects must never break the update itself.
        if stage_changed:
            # Snapshot ORM fields to avoid lazy-load IO in async side-effects.
            stage_after = str(getattr(c, "stage", None) or "").strip() or None
            company_after = str(getattr(c, "company_id", None) or "").strip() or None
            vacancy_after = str(getattr(c, "vacancy_id", None) or "").strip() or None
            assignee_after = str(getattr(c, "recruiter_id", None) or "").strip() or None
            if not assignee_after:
                assignee_after = str(getattr(c, "manager", None) or "").strip() or None
            if not assignee_after:
                assignee_after = str(actor_id or "").strip() or None
            # Plain snapshot for notifications to avoid ORM attribute IO after commits/rollbacks.
            cand_snapshot = SimpleNamespace(
                id=str(getattr(c, "id", "") or candidate_id),
                short_id=getattr(c, "short_id", None),
                first_name=getattr(c, "first_name", None),
                last_name=getattr(c, "last_name", None),
                intake_state=getattr(c, "intake_state", None),
                intake_token=getattr(c, "intake_token", None),
                status_share_token=getattr(c, "status_share_token", None),
            )

            try:
                await sync_candidate_links(
                    db=db,
                    tenant_id=UUID(tenant_id),
                    candidate_id=UUID(candidate_id),
                    candidate_stage=stage_after,
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "sync_candidate_links failed tenant=%s candidate=%s",
                    tenant_id,
                    candidate_id,
                )
                try:
                    await db.rollback()
                except Exception:
                    pass

            # Minimal rules builder (R2.2): trigger candidate.stage_changed rules.
            try:
                await run_automation_rules(
                    db,
                    tenant_id=tenant_id,
                    trigger="candidate.stage_changed",
                    actor_id=actor_id,
                    context={
                        "entity_type": "candidate",
                        "entity_id": c.id,
                        "stage_from": old_stage_code,
                        "stage_to": stage_after,
                        "company_id": company_after,
                        "vacancy_id": vacancy_after,
                        "assignee_id": assignee_after,
                    },
                )
                await db.commit()
            except Exception:
                try:
                    await db.rollback()
                except Exception:
                    pass

            try:
                await candidate_tg_notifications.send_candidate_stage_changed_telegram(
                    db,
                    tenant_id=tenant_id,
                    candidate=cand_snapshot,  # type: ignore[arg-type]
                    old_stage=old_stage_code,
                    new_stage=stage_after,
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "candidate telegram notify stage failed tenant=%s candidate=%s",
                    tenant_id,
                    candidate_id,
                )

            try:
                from backend.app.services import uos_auto_activities

                await uos_auto_activities.ensure_candidate_stage_follow_up_task(
                    db,
                    tenant_id,
                    str(actor_id or "").strip() or "uos-auto",
                    c,
                    old_stage_code,
                    stage_after,
                )
                await db.commit()
            except Exception:
                logging.getLogger(__name__).exception(
                    "uos candidate stage follow-up failed tenant=%s candidate=%s",
                    tenant_id,
                    candidate_id,
                )
                try:
                    await db.rollback()
                except Exception:
                    pass
    elif stage_changed and new_stage_code:
        try:
            history_entry = _make_stage_history(
                tenant_id,
                candidate_id,
                from_code=getattr(c, "stage", None),
                to_code=new_stage_code,
                actor_id=actor_id,
                reason=history_reason_text,
            )
            db.add(history_entry)
            await db.commit()
            await db.refresh(c)
            candidate_refresh_after_write = True
            email_after = str(getattr(c, "email", "") or "").strip()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Update failed: {e}")

        # Side-effects (best-effort)
        stage_after = str(getattr(c, "stage", None) or "").strip() or None
        cand_snapshot = SimpleNamespace(
            id=str(getattr(c, "id", "") or candidate_id),
            short_id=getattr(c, "short_id", None),
            first_name=getattr(c, "first_name", None),
            last_name=getattr(c, "last_name", None),
            intake_state=getattr(c, "intake_state", None),
            intake_token=getattr(c, "intake_token", None),
            status_share_token=getattr(c, "status_share_token", None),
        )
        try:
            await sync_candidate_links(
                db=db,
                tenant_id=UUID(tenant_id),
                candidate_id=UUID(candidate_id),
                candidate_stage=stage_after,
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "sync_candidate_links failed tenant=%s candidate=%s",
                tenant_id,
                candidate_id,
            )
            try:
                await db.rollback()
            except Exception:
                pass

        try:
            await candidate_tg_notifications.send_candidate_stage_changed_telegram(
                db,
                tenant_id=tenant_id,
                candidate=cand_snapshot,  # type: ignore[arg-type]
                old_stage=old_stage_code,
                new_stage=stage_after,
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "candidate telegram notify stage failed tenant=%s candidate=%s",
                tenant_id,
                candidate_id,
            )

        try:
            from backend.app.services import uos_auto_activities

            await uos_auto_activities.ensure_candidate_stage_follow_up_task(
                db,
                tenant_id,
                str(actor_id or "").strip() or "uos-auto",
                c,
                old_stage_code,
                stage_after,
            )
            await db.commit()
        except Exception:
            logging.getLogger(__name__).exception(
                "uos candidate stage follow-up failed tenant=%s candidate=%s",
                tenant_id,
                candidate_id,
            )
            try:
                await db.rollback()
            except Exception:
                pass

    # G-1 zero-leak: entering operational terminal (canonical completed stage **or** row-level
    # ``status`` in the completed set) cancels reminders / planner / bell noise. Runs after any
    # PATCH that persisted and refreshed the candidate row — not only ``stage_changed``.
    if candidate_refresh_after_write:
        try:
            await maybe_apply_candidate_operationally_terminal_cleanup(
                db,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                old_stage=old_stage_code,
                old_status=old_status_code,
                new_stage=str(getattr(c, "stage", None) or "").strip() or None,
                new_status=str(getattr(c, "status", None) or "").strip() or None,
                actor_id=actor_id,
            )
            await db.commit()
        except Exception:
            logging.getLogger(__name__).exception(
                "candidate lifecycle cleanup failed tenant=%s candidate=%s",
                tenant_id,
                candidate_id,
            )
            try:
                await db.rollback()
            except Exception:
                pass

    # Auto-send RODO when candidate has email (art.14 GDPR); send_rodo_email no-ops if already sent
    email_after = locals().get("email_after", "") or ""
    if str(email_after).strip():
        try:
            await _send_rodo_email(db, candidate_id=candidate_id, tenant_id=tenant_id, actor_id=actor_id)
            await db.commit()
        except Exception:
            await db.rollback()

    return c

from typing import TypedDict

class BulkStageResult(TypedDict, total=False):
    candidate_id: str
    stage: str
    ok: bool
    error: str

class BulkManagerResult(TypedDict, total=False):
    candidate_id: str
    manager: Optional[str]
    ok: bool
    error: str

class BulkDeleteResult(TypedDict, total=False):
    candidate_id: str
    ok: bool
    error: str

async def bulk_update_stage(
    db: AsyncSession,
    tenant_id: str,
    candidate_ids: list[str],
    stage: str,
    *,
    actor_id: Optional[str] = None,
    status_reason: Any = _UNSET,
    acl: CandidateACL | None = None,
) -> list[BulkStageResult]:
    def _bulk_error_value(detail: Any) -> str:
        if isinstance(detail, (dict, list)):
            try:
                return json.dumps(detail, ensure_ascii=False)
            except Exception:
                return str(detail)
        return str(detail)

    target_stage = _normalize_stage_to_code(stage) or stage
    client_tenant = await _is_client_tenant(db, tenant_id)
    hiring_gates = await resolve_hiring_pipeline_gates(db, tenant_id)

    out: list[BulkStageResult] = []
    status_reason_explicit = status_reason is not _UNSET and status_reason is not None
    status_reason_codes_input = (
        _normalize_status_reason_input(status_reason) if status_reason_explicit else []
    )

    for cid in candidate_ids:
        try:
            row = await db.execute(
                select(Candidate).where(
                    Candidate.id == cid,
                    Candidate.tenant_id == tenant_id,
                    Candidate.deleted_at.is_(None),
                )
            )
            c = row.scalar_one_or_none()
            if not c:
                out.append({"candidate_id": cid, "stage": target_stage, "ok": False, "error": "not found"})
                continue

            if not _candidate_matches_acl(
                acl,
                manager=getattr(c, "manager", None),
                company=getattr(c, "company_id", None),
                vacancy=getattr(c, "vacancy_id", None),
                recruiter_id=getattr(c, "recruiter_id", None),
            ):
                out.append({"candidate_id": cid, "stage": target_stage, "ok": False, "error": "forbidden"})
                continue

            cand_tid = str(getattr(c, "tenant_id", "") or "").strip()
            if not client_tenant:
                lock_err = await agency_recruitment_lock_bulk_error(
                    db,
                    agency_tenant_id=cand_tid,
                    candidate_id=cid,
                    operation_label="cannot change stage",
                )
                if lock_err:
                    out.append({"candidate_id": cid, "stage": target_stage, "ok": False, "error": lock_err})
                    continue

            normalized = _normalize_stage_to_code(target_stage) or target_stage
            if not normalized:
                out.append({"candidate_id": cid, "stage": target_stage, "ok": False, "error": "unknown stage"})
                continue

            if client_tenant and not _stage_visible_for_client(normalized):
                out.append(
                    {
                        "candidate_id": cid,
                        "stage": normalized,
                        "ok": False,
                        "error": "stage not allowed for client tenant",
                    }
                )
                continue

            _validate_stage_transition(getattr(c, "stage", None), normalized)
            await _enforce_rodo_before_contact_stage(
                db,
                candidate_id=cid,
                target_stage_code=normalized,
            )
            try:
                await enforce_pipeline_doc_forward_block(
                    db,
                    tenant_id=tenant_id,
                    candidate_id=cid,
                    old_stage=getattr(c, "stage", None),
                    new_stage=normalized,
                    extra=_as_dict_safe(getattr(c, "extra", None)),
                    personal=_as_dict_safe(getattr(c, "personal_data", None)),
                    gates=hiring_gates,
                )
                enforce_pipeline_vacancy_forward_block(
                    old_stage=getattr(c, "stage", None),
                    new_stage=normalized,
                    vacancy_id=getattr(c, "vacancy_id", None),
                    gates=hiring_gates,
                )
                await enforce_pipeline_contact_attempt_forward_block(
                    db,
                    tenant_id=tenant_id,
                    candidate=c,
                    old_stage=getattr(c, "stage", None),
                    new_stage=normalized,
                    gates=hiring_gates,
                )
                await enforce_critical_risk_forward_stage_gate(
                    db,
                    tenant_id=tenant_id,
                    candidate_id=cid,
                    old_stage=getattr(c, "stage", None),
                    new_stage=normalized,
                )
            except HTTPException as exc:
                out.append(
                    {
                        "candidate_id": cid,
                        "stage": normalized,
                        "ok": False,
                        "error": _bulk_error_value(exc.detail),
                    }
                )
                continue

            await _enforce_docs_ready_for_handoff_stage(
                db,
                tenant_id=tenant_id,
                candidate_id=cid,
                target_stage_code=normalized,
                extra=_as_dict_safe(getattr(c, "extra", None)),
                personal=_as_dict_safe(getattr(c, "personal_data", None)),
            )

            try:
                if normalized in _REASON_REQUIRED_STAGES or status_reason_explicit:
                    reason_codes = _validate_status_reasons(normalized, status_reason_codes_input)
                else:
                    reason_codes = []
            except HTTPException as exc:
                out.append(
                    {
                        "candidate_id": cid,
                        "stage": normalized,
                        "ok": False,
                        "error": _bulk_error_value(exc.detail),
                    }
                )
                continue

            old_stage_bulk = str(getattr(c, "stage", None) or "").strip() or None
            old_status_bulk = str(getattr(c, "status", None) or "").strip() or None

            await db.execute(
                update(Candidate)
                .where(Candidate.id == cid, Candidate.tenant_id == tenant_id)
                .values(
                    stage=normalized,
                    status=normalized,
                    status_reason=reason_codes,
                    updated_at=_now_naive(),
                )
            )

            history_entry = _make_stage_history(
                tenant_id,
                cid,
                from_code=getattr(c, "stage", None),
                to_code=normalized,
                actor_id=actor_id,
                reason=_format_status_reason_labels(normalized, reason_codes),
            )
            db.add(history_entry)

            await db.commit()

            # G-1 zero-leak: silence reminders/notifications/planner for terminal stages.
            try:
                await maybe_apply_candidate_operationally_terminal_cleanup(
                    db,
                    tenant_id=tenant_id,
                    candidate_id=cid,
                    old_stage=old_stage_bulk,
                    old_status=old_status_bulk,
                    new_stage=normalized,
                    new_status=normalized,
                    actor_id=actor_id,
                )
                await db.commit()
            except Exception:
                logging.getLogger(__name__).exception(
                    "bulk candidate lifecycle cleanup failed tenant=%s candidate=%s",
                    tenant_id,
                    cid,
                )
                try:
                    await db.rollback()
                except Exception:
                    pass

            await sync_candidate_links(
                db=db,
                tenant_id=UUID(tenant_id),
                candidate_id=UUID(cid),
                candidate_stage=normalized,
            )
            await candidate_tg_notifications.send_candidate_stage_changed_telegram(
                db,
                tenant_id=tenant_id,
                candidate=c,
                old_stage=getattr(c, "stage", None),
                new_stage=normalized,
            )

            try:
                from backend.app.services import uos_auto_activities

                await uos_auto_activities.ensure_candidate_stage_follow_up_task(
                    db,
                    tenant_id,
                    str(actor_id or "").strip() or "uos-auto",
                    c,
                    getattr(c, "stage", None),
                    normalized,
                )
                await db.commit()
            except Exception:
                logging.getLogger(__name__).exception(
                    "uos candidate stage follow-up failed tenant=%s candidate=%s",
                    tenant_id,
                    cid,
                )
                try:
                    await db.rollback()
                except Exception:
                    pass

            out.append({"candidate_id": cid, "stage": normalized, "ok": True})
        except HTTPException as exc:
            await db.rollback()
            out.append(
                {
                    "candidate_id": cid,
                    "stage": target_stage,
                    "ok": False,
                    "error": _bulk_error_value(exc.detail),
                }
            )
        except Exception as e:
            await db.rollback()
            out.append({"candidate_id": cid, "stage": target_stage, "ok": False, "error": str(e)})

    return out

async def bulk_update_manager(
    db: AsyncSession,
    tenant_id: str,
    candidate_ids: list[str],
    manager_id: str,
    *,
    actor_id: Optional[str] = None,
    acl: CandidateACL | None = None,
) -> list[BulkManagerResult]:
    """Bulk-reassign the «responsible» user for a set of candidates.

    Phase 2.6.G-5 Stage D — this endpoint historically wrote only to
    ``Candidate.manager`` (``update(Candidate).values(manager=...)``) in a
    single SQL statement, which (a) left ``Candidate.recruiter_id``
    unchanged — causing the NBA/notifications/bell to keep showing the old
    recruiter (the split-brain documented in
    ``docs/specs/manager-assignment.md`` §1.2.1), and (b) produced no audit
    trail. Stage D funnels every candidate through
    :func:`record_candidate_reassignment` so the shadow-write invariant
    (``manager == recruiter_id``) and the ``candidate_assignee_history``
    row are both guaranteed.

    Trade-off: the single bulk ``UPDATE`` is replaced with one flush per
    candidate (inside the helper). ``bulk_update_manager`` is a user-action
    on a visible selection (typical N < 100), so the per-row cost is
    acceptable and the correctness guarantees outweigh it.
    """
    manager_value = (manager_id or "").strip()
    try:
        manager_value = str(UUID(manager_value))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=422, detail="Invalid manager UUID") from exc

    results: list[BulkManagerResult] = []

    if not candidate_ids:
        return results

    rows = await db.execute(
        select(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.deleted_at.is_(None),
            Candidate.id.in_(candidate_ids),
        )
    )
    found = {str(c.id): c for c in rows.scalars().all()}

    applied_at_least_one = False
    for cid in candidate_ids:
        entry: BulkManagerResult = {"candidate_id": cid, "manager": manager_value}
        candidate_row = found.get(cid)
        if not candidate_row:
            entry["ok"] = False
            entry["error"] = "not found"
            results.append(entry)
            continue
        if not _candidate_matches_acl(
            acl,
            manager=getattr(candidate_row, "manager", None),
            company=getattr(candidate_row, "company_id", None),
            vacancy=getattr(candidate_row, "vacancy_id", None),
            recruiter_id=getattr(candidate_row, "recruiter_id", None),
        ):
            entry["ok"] = False
            entry["error"] = "forbidden"
            results.append(entry)
            continue

        cand_tid = str(getattr(candidate_row, "tenant_id", "") or "").strip()
        if cand_tid and not await _is_client_tenant(db, cand_tid):
            lock_err = await agency_recruitment_lock_bulk_error(
                db,
                agency_tenant_id=cand_tid,
                candidate_id=cid,
                operation_label="cannot reassign manager",
            )
            if lock_err:
                entry["ok"] = False
                entry["error"] = lock_err
                results.append(entry)
                continue

        try:
            await record_candidate_reassignment(
                db,
                candidate_row,
                new_recruiter_id=manager_value,
                reason="manual_bulk",
                actor=actor_id,
                actor_kind="user" if actor_id else "system",
                note=None,
            )
            # Ensure ``updated_at`` reflects the change even if the helper
            # short-circuited (no-op on unchanged recruiter_id) — bulk-set
            # semantics expect a touch on every selected candidate.
            candidate_row.updated_at = _now_naive()
            await db.flush()
            entry["ok"] = True
            applied_at_least_one = True
        except Exception as exc:  # pragma: no cover - defensive
            entry["ok"] = False
            entry["error"] = f"update_failed: {exc}"
        results.append(entry)

    if applied_at_least_one:
        try:
            await db.commit()
        except Exception as exc:  # pragma: no cover - defensive
            await db.rollback()
            for entry in results:
                if entry.get("ok"):
                    entry["ok"] = False
                    entry["error"] = f"commit_failed: {exc}"
    return results


async def bulk_delete_candidates(
    db: AsyncSession,
    tenant_id: str,
    candidate_ids: list[str],
    *,
    actor_id: Optional[str] = None,  # kept for future audit trail
    acl: CandidateACL | None = None,
) -> list[BulkDeleteResult]:
    """Bulk delete candidates (soft delete)."""
    results: list[BulkDeleteResult] = []
    allowed_indexes: list[int] = []

    if not candidate_ids:
        return results

    rows = await db.execute(
        select(Candidate).where(
            Candidate.tenant_id == tenant_id,
            Candidate.deleted_at.is_(None),
            Candidate.id.in_(candidate_ids),
        )
    )
    found = {str(c.id): c for c in rows.scalars().all()}

    for cid in candidate_ids:
        entry: BulkDeleteResult = {"candidate_id": cid}
        candidate_row = found.get(cid)
        if not candidate_row:
            entry["ok"] = False
            entry["error"] = "not found"
            results.append(entry)
            continue
        if not _candidate_matches_acl(
            acl,
            manager=getattr(candidate_row, "manager", None),
            company=getattr(candidate_row, "company_id", None),
            vacancy=getattr(candidate_row, "vacancy_id", None),
            recruiter_id=getattr(candidate_row, "recruiter_id", None),
        ):
            entry["ok"] = False
            entry["error"] = "forbidden"
            results.append(entry)
            continue

        cand_tid = str(getattr(candidate_row, "tenant_id", "") or "").strip()
        if cand_tid and not await _is_client_tenant(db, cand_tid):
            lock_err = await agency_recruitment_lock_bulk_error(
                db,
                agency_tenant_id=cand_tid,
                candidate_id=cid,
                operation_label="cannot delete candidate",
            )
            if lock_err:
                entry["ok"] = False
                entry["error"] = lock_err
                results.append(entry)
                continue

        allowed_indexes.append(len(results))
        results.append(entry)

    if not allowed_indexes:
        return results

    # Delete each candidate individually to ensure sync_candidate_links is called for each
    for idx in allowed_indexes:
        cid = results[idx]["candidate_id"]
        try:
            await delete_candidate_full(db, tenant_id, cid)
            results[idx]["ok"] = True
            results[idx].pop("error", None)
        except Exception as exc:
            # rollback is handled in delete_candidate_full
            results[idx]["ok"] = False
            results[idx]["error"] = f"delete_failed: {exc}"

    return results


async def delete_candidate_full(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
) -> None:
    row = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
            Candidate.deleted_at.is_(None),
        )
    )
    c = row.scalar_one_or_none()
    if not c:
        return  # идемпотентность

    await db.execute(
        update(Candidate)
        .where(Candidate.id == candidate_id, Candidate.tenant_id == tenant_id)
        .values(deleted_at=_now_naive(), updated_at=_now_naive())
    )
    await db.commit()

    # G-1 zero-leak: cancel pending reminders / mark notifications read / cancel future planner
    # events for this candidate. Runs unconditionally on delete (any prior stage is irrelevant).
    try:
        await apply_candidate_deletion_cleanup(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            actor_id=None,
        )
        await db.commit()
    except Exception:
        logging.getLogger(__name__).exception(
            "candidate deletion lifecycle cleanup failed tenant=%s candidate=%s",
            tenant_id,
            candidate_id,
        )
        try:
            await db.rollback()
        except Exception:
            pass

    try:
        await sync_candidate_links(
            db=db,
            tenant_id=UUID(tenant_id),
            candidate_id=UUID(candidate_id),
            candidate_stage=None,
        )
    except Exception:
        # не валим delete, ошибки синка игнорируем
        pass

_REASON_LABELS = {
    stage: {item["code"]: item["label"] for item in items}
    for stage, items in STATUS_REASON_CHOICES.items()
}
_REASON_CODES = {stage: set(labels.keys()) for stage, labels in _REASON_LABELS.items()}
_REASON_REQUIRED_STAGES = set(_REASON_CODES.keys())


def _stage_visible_for_client(stage_code: Optional[str]) -> bool:
    """
    Return True if stage is allowed to be set explicitly by client tenants.

    By умолчанию любые неизвестные/кастомные стадии считаются только агентскими
    (visible_for_client=False), пока явно не помечены в STAGE_META.
    """
    if not stage_code:
        return False
    meta = STAGE_META.get(stage_code) or {}
    return bool(meta.get("visible_for_client", False))


def _normalize_status_reason_input(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (set, tuple, list)):
        values = raw
    elif isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        try:
            decoded = json.loads(s)
            if isinstance(decoded, (list, tuple, set)):
                values = decoded
            else:
                values = [decoded]
        except Exception:
            values = s.split(",")
    else:
        values = [raw]

    out: list[str] = []
    for value in values:
        v = str(value).strip()
        if not v:
            continue
        out.append(v.lower())
    # preserve order, drop duplicates
    seen: set[str] = set()
    deduped: list[str] = []
    for code in out:
        if code in seen:
            continue
        seen.add(code)
        deduped.append(code)
    return deduped


def _validate_status_reasons(stage_code: Optional[str], codes: list[str]) -> list[str]:
    if not codes:
        if stage_code in _REASON_REQUIRED_STAGES:
            raise HTTPException(
                status_code=422,
                detail=f"Необходимо указать причину для этапа '{STAGE_LABELS.get(stage_code or '', stage_code)}'",
            )
        return []
    if stage_code not in _REASON_CODES:
        raise HTTPException(
            status_code=422,
            detail=f"Для этапа '{STAGE_LABELS.get(stage_code or '', stage_code)}' причины не поддерживаются.",
        )
    allowed = _REASON_CODES[stage_code]
    invalid = [code for code in codes if code not in allowed]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Некорректные причины для этапа '{STAGE_LABELS.get(stage_code or '', stage_code)}': {', '.join(invalid)}",
        )
    return codes


def _format_status_reason_labels(stage_code: Optional[str], codes: list[str]) -> Optional[str]:
    if not codes or stage_code not in _REASON_LABELS:
        return None
    labels = _REASON_LABELS.get(stage_code, {})
    human = [labels.get(code, code) for code in codes]
    return ", ".join(human) if human else None
