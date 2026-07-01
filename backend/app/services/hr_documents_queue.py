"""HR document queues: missing (ruleset vs live) and expiring (live expiry)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.pipeline_overrides_service import approved_handoff_relaxed_types
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot
from backend.app.models.enums import DocumentStatus
from backend.app.services.document_catalog import normalize_doc_type
from backend.app.services.document_hub_delivery_contract import (
    list_candidate_documents_via_contract,
)
from backend.app.services.reference_service_facade import ReferenceContext, ReferenceServiceFacade

HR_HIGH_RISK_DOC_TYPES: frozenset[str] = frozenset(
    {
        "work_permit",
        "residence_permit",
        "visa",
        "code95",
        "tacho_card",
        "medical_certificate",
        "psych_tests",
        "driver_license",
    }
)

READY_LIVE = frozenset(
    {
        DocumentStatus.approved.value,
        DocumentStatus.received.value,
        DocumentStatus.delivered.value,
        DocumentStatus.completed.value,
        DocumentStatus.verified.value,
        DocumentStatus.issued.value,
        DocumentStatus.registered.value,
        DocumentStatus.active.value,
        DocumentStatus.not_required.value,
    }
)


def _parse_extra(candidate: Candidate) -> dict[str, Any]:
    raw = getattr(candidate, "extra", None)
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            out = json.loads(raw)
            return out if isinstance(out, dict) else {}
        except Exception:
            return {}
    return {}


def _snapshot_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    c = payload.get("candidate") or {}
    name = c.get("name") or {}
    return {
        "candidate_id": c.get("id"),
        "first_name": name.get("first_name"),
        "last_name": name.get("last_name"),
    }


def _snapshot_doc_status(payload: dict[str, Any] | None, doc_type: str) -> str | None:
    if not payload:
        return None
    canon = normalize_doc_type(doc_type)
    for d in (payload.get("expected_documents") or []) or []:
        t = normalize_doc_type(str(d.get("document_code") or ""))
        if t == canon:
            return str(d.get("status") or "").strip() or None
    for d in (payload.get("documents") or []) or []:
        t = normalize_doc_type(str((d.get("canonical") or {}).get("code") or d.get("type") or ""))
        if t == canon:
            return str(d.get("status") or "").strip() or None
    return None


def _doc_status_str(doc: Any) -> str:
    st = getattr(doc, "status", None)
    if hasattr(st, "value"):
        return str(st.value)
    return str(st or "").lower()


def _live_best_status_for_type(docs: Sequence[Any], doc_type: str) -> str:
    canon = normalize_doc_type(doc_type)
    acceptable = {canon}
    matches = [
        d
        for d in docs
        if normalize_doc_type(str(getattr(d, "doc_type", "") or "")) in acceptable
        and getattr(d, "deleted_at", None) is None
    ]
    if not matches:
        return "missing"
    for d in matches:
        if _doc_status_str(d) in READY_LIVE:
            return _doc_status_str(d)
    return _doc_status_str(matches[0])


def _risk_for_type(doc_type: str) -> str:
    return "high" if normalize_doc_type(doc_type) in HR_HIGH_RISK_DOC_TYPES else "normal"


def _missing_recommended(*, risk: str) -> str:
    if risk == "high":
        return "urgent_collect_compliance_document"
    return "collect_required_document"


def _expiring_recommended(*, expired: bool) -> str:
    if expired:
        return "renew_or_replace_immediately"
    return "schedule_renewal"


async def _accepted_internal_hr_handoffs(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str | None,
    candidate_id: str | None,
    max_scan: int = 400,
) -> list[CandidateHandoff]:
    tid = str(tenant_id).strip()
    stmt = (
        select(CandidateHandoff)
        .join(Candidate, Candidate.id == CandidateHandoff.candidate_id)
        .where(
            CandidateHandoff.agency_tenant_id == tid,
            CandidateHandoff.destination == "internal_hr",
            CandidateHandoff.status == "accepted",
            Candidate.deleted_at.is_(None),
        )
    )
    if handoff_id:
        stmt = stmt.where(CandidateHandoff.id == str(handoff_id))
    if candidate_id:
        stmt = stmt.where(CandidateHandoff.candidate_id == str(candidate_id))
    stmt = stmt.order_by(
        CandidateHandoff.reviewed_at.desc().nulls_last(),
        CandidateHandoff.requested_at.desc(),
    ).limit(max_scan)
    return list((await db.execute(stmt)).scalars().all())


async def _snapshots_by_handoff(
    db: AsyncSession, handoff_ids: Sequence[str]
) -> dict[str, CandidateHandoffSnapshot]:
    if not handoff_ids:
        return {}
    rows = await db.execute(
        select(CandidateHandoffSnapshot).where(
            CandidateHandoffSnapshot.handoff_id.in_(list(handoff_ids))
        )
    )
    return {str(s.handoff_id): s for s in rows.scalars().all()}


def _assignee_team_scope(assignee_scope: str, viewer_role: str) -> bool:
    scope = (assignee_scope or "mine").strip().lower()
    role = (viewer_role or "").strip().lower()
    if scope == "team" and role in (
        "administrator",
        "supervisor",
        "hr_officer",
        "superadmin",
    ):
        return True
    return False


async def list_hr_documents_missing(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer_id: str,
    viewer_role: str,
    assignee_scope: str,
    document_type: str | None,
    priority: str | None,
    handoff_id: str | None,
    candidate_id: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    from backend.app.services.hr_inbox import _workforce_employee_id_by_handoff

    handoffs = await _accepted_internal_hr_handoffs(
        db,
        tenant_id=tenant_id,
        handoff_id=handoff_id,
        candidate_id=candidate_id,
    )
    if not handoffs:
        return [], 0
    snaps = await _snapshots_by_handoff(db, [h.id for h in handoffs])
    wf = await _workforce_employee_id_by_handoff(db, tenant_id=tenant_id, handoffs=handoffs)

    team = _assignee_team_scope(assignee_scope, viewer_role)
    viewer = str(viewer_id).strip()

    rows_out: list[dict[str, Any]] = []
    for h in handoffs:
        assignee = str(h.assigned_to_user_id).strip() if h.assigned_to_user_id else None
        if not team and assignee and assignee != viewer:
            continue
        # "mine" still includes unassigned accepted internal-HR handoffs (pool queue), same as inbox visibility.

        cand = await db.get(Candidate, str(h.candidate_id))
        if not cand:
            continue
        extra = _parse_extra(cand)
        pd = getattr(cand, "personal_data", None) or {}
        if not isinstance(pd, dict):
            pd = {}
        oc = getattr(cand, "own_company_id", None)
        own_company_id = str(oc).strip() if oc else None
        expected_docs = await ReferenceServiceFacade.get_applicable_documents(
            db,
            context=ReferenceContext(
                tenant_id=str(tenant_id),
                module="hr",
                entity_type="candidate",
                entity_id=str(cand.id),
                candidate_id=str(cand.id),
                citizenship=(extra.get("citizenship") or pd.get("citizenship")),
                work_country=(extra.get("work_country") or pd.get("work_country")),
                residence_status=(extra.get("poland_stay_basis") or pd.get("residency_status")),
                position_category=(extra.get("position_category") or pd.get("position_category") or extra.get("role")),
                employment_type=(extra.get("employment_type") or pd.get("employment_type")),
                stage="hr",
                client_id=own_company_id or None,
                vacancy_id=(str(getattr(cand, "vacancy_id", "") or "").strip() or None),
            ),
        )
        live_docs = await list_candidate_documents_via_contract(
            db,
            tenant_id=str(tenant_id),
            candidate_id=str(cand.id),
            active_own_company_id=own_company_id,
        )
        active = [d for d in live_docs if getattr(d, "deleted_at", None) is None]
        required_codes = {
            normalize_doc_type(str(item.get("document_code") or ""))
            for item in expected_docs
            if bool(item.get("required")) and str(item.get("document_code") or "").strip()
        }
        if not required_codes:
            # Safe compatibility fallback when packs are not enabled yet for a tenant.
            required_codes = {
                normalize_doc_type(str(getattr(d, "doc_type", "") or ""))
                for d in active
                if str(getattr(d, "doc_type", "") or "").strip()
            }

        missing_types = [
            code
            for code in sorted(required_codes)
            if _live_best_status_for_type(active, code) not in READY_LIVE
        ]
        relaxed = await approved_handoff_relaxed_types(
            db, tenant_id=str(tenant_id), candidate_id=str(cand.id)
        )
        if relaxed:
            missing_types = [m for m in missing_types if m not in relaxed]

        snap_row = snaps.get(str(h.id))
        payload = dict(snap_row.payload) if snap_row is not None else None

        for mtype in missing_types:
            canon = normalize_doc_type(mtype)
            if document_type and normalize_doc_type(document_type) != canon:
                continue
            risk = _risk_for_type(canon)
            if (priority or "").strip().lower() == "high" and risk != "high":
                continue
            rows_out.append(
                {
                    "handoff_id": str(h.id),
                    "workforce_employee_id": wf.get(str(h.id)),
                    "candidate_snapshot_summary": _snapshot_summary(payload),
                    "document_type": canon,
                    "current_status": _live_best_status_for_type(active, canon),
                    "required": True,
                    "snapshot_status": _snapshot_doc_status(payload, canon),
                    "expires_at": None,
                    "risk": risk,
                    "assignee_user_id": assignee,
                    "recommended_action": _missing_recommended(risk=risk),
                }
            )

    total = len(rows_out)
    page = rows_out[offset : offset + limit]
    return page, total


def _is_expired_date(expire: date, today: date) -> bool:
    return expire < today


def _within_horizon(expire: date, today: date, horizon: int) -> bool:
    return today <= expire <= today + timedelta(days=horizon)


async def list_hr_documents_expiring(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer_id: str,
    viewer_role: str,
    assignee_scope: str,
    horizon_days: int,
    status: str,
    document_type: str | None,
    risk: str | None,
    handoff_id: str | None,
    candidate_id: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    from backend.app.services.hr_inbox import _workforce_employee_id_by_handoff

    handoffs = await _accepted_internal_hr_handoffs(
        db,
        tenant_id=tenant_id,
        handoff_id=handoff_id,
        candidate_id=candidate_id,
    )
    if not handoffs:
        return [], 0
    snaps = await _snapshots_by_handoff(db, [h.id for h in handoffs])
    wf = await _workforce_employee_id_by_handoff(db, tenant_id=tenant_id, handoffs=handoffs)
    team = _assignee_team_scope(assignee_scope, viewer_role)
    viewer = str(viewer_id).strip()
    today = datetime.now(timezone.utc).date()
    horizon = max(1, min(int(horizon_days or 30), 365))
    st_f = (status or "all").strip().lower()

    rows_out: list[dict[str, Any]] = []
    for h in handoffs:
        assignee = str(h.assigned_to_user_id).strip() if h.assigned_to_user_id else None
        if not team and assignee and assignee != viewer:
            continue

        cand = await db.get(Candidate, str(h.candidate_id))
        if not cand:
            continue
        oc = getattr(cand, "own_company_id", None)
        own_company_id = str(oc).strip() if oc else None
        live_docs = await list_candidate_documents_via_contract(
            db,
            tenant_id=str(tenant_id),
            candidate_id=str(cand.id),
            active_own_company_id=own_company_id,
        )
        snap_row = snaps.get(str(h.id))
        payload = dict(snap_row.payload) if snap_row is not None else None

        for d in live_docs:
            if getattr(d, "deleted_at", None) is not None:
                continue
            exp = getattr(d, "expire_date", None)
            if exp is None:
                continue
            if not isinstance(exp, date):
                continue
            runtime_profile = await ReferenceServiceFacade.get_document_runtime_profile(
                db,
                document=d,
                context=ReferenceContext(
                    tenant_id=str(tenant_id),
                    module="hr",
                    entity_type="candidate",
                    entity_id=str(cand.id),
                    candidate_id=str(cand.id),
                    stage="hr",
                    client_id=own_company_id or None,
                ),
            )
            canon = normalize_doc_type(
                str(
                    (runtime_profile.get("profile") or {}).get("canonical_code")
                    or getattr(d, "doc_type", "")
                    or ""
                )
            )
            if document_type and normalize_doc_type(document_type) != canon:
                continue
            rsk = _risk_for_type(canon)
            if (risk or "").strip().lower() == "high" and rsk != "high":
                continue

            expired = _is_expired_date(exp, today) or _doc_status_str(d) == DocumentStatus.expired.value
            in_horizon = _within_horizon(exp, today, horizon)
            if st_f == "expired" and not expired:
                continue
            if st_f == "expiring" and (expired or not in_horizon):
                continue
            if st_f == "all":
                if not expired and not in_horizon:
                    continue

            rows_out.append(
                {
                    "handoff_id": str(h.id),
                    "workforce_employee_id": wf.get(str(h.id)),
                    "candidate_snapshot_summary": _snapshot_summary(payload),
                    "document_type": canon,
                    "current_status": _doc_status_str(d),
                    "required": False,
                    "snapshot_status": _snapshot_doc_status(payload, canon),
                    "expires_at": exp.isoformat(),
                    "risk": rsk,
                    "assignee_user_id": assignee,
                    "recommended_action": _expiring_recommended(expired=expired),
                }
            )

    rows_out.sort(key=lambda r: (r.get("expires_at") or ""))
    total = len(rows_out)
    page = rows_out[offset : offset + limit]
    return page, total
