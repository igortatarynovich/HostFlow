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
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid as _uuid
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_stage_history import CandidateStageHistory
from backend.app.api.v1.candidates import repo
from backend.app.api.v1.candidates.acl import CandidateACL
from uuid import UUID
from sqlalchemy import select, update, insert, or_
from fastapi import HTTPException
from backend.app.constants.stages_adapter import DEFAULT_STAGE_CODE
from backend.app.constants.stages import LABELS as STAGE_LABELS, STATUS_REASON_CHOICES
from backend.app.models import Vacancy
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
from backend.app.services.recruiter_assignment import (
    AssignmentDecision,
    assign_recruiter as assign_recruiter_service,
)
from backend.app.services.audit import log_activity
from backend.app.services import events
from backend.app.services.events import EventAudience
from backend.app.services.source_labels import normalize_candidate_source

_UNSET = object()


def _now_naive() -> datetime:
    """Return current UTC timestamp without tzinfo for legacy naive columns."""
    return _now_utc().replace(tzinfo=None)


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
) -> bool:
    if acl is None or acl.unrestricted:
        return True

    manager_val = str(manager) if manager else None
    company_val = str(company) if company else None
    vacancy_val = str(vacancy) if vacancy else None

    if manager_val and manager_val in acl.manager_ids:
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
    reason: Any = _UNSET,
) -> Optional[Candidate]:
    """Update candidate fields and apply domain rules (tenant-scoped)."""
    return await update_candidate_full(
        db,
        tenant_id,
        candidate_id,
        data,
        actor_id=actor_id,
        status_reason_override=reason,
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
) -> Candidate:
    payload = dict(payload or {})

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

    source_val: Optional[str] = source_update_value

    origin_payload = payload.pop("origin", None)
    if origin_payload is not None and not isinstance(origin_payload, dict):
        origin_payload = {"value": origin_payload}

    stage_input = payload.get("stage") or payload.get("status")
    if stage_input is None or str(stage_input).strip() == "":
        stage_code = DEFAULT_STAGE_CODE
    else:
        normalized = _normalize_stage_to_code(str(stage_input))
        if not normalized:
            raise HTTPException(status_code=422, detail=f"Unknown stage '{stage_input}'")
        stage_code = normalized

    _validate_stage_transition(None, stage_code)
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
    if acl and not acl.unrestricted:
        if manager_val is None:
            manager_val = actor_id
        if manager_val is None or manager_val not in acl.manager_ids:
            raise HTTPException(status_code=403, detail="Forbidden manager for recruiter")
        if company_id_val and str(company_id_val) not in acl.company_ids:
            raise HTTPException(status_code=403, detail="Forbidden company for recruiter")

    cand_id = str(payload.get("id") or _uuid.uuid4())

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

    values: Dict[str, Any] = {
        "id": cand_id,
        "tenant_id": tenant_id,
        "first_name": str(payload.get("first_name") or "").strip(),
        "last_name": str(payload.get("last_name") or "").strip(),
        "phone": payload.get("phone"),
        "languages": languages,
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
        "created_at": _now_naive(),
        "updated_at": _now_naive(),
    }
    if source_val is not None:
        values["source"] = source_val
    if origin_payload is not None:
        values["origin"] = origin_payload
    if assignment and assignment.assigned:
        values["recruiter_id"] = assignment.recruiter_id

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
    return c


