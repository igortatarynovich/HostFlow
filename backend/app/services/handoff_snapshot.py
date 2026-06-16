"""Build and persist immutable handoff snapshot (v1) at create_handoff time."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.models.user import User
from backend.app.models.vacancy import Vacancy
from backend.app.modules.documents.crud import list_candidate_documents
from backend.app.services.reference_service_facade import ReferenceContext, ReferenceServiceFacade
from backend.app.services.recruitment_application_service import get_application_for_handoff
from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver


def _iso(dt: datetime | date | None) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).isoformat()
        return dt.isoformat()
    return dt.isoformat()


def _doc_status_value(status: Any) -> str:
    if hasattr(status, "value"):
        return str(status.value)
    return str(status)


async def _user_label(db: AsyncSession, user_id: str | None) -> dict[str, Any | None]:
    if not user_id:
        return {"user_id": None, "name": None}
    u = await db.get(User, str(user_id))
    if not u:
        return {"user_id": str(user_id), "name": None}
    name = (getattr(u, "full_name", None) or "").strip() or None
    email = (getattr(u, "email", None) or "").strip() or None
    return {"user_id": str(user_id), "name": name or email}


def _citizenship(cand: Candidate) -> str | None:
    pd = getattr(cand, "personal_data", None) or {}
    if not isinstance(pd, dict):
        return None
    for key in ("citizenship", "nationality", "country_of_citizenship"):
        v = pd.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def _work_country(cand: Candidate) -> str | None:
    pd = getattr(cand, "personal_data", None) or {}
    if isinstance(pd, dict):
        for key in ("work_country", "country_of_work", "country"):
            v = pd.get(key)
            if v is not None and str(v).strip():
                return str(v).strip()
    extra = getattr(cand, "extra", None) or {}
    if isinstance(extra, dict):
        for key in ("work_country", "country_of_work"):
            v = extra.get(key)
            if v is not None and str(v).strip():
                return str(v).strip()
    return None


def _campaign_from_origin(cand: Candidate) -> str | None:
    o = getattr(cand, "origin", None) or {}
    if not isinstance(o, dict):
        return None
    for key in ("utm_campaign", "campaign", "utm_medium"):
        v = o.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


async def build_handoff_snapshot_payload_v1(
    db: AsyncSession,
    *,
    handoff: CandidateHandoff,
    candidate: Candidate,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Assemble JSON payload (v1 blocks). `now` is anchor for integrity.created_at."""
    snap_time = now or datetime.now(timezone.utc)
    agency_tid = str(handoff.agency_tenant_id)
    vac_id_raw = getattr(candidate, "vacancy_id", None)
    vac_id = str(vac_id_raw).strip() if vac_id_raw else None
    app = await get_application_for_handoff(
        db,
        tenant_id=agency_tid,
        candidate_id=str(candidate.id),
        vacancy_id=vac_id,
        application_id=str(handoff.application_id).strip()
        if getattr(handoff, "application_id", None)
        else None,
    )

    vacancy_title: str | None = None
    if app and getattr(app, "vacancy_id", None):
        vac = await db.get(Vacancy, str(app.vacancy_id))
        if vac:
            vacancy_title = str(vac.title)
    elif vac_id:
        vac = await db.get(Vacancy, vac_id)
        if vac:
            vacancy_title = str(vac.title)

    recruiter_block: dict[str, Any | None] = {"id": None, "name": None}
    rid = getattr(app, "recruiter_id", None) if app else getattr(candidate, "recruiter_id", None)
    if rid:
        recruiter_block = await _user_label(db, str(rid))

    docs = await list_candidate_documents(db, agency_tid, str(candidate.id))
    documents_out: list[dict[str, Any]] = []
    for d in docs:
        runtime_ref = await DocumentTypeRuntimeResolver.resolve_for_document(db, d)
        documents_out.append(
            {
                "type": str(getattr(d, "doc_type", "") or ""),
                "status": _doc_status_value(getattr(d, "status", "")),
                "expires_at": _iso(getattr(d, "expire_date", None)),
                "verified_at": _iso(getattr(d, "verified_at", None)),
                "canonical": {
                    "code": runtime_ref.canonical_code,
                    "category": runtime_ref.category_code,
                    "criticality": runtime_ref.compliance_criticality,
                    "fallback_used": runtime_ref.fallback_used,
                },
            }
        )

    applicability = await ReferenceServiceFacade.get_applicable_documents(
        db,
        context=ReferenceContext(
            tenant_id=agency_tid,
            module="recruitment",
            entity_type="candidate",
            entity_id=str(candidate.id),
            candidate_id=str(candidate.id),
            citizenship=_citizenship(candidate),
            work_country=_work_country(candidate),
            stage=str(getattr(candidate, "stage", "") or "") or None,
            vacancy_id=str(getattr(app, "vacancy_id", "") or "") or vac_id,
        ),
    )
    applicability_out = [
        {
            "document_code": str(r.get("document_code") or ""),
            "required": bool(r.get("required")),
            "reason": str(r.get("reason") or ""),
            "source_pack": str(r.get("source_pack") or ""),
            "criticality": str(r.get("criticality") or ""),
            "due_point": str(r.get("due_point") or ""),
            "status": str(r.get("status") or "") or None,
        }
        for r in applicability
    ]

    requested_by = await _user_label(db, str(handoff.requested_by_user_id))

    lead_id = str(app.lead_id) if app and getattr(app, "lead_id", None) else None
    app_source = str(app.source) if app else (getattr(candidate, "source", None) or None)
    if app_source is not None:
        app_source = str(app_source).strip() or None

    application_block: dict[str, Any] | None = None
    if app:
        application_block = {
            "application_id": str(app.id),
            "vacancy_id": str(app.vacancy_id) if getattr(app, "vacancy_id", None) else None,
            "vacancy_title": vacancy_title,
            "recruiter": recruiter_block,
        }

    payload: dict[str, Any] = {
        "handoff": {
            "handoff_id": str(handoff.id),
            "type": str(getattr(handoff, "handoff_type", "") or ""),
            "destination": str(getattr(handoff, "destination", "") or ""),
            "created_at": _iso(handoff.requested_at),
            "requested_by": requested_by,
        },
        "candidate": {
            "id": str(candidate.id),
            "name": {
                "first_name": str(candidate.first_name or ""),
                "last_name": str(candidate.last_name or ""),
            },
            "contacts": {
                "email": getattr(candidate, "email", None),
                "phone": getattr(candidate, "phone", None),
                "phone_country_code": getattr(candidate, "phone_country_code", None),
            },
            "citizenship": _citizenship(candidate),
            "current_stage": getattr(candidate, "stage", None),
        },
        "application": application_block,
        "documents": documents_out,
        "expected_documents": applicability_out,
        "notes_summary": getattr(candidate, "note", None),
        "source": {
            "lead_id": lead_id,
            "source": app_source,
            "campaign": _campaign_from_origin(candidate),
        },
        "integrity": {
            "snapshot_version": 1,
            "created_at": _iso(snap_time),
        },
    }
    return payload


async def persist_handoff_create_snapshot(
    db: AsyncSession,
    *,
    handoff: CandidateHandoff,
    candidate: Candidate,
) -> CandidateHandoffSnapshot:
    """Insert immutable snapshot row for this handoff (caller must commit)."""
    existing = (
        await db.execute(
            select(CandidateHandoffSnapshot).where(
                CandidateHandoffSnapshot.handoff_id == str(handoff.id)
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    now = datetime.now(timezone.utc)
    payload = await build_handoff_snapshot_payload_v1(db, handoff=handoff, candidate=candidate, now=now)
    # Deep-freeze shape for tests / API consumers (JSON round-trip stable).
    payload = json.loads(json.dumps(payload, default=str))

    row = CandidateHandoffSnapshot(
        id=str(uuid.uuid4()),
        handoff_id=str(handoff.id),
        agency_tenant_id=str(handoff.agency_tenant_id),
        payload=payload,
    )
    db.add(row)
    await db.flush()
    return row