async def update_candidate_full(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    payload: Dict[str, Any],
    *,
    actor_id: Optional[str] = None,
    status_reason_override: Any = _UNSET,
    acl: CandidateACL | None = None,
) -> Candidate:
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

    payload = dict(payload or {})

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
    if "phone" in payload and payload["phone"] is not None:
        changes["phone"] = str(payload["phone"]).strip() or None
    if "phone_country_code" in payload and payload["phone_country_code"] is not None:
        prefix = str(payload["phone_country_code"]).strip()
        changes["phone_country_code"] = prefix or None
    if "email" in payload and payload["email"] is not None:
        changes["email"] = payload["email"]
    if "note" in payload and payload["note"] is not None:
        changes["note"] = payload["note"]

    _mgr_present = (payload.get("manager") is not None) or (payload.get("manager_id") is not None)
    if _mgr_present:
        _mgr_raw = payload.get("manager") if payload.get("manager") is not None else payload.get("manager_id")
        _mgr_str = (str(_mgr_raw or "").strip())
        if _mgr_str == "":
            pass
        else:
            try:
                changes["manager"] = str(UUID(_mgr_str))
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid manager UUID")

    if "recruiter_id" in payload:
        recruiter_raw = payload.get("recruiter_id")
        if recruiter_raw in (None, ""):
            changes["recruiter_id"] = None
        else:
            try:
                recruiter_uuid = str(UUID(str(recruiter_raw).strip()))
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid recruiter UUID")
            recruiter_row = await db.execute(
                select(User).where(
                    User.id == recruiter_uuid,
                    or_(User.tenant_id.is_(None), User.tenant_id == tenant_id),
                    User.is_active.is_(True),
                )
            )
            recruiter_obj = recruiter_row.scalar_one_or_none()
            if recruiter_obj is None:
                raise HTTPException(status_code=404, detail="Recruiter not found")
            changes["recruiter_id"] = recruiter_uuid

    if "languages" in payload and payload["languages"] is not None:
        changes["languages"] = _ensure_langs(payload["languages"])

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
            _validate_stage_transition(getattr(c, "stage", None), new_stage_code)
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
            vrow = await db.execute(
                select(Vacancy).where(
                    Vacancy.id == str(payload["vacancy_id"]),
                    Vacancy.tenant_id == tenant_id,
                )
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

    if "company_id" in payload and payload.get("vacancy_id") is None:
        company_val = str(payload["company_id"]) if payload["company_id"] else None
        if company_val and acl and not acl.unrestricted and company_val not in acl.company_ids:
            raise HTTPException(status_code=403, detail="Forbidden company for recruiter")
        changes["company_id"] = company_val

    if not c.short_id:
        changes["short_id"] = await _generate_unique_short_id(db)

    target_manager = changes.get("manager", getattr(c, "manager", None))
    target_company = changes.get("company_id", getattr(c, "company_id", None))
    target_vacancy = changes.get("vacancy_id", getattr(c, "vacancy_id", None))
    if acl and not _candidate_matches_acl(
        acl,
        manager=target_manager,
        company=target_company,
        vacancy=target_vacancy,
    ):
        raise HTTPException(status_code=403, detail="Forbidden candidate scope for recruiter")

    if changes:
        try:
            changes["updated_at"] = _now_naive()
            await db.execute(
                update(Candidate)
                .where(Candidate.id == candidate_id, Candidate.tenant_id == tenant_id)
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

            if stage_changed:
                await sync_candidate_links(
                    db=db,
                    tenant_id=UUID(tenant_id),
                    candidate_id=UUID(candidate_id),
                    candidate_stage=c.stage,
                )
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Update failed: {e}")
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
            await sync_candidate_links(
                db=db,
                tenant_id=UUID(tenant_id),
                candidate_id=UUID(candidate_id),
                candidate_stage=c.stage,
            )
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Update failed: {e}")

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
    target_stage = _normalize_stage_to_code(stage) or stage
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
            ):
                out.append({"candidate_id": cid, "stage": target_stage, "ok": False, "error": "forbidden"})
                continue

            normalized = _normalize_stage_to_code(target_stage) or target_stage
            if not normalized:
                out.append({"candidate_id": cid, "stage": target_stage, "ok": False, "error": "unknown stage"})
                continue

            _validate_stage_transition(getattr(c, "stage", None), normalized)

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
                        "error": str(exc.detail),
                    }
                )
                continue

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

            await sync_candidate_links(
                db=db,
                tenant_id=UUID(tenant_id),
                candidate_id=UUID(cid),
                candidate_stage=normalized,
            )

            out.append({"candidate_id": cid, "stage": normalized, "ok": True})
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
    actor_id: Optional[str] = None,  # kept for future audit trail
    acl: CandidateACL | None = None,
) -> list[BulkManagerResult]:
    manager_value = (manager_id or "").strip()
    try:
        manager_value = str(UUID(manager_value))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=422, detail="Invalid manager UUID") from exc

    results: list[BulkManagerResult] = []
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
        ):
            entry["ok"] = False
            entry["error"] = "forbidden"
            results.append(entry)
            continue
        allowed_indexes.append(len(results))
        results.append(entry)

    if not allowed_indexes:
        return results

    try:
        await db.execute(
            update(Candidate)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.deleted_at.is_(None),
                Candidate.id.in_([results[idx]["candidate_id"] for idx in allowed_indexes]),
            )
            # updated_at should remain timezone-naive to match DB schema
            .values(manager=manager_value, updated_at=_now_naive())
        )
        await db.commit()
        for idx in allowed_indexes:
            results[idx]["ok"] = True
            results[idx].pop("error", None)
    except Exception as exc:  # pragma: no cover - defensive
        await db.rollback()
        for idx in allowed_indexes:
            results[idx]["ok"] = False
            results[idx]["error"] = f"update_failed: {exc}"
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
